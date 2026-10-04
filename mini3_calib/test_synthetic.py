#!/usr/bin/env python3
"""Recover a known camera from rendered views of the circle grid."""

import tempfile
from pathlib import Path

import cv2
import numpy as np

from calibrate import orb_yaml
from pattern import COLS, ROWS, find_grid, geometry, object_points, render

# USER_SETTINGS
PANEL_WIDTH = 1920              # 合成するモニタの幅（画素）
PANEL_HEIGHT = 1080             # 合成するモニタの高さ（画素）
DIAGONAL_IN = 27.0              # 合成するモニタの対角（インチ）
WIDTH = 1280                    # 合成するカメラ画像の幅
HEIGHT = 720                    # 合成するカメラ画像の高さ
FX = 730.0                      # 正解とする水平焦点距離（画素）
FY = 730.0                      # 正解とする垂直焦点距離（画素）
DIST_COEFFS = (0.08, -0.18, 0.001, -0.001, 0.12)  # 正解とする k1 k2 p1 p2 k3
CIRCLE_SAMPLES = 36             # 1つの円を描くときの外周の点数
CENTER_ERROR_MAX_PX = 1.5       # 正面画像で許す中心のずれ（画素）
RMS_MAX_PX = 0.5                # 許す再投影誤差（画素）
PARAM_TOLERANCE_PX = 8.0        # 焦点距離と主点の許容誤差（画素）
POSES_MM = (                    # 各視点のヨー、ピッチ、距離（ミリメートル）
    (0.0, 0.0, 1600.0),
    (-0.25, 0.05, 1700.0),
    (0.22, -0.08, 1800.0),
    (0.05, 0.2, 1900.0),
    (-0.08, -0.18, 2000.0),
    (0.18, 0.12, 2100.0),
    (-0.16, 0.16, 1750.0),
    (0.1, -0.14, 2200.0),
)


def camera_matrix():
    return np.array(
        [[FX, 0.0, WIDTH / 2.0], [0.0, FY, HEIGHT / 2.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )


def paint_view(spec, rvec, tvec):
    points = object_points(spec["cols"], spec["rows"], spec["spacing_mm"])
    image = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    radius = spec["radius_mm"]
    for center in points:
        angles = np.linspace(0.0, 2.0 * np.pi, CIRCLE_SAMPLES, endpoint=False)
        ring = np.stack(
            [
                center[0] + radius * np.cos(angles),
                center[1] + radius * np.sin(angles),
                np.zeros_like(angles),
            ],
            axis=1,
        ).astype(np.float64)
        projected, _ = cv2.projectPoints(
            ring, rvec, tvec, camera_matrix(), np.asarray(DIST_COEFFS, dtype=np.float64)
        )
        polygon = np.round(projected.reshape(-1, 2)).astype(np.int32)
        if polygon[:, 0].min() < 0 or polygon[:, 1].min() < 0:
            return None
        if polygon[:, 0].max() >= WIDTH or polygon[:, 1].max() >= HEIGHT:
            return None
        cv2.fillConvexPoly(image, polygon, 255)
    return image


def poses(spec):
    points = object_points(spec["cols"], spec["rows"], spec["spacing_mm"])
    center = points.mean(axis=0)
    views = []
    for yaw, pitch, distance in POSES_MM:
        rotation, _ = cv2.Rodrigues(np.array([pitch, yaw, 0.0], dtype=np.float64))
        translation = (-rotation @ center.reshape(3, 1)).reshape(3) + np.array([0.0, 0.0, distance])
        views.append((np.array([pitch, yaw, 0.0], dtype=np.float64), translation))
    return views


def main():
    spec = geometry(PANEL_WIDTH, PANEL_HEIGHT, DIAGONAL_IN, COLS, ROWS)
    panel, centers = render(spec)
    found = find_grid(panel, spec["cols"], spec["rows"])
    if found is None:
        raise SystemExit("frontal panel: grid not found")
    if found.shape != centers.shape:
        raise SystemExit(f"frontal panel: got {found.shape[0]} circles, expected {centers.shape[0]}")
    shift = np.linalg.norm(found - centers, axis=1).max()
    if shift > CENTER_ERROR_MAX_PX:
        raise SystemExit(f"frontal panel: center error {shift:.2f} px")

    object_sets = []
    image_sets = []
    model = object_points(spec["cols"], spec["rows"], spec["spacing_mm"])
    for rvec, tvec in poses(spec):
        view = paint_view(spec, rvec, tvec)
        if view is None:
            raise SystemExit("synthetic view left the image")
        detected = find_grid(view, spec["cols"], spec["rows"])
        if detected is None:
            raise SystemExit("synthetic view: grid not found")
        object_sets.append(model.astype(np.float32).reshape(-1, 1, 3))
        image_sets.append(detected.reshape(-1, 1, 2).astype(np.float32))

    rms, matrix, dist, _rvecs, _tvecs = cv2.calibrateCamera(
        object_sets,
        image_sets,
        (WIDTH, HEIGHT),
        None,
        None,
    )
    if rms > RMS_MAX_PX:
        raise SystemExit(f"rms {rms:.3f} px is too high")
    if abs(matrix[0, 0] - FX) > PARAM_TOLERANCE_PX or abs(matrix[1, 1] - FY) > PARAM_TOLERANCE_PX:
        raise SystemExit(f"focal length {matrix[0, 0]:.1f}, {matrix[1, 1]:.1f}")
    if abs(matrix[0, 2] - WIDTH / 2.0) > PARAM_TOLERANCE_PX or abs(matrix[1, 2] - HEIGHT / 2.0) > PARAM_TOLERANCE_PX:
        raise SystemExit(f"principal point {matrix[0, 2]:.1f}, {matrix[1, 2]:.1f}")

    text = orb_yaml((WIDTH, HEIGHT), matrix, dist, rms)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "mini3.yaml"
        path.write_text(text)
        fs = cv2.FileStorage(str(path), cv2.FILE_STORAGE_READ)
        if not fs.isOpened():
            raise SystemExit("yaml did not open")
        read_fx = fs.getNode("Camera1.fx").real()
        fs.release()
    if abs(read_fx - matrix[0, 0]) > 1e-3:
        raise SystemExit("yaml fx does not match")
    print(
        f"ok  rms {rms:.4f}  fx {matrix[0, 0]:.2f}  fy {matrix[1, 1]:.2f}  "
        f"cx {matrix[0, 2]:.2f}  cy {matrix[1, 2]:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
