#!/usr/bin/env python3
"""Save frames where the circle grid is fully visible, then skip N frames."""

import argparse
from pathlib import Path

import cv2
import numpy as np

from pattern import COLS, RADIUS_RATIO, ROWS, find_grid

# USER_SETTINGS
CIRCLE_COUNT = COLS * ROWS  # 残す円の個数。これ以外の画像は削除
SKIP_FRAMES = 5            # 円がそろったフレームのあと、この枚数を飛ばす
CORE_RATIO = 0.55           # 欠け判定に使う、半径に対する芯の割合
MAX_CORE_DARK = 0.25        # 芯のうち暗い画素がこの割合を超えたら、円が欠けている
EDGE_PAD = 8                # 円の外側に必要な余白（画素）。画面端に触れた円は欠けている
FRAMES_ROOT = "out/frames"  # この下に、動画名のフォルダを作る
VIDEOS_DIR = "mini3_bridge/pc/recordings"  # 引数を省略したときに見る動画の場所
PROGRESS_EVERY = 100        # この枚数ごとに、見ているフレーム数を出す


def radius_px(points):
    return RADIUS_RATIO * float(np.linalg.norm(points[1] - points[0])) / 2.0


def core_dark_fraction(gray, center_x, center_y, radius):
    inner = CORE_RATIO * radius
    x0 = int(np.floor(center_x - inner))
    x1 = int(np.ceil(center_x + inner)) + 1
    y0 = int(np.floor(center_y - inner))
    y1 = int(np.ceil(center_y + inner)) + 1
    if x0 < 0 or y0 < 0 or x1 > gray.shape[1] or y1 > gray.shape[0]:
        return 1.0
    patch = gray[y0:y1, x0:x1]
    yy, xx = np.ogrid[: patch.shape[0], : patch.shape[1]]
    mask = (xx - (center_x - x0)) ** 2 + (yy - (center_y - y0)) ** 2 <= inner ** 2
    values = patch[mask]
    if values.size == 0:
        return 1.0
    return float((values < 120).mean())


def log(message):
    print(message, flush=True)


def inspect_frame(frame):
    points = find_grid(frame, COLS, ROWS)
    if points is None or len(points) != CIRCLE_COUNT:
        return None, "円がそろっていない"
    radius = radius_px(points) + EDGE_PAD
    height, width = frame.shape[:2]
    clipped = (
        (points[:, 0] < radius)
        | (points[:, 0] > width - radius)
        | (points[:, 1] < radius)
        | (points[:, 1] > height - radius)
    )
    if clipped.any():
        return None, "円が画面端で欠けている"
    gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    for center_x, center_y in points:
        if core_dark_fraction(gray, center_x, center_y, radius - EDGE_PAD) > MAX_CORE_DARK:
            return None, "円の芯が欠けている"
    return points, ""


def videos_in(path):
    if path.is_dir():
        files = sorted(path.glob("*.mp4"))
        if not files:
            raise SystemExit(f"no mp4 in {path}")
        return files
    if not path.is_file():
        raise SystemExit(f"cannot open {path}")
    return [path]


def extract(video, out_dir, video_index, video_count):
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise SystemExit(f"cannot open {video}")
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    log(f"[{video_index}/{video_count}] {video.name}  {total} frames -> {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):
        old.unlink()
    index = 0
    skip_until = 0
    saved = 0
    while True:
        if index < skip_until:
            if not capture.grab():
                break
            index += 1
            if index % PROGRESS_EVERY == 0:
                log(f"  frame {index}/{total}  saved {saved}  skipping until {skip_until}")
            continue
        ok, frame = capture.read()
        if not ok:
            break
        _points, reason = inspect_frame(frame)
        if reason == "":
            name = f"f{index:05d}.png"
            cv2.imwrite(str(out_dir / name), frame)
            saved += 1
            skip_until = index + 1 + SKIP_FRAMES
            log(f"  save {name}  then skip {SKIP_FRAMES}")
        elif reason != "円がそろっていない":
            log(f"  frame {index}  {reason}")
        elif index % PROGRESS_EVERY == 0:
            log(f"  frame {index}/{total}  saved {saved}  {reason}")
        index += 1
    capture.release()
    removed = delete_wrong_count(out_dir)
    log(f"  done  frames {index}  saved {saved}  removed {removed}")


def delete_wrong_count(out_dir):
    removed = 0
    for path in sorted(out_dir.glob("*.png")):
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        points, reason = (None, "読めない") if frame is None else inspect_frame(frame)
        if points is None or len(points) != CIRCLE_COUNT:
            path.unlink()
            removed += 1
            log(f"  delete {path.name}  {reason}")
    return removed


def main():
    if CIRCLE_COUNT != COLS * ROWS:
        raise SystemExit(f"CIRCLE_COUNT {CIRCLE_COUNT} is not {COLS}x{ROWS}")
    parser = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    root = here.parent
    parser.add_argument(
        "video",
        nargs="?",
        type=Path,
        default=root / VIDEOS_DIR,
        help="one mp4, or a directory of mp4 files",
    )
    parser.add_argument("--out", type=Path, default=here / FRAMES_ROOT)
    args = parser.parse_args()
    videos = videos_in(args.video)
    log(f"videos {len(videos)}  from {args.video}")
    for video_index, video in enumerate(videos, start=1):
        extract(video, args.out / video.stem, video_index, len(videos))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
