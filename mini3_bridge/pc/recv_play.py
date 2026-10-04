#!/usr/bin/env python3
"""Receive mini3_bridge TCP messages, play them, and save the same bytes."""

import argparse
import socket
import struct
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from recv_save import export_tum, remux


def read_exact(conn: socket.socket, size: int) -> bytes:
    buf = bytearray()
    while len(buf) < size:
        chunk = conn.recv(size - len(buf))
        if not chunk:
            raise EOFError
        buf += chunk
    return bytes(buf)


def ffmpeg_format(mime: str) -> str:
    name = mime.upper()
    if "265" in name or "HEVC" in name:
        return "hevc"
    return "h264"


def start_player(fmt: str) -> subprocess.Popen:
    return subprocess.Popen(
        [
            "ffplay",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            "-framedrop",
            "-probesize",
            "32",
            "-analyzeduration",
            "0",
            "-fpsprobesize",
            "0",
            "-max_delay",
            "0",
            "-sync",
            "ext",
            "-vf",
            "setpts=0",
            "-framerate",
            "30",
            "-f",
            fmt,
            "-i",
            "pipe:0",
            "-window_title",
            "mini3_bridge",
        ],
        stdin=subprocess.PIPE,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--tum", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "recordings",
    )
    args = parser.parse_args()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.host, args.port))
    server.listen(1)
    print(f"listening {args.host}:{args.port}", flush=True)
    try:
        conn, addr = server.accept()
    except KeyboardInterrupt:
        print("stop", flush=True)
        server.close()
        return 0
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    print(f"client {addr}", flush=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fmt = "h264"
    mime = ""
    width = 0
    height = 0
    elementary = args.out / f"{stamp}.h264"
    mp4 = elementary.with_suffix(".mp4")
    stream = None
    if not args.no_save:
        args.out.mkdir(parents=True, exist_ok=True)
        stream = elementary.open("wb")
        print(f"save {elementary}", flush=True)

    player = None
    video_bytes = 0
    last_report = time.monotonic()
    window = 0
    try:
        while True:
            (length,) = struct.unpack("!I", read_exact(conn, 4))
            if length < 1 or length > 8_000_000:
                print(f"bad length {length}", flush=True)
                return 1
            body = read_exact(conn, length)
            kind = body[0]
            payload = body[1:]
            if kind == 1:
                mime_len = payload[0]
                mime = payload[1 : 1 + mime_len].decode("utf-8", "replace")
                width, height = struct.unpack("!HH", payload[1 + mime_len : 1 + mime_len + 4])
                fmt = ffmpeg_format(mime)
                suffix = ".h264" if fmt == "h264" else ".h265"
                if elementary.suffix != suffix and stream is not None:
                    stream.close()
                    elementary.unlink(missing_ok=True)
                    elementary = elementary.with_suffix(suffix)
                    mp4 = elementary.with_suffix(".mp4")
                    stream = elementary.open("wb")
                print(f"codec {mime} {width}x{height} ffplay -f {fmt}", flush=True)
                if player is None:
                    player = start_player(fmt)
            elif kind == 2:
                if stream is not None:
                    stream.write(payload)
                    stream.flush()
                if player is not None and player.stdin is not None:
                    player.stdin.write(payload)
                    player.stdin.flush()
                    if player.poll() is not None:
                        player = None
                video_bytes += len(payload)
                window += len(payload)
                now = time.monotonic()
                if now - last_report >= 1.0:
                    kbps = window * 8 / 1000 / (now - last_report)
                    print(f"video {video_bytes} bytes ~{kbps:.0f} kbps", flush=True)
                    last_report = now
                    window = 0
    except (EOFError, KeyboardInterrupt):
        print("stop", flush=True)
    finally:
        if stream is not None:
            stream.close()
        if player is not None and player.stdin is not None:
            player.stdin.close()
        if player is not None:
            try:
                player.wait(timeout=2)
            except subprocess.TimeoutExpired:
                player.kill()
        conn.close()
        server.close()
    if stream is not None and video_bytes > 0:
        remux(elementary, mp4, fmt, args.fps)
        print(f"mp4 {mp4}", flush=True)
        if args.tum:
            export_tum(mp4, args.out / stamp, args.fps)
    elif video_bytes == 0:
        print("no video saved", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
