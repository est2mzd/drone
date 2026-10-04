#!/usr/bin/env python3
"""Detect the circle grid in Mini 3 frames and write a pinhole calibration."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from pattern import find_grid, object_points

# USER_SETTINGS
MIN_VIEWS = 6                   # 校正に必要な、円がそろった画像の最少枚数
GEOMETRY_JSON = "out/pattern.json"  # show_pattern.py が書いた間隔
FRAMES_ROOT = "out/frames"     # この下の日時分フォルダから校正する画像を選ぶ
OUT_YAML = "out/mini3.yaml"     # ORB-SLAM3 用の書き出し先
DETECT_DIR = "detect"           # 検出結果の画像を置くディレクトリ
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")  # 静止画として読む拡張子
SLAM_WIDTH = 1280               # 追跡に使う画像の幅。これ以外は警告する
SLAM_HEIGHT = 720               # 追跡に使う画像の高さ。これ以外は警告する
CAMERA_FPS = 30                 # 書き出す YAML のフレームレート
CAMERA_RGB = 0                  # 0 はグレーで追跡する
ORB_FEATURES = 1000             # 1フレームで探す特徴点の数
ORB_SCALE = 1.2                 # 特徴点ピラミッドの段の縮小率
ORB_LEVELS = 8                  # 特徴点ピラミッドの段数
ORB_INI_TH_FAST = 20            # FAST の最初の閾値
ORB_MIN_TH_FAST = 7             # 点が足りないときの FAST の閾値
VIEWER_KEYFRAME_SIZE = 0.05     # ビューアのキーフレーム表示サイズ
VIEWER_KEYFRAME_LINE_WIDTH = 1.0  # ビューアのキーフレーム線の太さ
VIEWER_GRAPH_LINE_WIDTH = 0.9   # ビューアの共視グラフ線の太さ
VIEWER_POINT_SIZE = 2.0         # ビューアの地図点の大きさ
VIEWER_CAMERA_SIZE = 0.08       # ビューアのカメラ表示サイズ
VIEWER_CAMERA_LINE_WIDTH = 3.0  # ビューアのカメラ線の太さ
VIEWER_VIEWPOINT_X = 0.0        # ビューア初期視点の X
VIEWER_VIEWPOINT_Y = -0.7       # ビューア初期視点の Y
VIEWER_VIEWPOINT_Z = -1.8       # ビューア初期視点の Z
VIEWER_VIEWPOINT_F = 500.0      # ビューア投影の焦点距離
PROGRESS_EVERY = 1          # この枚数ごとに、見ている画像を出す


def load_geometry(path):
    spec = json.loads(Path(path).read_text())
    required = ("cols", "rows", "spacing_mm")
    missing = [key for key in required if key not in spec]
    if missing:
        raise SystemExit(f"{path} is missing {', '.join(missing)}")
    return spec


def frame_folders(root):
    if not root.is_dir():
        raise SystemExit(f"no frames yet: {root}")
    folders = [
        path
        for path in sorted(root.iterdir())
        if path.is_dir() and path.name != "preview" and any(path.glob("*.png"))
    ]
    if not folders:
        raise SystemExit(f"no frame folders in {root}")
    return folders


def choose_folder(root):
    folders = frame_folders(root)
    print("folders:")
    for index, path in enumerate(folders, start=1):
        print(f"  {index}  {path.name}")
    raw = input("number: ").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= len(folders):
        raise SystemExit(f"choose 1..{len(folders)}")
    return folders[int(raw) - 1]


def list_images(directory):
    files = [
        path
        for path in sorted(Path(directory).iterdir())
        if path.suffix.lower() in IMAGE_SUFFIXES
    ]
    if not files:
        raise SystemExit(f"no images in {directory}")
    return files


def frames_from_images(directory):
    for path in list_images(directory):
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if frame is None:
            raise SystemExit(f"cannot read {path}")
        yield path.name, frame


def orb_yaml(image_size, camera_matrix, dist_coeffs, rms):
    width, height = image_size
    fx, fy = camera_matrix[0, 0], camera_matrix[1, 1]
    cx, cy = camera_matrix[0, 2], camera_matrix[1, 2]
    k1, k2, p1, p2, k3 = dist_coeffs.reshape(-1)[:5]
    return f"""%YAML:1.0

File.version: "1.0"

Camera.type: "PinHole"

# Measured on the Mini 3 downlink with the mini3_calib circle grid.
# Reprojection RMS {rms:.4f} px. Image {width}x{height}.
Camera1.fx: {fx:.6f}
Camera1.fy: {fy:.6f}
Camera1.cx: {cx:.6f}
Camera1.cy: {cy:.6f}

Camera1.k1: {k1:.8f}
Camera1.k2: {k2:.8f}
Camera1.k3: {k3:.8f}
Camera1.p1: {p1:.8f}
Camera1.p2: {p2:.8f}

Camera.width: {width}
Camera.height: {height}
Camera.fps: {CAMERA_FPS}
Camera.RGB: {CAMERA_RGB}

ORBextractor.nFeatures: {ORB_FEATURES}
ORBextractor.scaleFactor: {ORB_SCALE}
ORBextractor.nLevels: {ORB_LEVELS}
ORBextractor.iniThFAST: {ORB_INI_TH_FAST}
ORBextractor.minThFAST: {ORB_MIN_TH_FAST}

Viewer.KeyFrameSize: {VIEWER_KEYFRAME_SIZE}
Viewer.KeyFrameLineWidth: {VIEWER_KEYFRAME_LINE_WIDTH}
Viewer.GraphLineWidth: {VIEWER_GRAPH_LINE_WIDTH}
Viewer.PointSize: {VIEWER_POINT_SIZE}
Viewer.CameraSize: {VIEWER_CAMERA_SIZE}
Viewer.CameraLineWidth: {VIEWER_CAMERA_LINE_WIDTH}
Viewer.ViewpointX: {VIEWER_VIEWPOINT_X}
Viewer.ViewpointY: {VIEWER_VIEWPOINT_Y}
Viewer.ViewpointZ: {VIEWER_VIEWPOINT_Z}
Viewer.ViewpointF: {VIEWER_VIEWPOINT_F}
"""


def log(message):
    print(message, flush=True)


def main():
    parser = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    parser.add_argument("--images", type=Path, help="frame folder; omit to choose from out/frames")
    parser.add_argument(
        "--geometry",
        type=Path,
        default=here / GEOMETRY_JSON,
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=here / OUT_YAML,
    )
    parser.add_argument("--min-views", type=int, default=MIN_VIEWS)
    args = parser.parse_args()
    if args.images is None:
        args.images = choose_folder(here / FRAMES_ROOT)

    spec = load_geometry(args.geometry)
    log(f"images {args.images}")
    model = object_points(spec["cols"], spec["rows"], spec["spacing_mm"])
    frames = list(frames_from_images(args.images))
    log(f"read {len(frames)} images")
    object_sets = []
    image_sets = []
    image_size = None
    found = 0
    debug_dir = args.out.parent / DETECT_DIR
    debug_dir.mkdir(parents=True, exist_ok=True)

    for seen, (name, frame) in enumerate(frames, start=1):
        if image_size is None:
            image_size = (frame.shape[1], frame.shape[0])
            log(f"size {image_size[0]}x{image_size[1]}")
        elif image_size != (frame.shape[1], frame.shape[0]):
            raise SystemExit(f"{name} is {frame.shape[1]}x{frame.shape[0]}, expected {image_size[0]}x{image_size[1]}")
        centers = find_grid(frame, spec["cols"], spec["rows"])
        if centers is None:
            if seen % PROGRESS_EVERY == 0:
                log(f"  {seen}/{len(frames)} {name}  円がそろっていない")
            continue
        found += 1
        object_sets.append(model.astype(np.float32).reshape(-1, 1, 3))
        image_sets.append(centers.reshape(-1, 1, 2).astype(np.float32))
        drawn = frame if frame.ndim == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        cv2.drawChessboardCorners(drawn, (spec["cols"], spec["rows"]), image_sets[-1], True)
        cv2.imwrite(str(debug_dir / f"{found:03d}_{Path(name).stem}.png"), drawn)
        if seen % PROGRESS_EVERY == 0:
            log(f"  {seen}/{len(frames)} {name}  円 {len(centers)}")

    log(f"grid found in {found} of {len(frames)} frames")
    if found < args.min_views:
        raise SystemExit(f"need at least {args.min_views} views, got {found}")

    log(f"calibrating {found} images")
    rms, camera_matrix, dist_coeffs, _rvecs, _tvecs = cv2.calibrateCamera(
        object_sets,
        image_sets,
        image_size,
        None,
        None,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(orb_yaml(image_size, camera_matrix, dist_coeffs, rms))
    log(f"rms {rms:.4f} px")
    log(
        f"fx {camera_matrix[0, 0]:.2f}  fy {camera_matrix[1, 1]:.2f}  "
        f"cx {camera_matrix[0, 2]:.2f}  cy {camera_matrix[1, 2]:.2f}"
    )
    log(f"wrote {args.out}")
    if image_size != (SLAM_WIDTH, SLAM_HEIGHT):
        log(
            f"warning: SLAM recordings are {SLAM_WIDTH}x{SLAM_HEIGHT}, "
            f"this set is {image_size[0]}x{image_size[1]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
