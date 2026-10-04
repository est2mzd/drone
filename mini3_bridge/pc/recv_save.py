#!/usr/bin/env python3
"""Receive mini3_bridge video and save it for ORB-SLAM3.

The phone sends the same TCP messages as recv_play.py. This program writes the
compressed elementary stream as it arrives, then remuxes it to MP4 without
re-encoding. With --tum it also writes a TUM-style image sequence.
"""

import argparse
import socket
import struct
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


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
            "mini3_bridge record",
        ],
        stdin=subprocess.PIPE,
    )


def remux(elementary: Path, mp4: Path, fmt: str, fps: float) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-fflags",
            "+genpts",
            "-r",
            str(fps),
            "-f",
            fmt,
            "-i",
            str(elementary),
            "-c",
            "copy",
            str(mp4),
        ],
        check=True,
    )


def export_tum(mp4: Path, sequence: Path, fps: float) -> None:
    rgb = sequence / "rgb"
    rgb.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(mp4),
            "-start_number",
            "0",
            str(rgb / "%06d.png"),
        ],
        check=True,
    )
    frames = sorted(rgb.glob("*.png"))
    lines = []
    for index, frame in enumerate(frames):
        timestamp = index / fps
        lines.append(f"{timestamp:.6f} rgb/{frame.name}")
    (sequence / "rgb.txt").write_text("\n".join(lines) + "\n")
    print(f"tum {sequence} frames={len(frames)}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "recordings",
    )
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--no-play", action="store_true")
    parser.add_argument(
        "--tum",
        action="store_true",
        help="also export rgb.txt and png frames for ORB-SLAM3 mono_tum",
    )
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fmt = "h264"
    elementary = args.out / f"{stamp}.h264"
    mp4 = args.out / f"{stamp}.mp4"
    meta = args.out / f"{stamp}.txt"
    sequence = args.out / stamp

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.host, args.port))
    server.listen(1)
    print(f"listening {args.host}:{args.port}", flush=True)
    print(f"save {elementary}", flush=True)
    conn, addr = server.accept()
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    print(f"client {addr}", flush=True)

    player = None
    mime = ""
    width = 0
    height = 0
    video_bytes = 0
    started = time.time()
    last_report = time.monotonic()
    window = 0
    stream = elementary.open("wb")
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
                elementary = elementary.with_suffix(".h264" if fmt == "h264" else ".h265")
                if stream.name != str(elementary):
                    stream.close()
                    stream = elementary.open("wb")
                mp4 = elementary.with_suffix(".mp4")
                print(f"codec {mime} {width}x{height} -> {elementary.name}", flush=True)
                if not args.no_play and player is None:
                    player = start_player(fmt)
            elif kind == 2:
                stream.write(payload)
                stream.flush()
                video_bytes += len(payload)
                window += len(payload)
                if player is not None and player.stdin is not None:
                    player.stdin.write(payload)
                    player.stdin.flush()
                    if player.poll() is not None:
                        player = None
                now = time.monotonic()
                if now - last_report >= 1.0:
                    kbps = window * 8 / 1000 / (now - last_report)
                    print(f"saved {video_bytes} bytes ~{kbps:.0f} kbps", flush=True)
                    last_report = now
                    window = 0
    except (EOFError, KeyboardInterrupt):
        print("stop", flush=True)
    finally:
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

    duration = max(0.0, time.time() - started)
    meta.write_text(
        "\n".join(
            [
                f"mime={mime}",
                f"width={width}",
                f"height={height}",
                f"fps_assumed={args.fps}",
                f"bytes={video_bytes}",
                f"seconds={duration:.3f}",
                f"elementary={elementary}",
            ]
        )
        + "\n"
    )
    if video_bytes == 0:
        print("no video saved", flush=True)
        return 1
    remux(elementary, mp4, fmt, args.fps)
    print(f"mp4 {mp4}", flush=True)
    if args.tum:
        export_tum(mp4, sequence, args.fps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
