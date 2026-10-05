#!/usr/bin/env python3
"""Depth Anything 3 の深度を、元の映像へ重ねた動画にする。近いほど赤、遠いほど青。"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# USER_SETTINGS
VIDEO = Path(
    "mini3_bridge/pc/recordings/20261002_001816.mp4"
)  # いま使っている映像
MODEL_ID = "depth-anything/DA3-SMALL"  # CPU で回す Depth Anything 3。Apache-2.0 の最小モデル
SAMPLE_FPS = 5.0  # 推論する枚数/秒。間のフレームは近い時刻の深度を使う
PROCESS_RES = 504  # モデルに入れる長辺の画素
BLEND = 0.75  # 深度色の濃さ。ORB の重ね動画と同じ
CAMERA_YAML = (
    Path(__file__).resolve().parents[2] / "mini3_calib/out/mini3.yaml"
)  # 円パターンで測ったカメラ設定。箱を映像へ戻すときに使う
VOXEL_DIV = 80.0  # 箱の一辺。そのフレームの点群の対角長さをこの数で割る。小さいほど箱は大きい
VOXEL_FILL = 0.72  # 箱がマスを占める割合。1 にすると隣とくっついて面に見える

DISTANCE_COLORS = np.array(
    [
        [40, 40, 255],
        [0, 110, 255],
        [0, 210, 255],
        [50, 190, 40],
        [255, 150, 30],
        [230, 40, 20],
    ],
    dtype=np.uint8,
)


def log(message):
    print(message, flush=True)


def sample_indices(frame_count, fps, sample_fps):
    step = max(1, int(round(fps / sample_fps)))
    indices = list(range(0, frame_count, step))
    if indices[-1] != frame_count - 1:
        indices.append(frame_count - 1)
    return indices


def read_frames(video, indices):
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise SystemExit(f"cannot open {video}")
    frames = []
    wanted = set(indices)
    for index in range(max(indices) + 1):
        ok, frame = capture.read()
        if not ok:
            break
        if index in wanted:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            log(f"read frame {index}")
    capture.release()
    if len(frames) != len(indices):
        raise SystemExit(f"read {len(frames)} frames, wanted {len(indices)}")
    return frames


def infer_depths(frames):
    import torch
    from depth_anything_3.api import DepthAnything3

    torch.set_num_threads(max(1, torch.get_num_threads()))
    log(f"loading {MODEL_ID}")
    started = time.time()
    model = DepthAnything3.from_pretrained(MODEL_ID).to("cpu")
    model.eval()
    log(f"loaded in {time.time() - started:.1f}s")
    depths = []
    for index, frame in enumerate(frames):
        started = time.time()
        prediction = model.inference(
            image=[frame],
            process_res=PROCESS_RES,
            process_res_method="upper_bound_resize",
        )
        depths.append(np.asarray(prediction.depth[0], dtype=np.float32))
        log(f"infer {index + 1}/{len(frames)} {time.time() - started:.1f}s shape {depths[-1].shape}")
    return depths


def color_bands(depths):
    logs = np.concatenate([np.log(np.clip(depth, 1e-3, None)).ravel() for depth in depths])
    low, high = np.percentile(logs, [5, 95])
    span = float(high - low)
    if span < 1e-6:
        span = 1.0
    return float(low), span


def colorize(depth, low, span, shape):
    resized = cv2.resize(depth, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
    log_depth = np.log(np.clip(resized, 1e-3, None))
    unit = np.clip((log_depth - low) / span, 0.0, 1.0)
    band = np.minimum((unit * len(DISTANCE_COLORS)).astype(np.int32), len(DISTANCE_COLORS) - 1)
    return DISTANCE_COLORS[band]


def nearest_depth(index, sample_index, depths):
    position = int(np.searchsorted(sample_index, index))
    if position <= 0:
        return depths[0]
    if position >= len(sample_index):
        return depths[-1]
    before = position - 1
    if abs(sample_index[before] - index) <= abs(sample_index[position] - index):
        return depths[before]
    return depths[position]


FACE_CORNERS = np.array(
    [
        [[1, -1, -1], [1, 1, -1], [1, 1, 1], [1, -1, 1]],
        [[-1, -1, -1], [-1, -1, 1], [-1, 1, 1], [-1, 1, -1]],
        [[-1, 1, -1], [1, 1, -1], [1, 1, 1], [-1, 1, 1]],
        [[-1, -1, -1], [-1, -1, 1], [1, -1, 1], [1, -1, -1]],
        [[-1, -1, 1], [-1, 1, 1], [1, 1, 1], [1, -1, 1]],
        [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1]],
    ],
    dtype=np.float64,
)
FACE_NORMALS = np.array(
    [
        [1, 0, 0],
        [-1, 0, 0],
        [0, 1, 0],
        [0, -1, 0],
        [0, 0, 1],
        [0, 0, -1],
    ],
    dtype=np.float64,
)


def load_camera(path):
    if not path.is_file():
        raise SystemExit(f"calibration file not found: {path}")
    storage = cv2.FileStorage(str(path), cv2.FILE_STORAGE_READ)
    if not storage.isOpened():
        raise SystemExit(f"cannot read {path}")
    fx = storage.getNode("Camera1.fx").real()
    fy = storage.getNode("Camera1.fy").real()
    cx = storage.getNode("Camera1.cx").real()
    cy = storage.getNode("Camera1.cy").real()
    k1 = storage.getNode("Camera1.k1").real()
    k2 = storage.getNode("Camera1.k2").real()
    p1 = storage.getNode("Camera1.p1").real()
    p2 = storage.getNode("Camera1.p2").real()
    k3 = storage.getNode("Camera1.k3").real()
    width = int(storage.getNode("Camera.width").real())
    height = int(storage.getNode("Camera.height").real())
    storage.release()
    matrix = np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
    dist = np.array([k1, k2, p1, p2, k3], dtype=np.float64)
    return matrix, dist, width, height


def depth_intrinsics(matrix, video_size, depth_shape):
    video_w, video_h = video_size
    depth_h, depth_w = depth_shape
    scale = depth_w / float(video_w)
    resized_h = video_h * scale
    crop = (resized_h - depth_h) / 2.0
    fx = matrix[0, 0] * scale
    fy = matrix[1, 1] * scale
    cx = matrix[0, 2] * scale
    cy = matrix[1, 2] * scale - crop
    return fx, fy, cx, cy


def voxels_from_depth(depth, intrinsics, divisor):
    fx, fy, cx, cy = intrinsics
    height, width = depth.shape
    rows, cols = np.indices((height, width))
    z = depth.astype(np.float64)
    points = np.stack(
        [
            (cols - cx) * z / fx,
            (rows - cy) * z / fy,
            z,
        ],
        axis=-1,
    ).reshape(-1, 3)
    span = points.max(axis=0) - points.min(axis=0)
    diagonal = float(np.linalg.norm(span))
    size = diagonal / float(divisor) if diagonal > 1e-9 else 1.0
    keys = np.floor(points / size).astype(np.int32)
    _, first = np.unique(keys, axis=0, return_index=True)
    centers = (keys[first].astype(np.float64) + 0.5) * size
    return centers, size


def paint_voxels(centers, size, low, span, width, height, matrix, dist):
    layer = np.zeros((height, width, 3), dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)
    if len(centers) == 0:
        return layer, mask
    visible = centers @ FACE_NORMALS.T < 0.0
    voxel_index, face_index = np.nonzero(visible)
    if len(voxel_index) == 0:
        return layer, mask
    order = np.argsort(centers[voxel_index, 2])[::-1]
    voxel_index = voxel_index[order]
    face_index = face_index[order]
    half = size * 0.5 * VOXEL_FILL
    corners = centers[voxel_index][:, None, :] + FACE_CORNERS[face_index] * half
    keep = np.all(corners[:, :, 2] > 0.05, axis=1)
    pixels, _ = cv2.projectPoints(
        corners.reshape(-1, 1, 3),
        np.zeros((3, 1), dtype=np.float64),
        np.zeros((3, 1), dtype=np.float64),
        matrix,
        dist,
    )
    pixels = pixels.reshape(-1, 4, 2)
    log_depth = np.log(np.clip(centers[voxel_index, 2], 1e-3, None))
    unit = np.clip((log_depth - low) / span, 0.0, 1.0)
    band = np.minimum((unit * len(DISTANCE_COLORS)).astype(np.int32), len(DISTANCE_COLORS) - 1)
    colors = DISTANCE_COLORS[band]
    for index in np.flatnonzero(keep):
        polygon = pixels[index]
        if not np.isfinite(polygon).all():
            continue
        extent = polygon.max(axis=0) - polygon.min(axis=0)
        edges = np.linalg.norm(np.roll(polygon, -1, axis=0) - polygon, axis=1)
        if extent.max() > 140 or edges.max() > 90:
            continue
        if extent.max() < 2.0:
            center = polygon.mean(axis=0)
            polygon = np.stack(
                [
                    center + [-1.0, -1.0],
                    center + [1.0, -1.0],
                    center + [1.0, 1.0],
                    center + [-1.0, 1.0],
                ]
            )
        polygon = np.round(polygon).astype(np.int32)
        color = colors[index].tolist()
        cv2.fillConvexPoly(layer, polygon, color, lineType=cv2.LINE_8)
        cv2.fillConvexPoly(mask, polygon, 255, lineType=cv2.LINE_8)
    return layer, mask


def open_ffmpeg(path, width, height, fps):
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{width}x{height}",
        "-r",
        f"{fps}",
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(path),
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


def write_voxels(video, sample_index, depths, out_path):
    matrix, dist, calib_w, calib_h = load_camera(CAMERA_YAML)
    intrinsics = depth_intrinsics(matrix, (calib_w, calib_h), depths[0].shape)
    packs = []
    for index, depth in enumerate(depths):
        centers, size = voxels_from_depth(depth, intrinsics, VOXEL_DIV)
        packs.append((centers, size))
        if index % 20 == 0:
            log(f"voxels {index}/{len(depths)} n={len(centers)} edge={size:.4f}")
    low, span = color_bands(depths)
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise SystemExit(f"cannot open {video}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    layers = []
    for index, (centers, size) in enumerate(packs):
        started = time.time()
        layer, mask = paint_voxels(centers, size, low, span, width, height, matrix, dist)
        layers.append((layer, mask))
        log(f"paint {index + 1}/{len(packs)} {time.time() - started:.1f}s voxels {len(centers)}")
    process = open_ffmpeg(out_path, width, height, fps)
    caption = f"da3 voxel 1/{int(VOXEL_DIV)}  near=red far=blue"
    for index in range(frame_count):
        ok, frame = capture.read()
        if not ok:
            break
        position = int(np.searchsorted(sample_index, index))
        if position <= 0:
            chosen = 0
        elif position >= len(sample_index):
            chosen = len(sample_index) - 1
        else:
            before = position - 1
            if abs(int(sample_index[before]) - index) <= abs(int(sample_index[position]) - index):
                chosen = before
            else:
                chosen = position
        layer, mask = layers[chosen]
        blended = (BLEND * layer.astype(np.float32) + (1.0 - BLEND) * frame.astype(np.float32)).astype(np.uint8)
        image = np.where(mask[:, :, None] > 0, blended, frame)
        cv2.putText(image, caption, (16, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_8)
        process.stdin.write(np.ascontiguousarray(image).tobytes())
        if index % 100 == 0:
            log(f"write {index}/{frame_count}")
    process.stdin.close()
    capture.release()
    code = process.wait()
    if code != 0:
        raise SystemExit(f"ffmpeg exited {code}")
    log(f"wrote {out_path}")


def write_overlay(video, sample_index, depths, out_path):
    low, span = color_bands(depths)
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise SystemExit(f"cannot open {video}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    process = open_ffmpeg(out_path, width, height, fps)
    caption = "da3  near=red far=blue"
    for index in range(frame_count):
        ok, frame = capture.read()
        if not ok:
            break
        color = colorize(nearest_depth(index, sample_index, depths), low, span, frame.shape)
        image = cv2.addWeighted(color, BLEND, frame, 1.0 - BLEND, 0)
        cv2.putText(image, caption, (16, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_8)
        process.stdin.write(image.tobytes())
        if index % 100 == 0:
            log(f"write {index}/{frame_count}")
    process.stdin.close()
    capture.release()
    code = process.wait()
    if code != 0:
        raise SystemExit(f"ffmpeg exited {code}")
    log(f"wrote {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?", type=Path, default=VIDEO)
    parser.add_argument("--voxels", action="store_true")
    args = parser.parse_args()
    video = args.video
    if not video.is_file():
        raise SystemExit(f"missing {video}")
    capture = cv2.VideoCapture(str(video))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    capture.release()
    indices = sample_indices(frame_count, fps, SAMPLE_FPS)
    log(f"{video} frames {frame_count} fps {fps:.2f} samples {len(indices)}")
    cache = video.with_name(f"{video.stem}_da3_depth.npz")
    if cache.is_file():
        stored = np.load(cache)
        indices = stored["indices"].astype(np.int32).tolist()
        depths = [stored[f"d{i}"] for i in range(len(indices))]
        log(f"loaded {cache} samples {len(depths)}")
    else:
        frames = read_frames(video, indices)
        depths = infer_depths(frames)
        np.savez_compressed(cache, indices=np.array(indices, dtype=np.int32), **{f"d{i}": depth for i, depth in enumerate(depths)})
        log(f"saved {cache}")
    sample_index = np.array(indices, dtype=np.int32)
    if args.voxels:
        out_path = video.with_name(f"{video.stem}_da3_div_{int(round(VOXEL_DIV)):03d}.mp4")
        write_voxels(video, sample_index, depths, out_path)
    else:
        out_path = video.with_name(f"{video.stem}_da3.mp4")
        write_overlay(video, sample_index, depths, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
