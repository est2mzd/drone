#!/usr/bin/env python3
"""Play a video on the right and ORB-SLAM3 voxels on the left."""

import argparse
import sys
import time

import cv2
import numpy as np

WINDOW_W = 1600
WINDOW_H = 720
LEFT_W = 640
VIDEO_W = 960
VIDEO_H = 540

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


def load_points(path):
    raw = np.loadtxt(path)
    if raw.size == 0:
        return np.zeros((0, 4), dtype=np.float64)
    raw = np.atleast_2d(raw)
    if raw.shape[1] != 4:
        raise SystemExit(f"expected t x y z in {path}")
    return raw


def build_voxels(points, divisor=80.0):
    if len(points) == 0:
        return np.zeros((0, 3)), np.zeros((0,)), 1.0
    grouped = {}
    xyz = points[:, 1:4]
    span = xyz.max(axis=0) - xyz.min(axis=0)
    diagonal = float(np.linalg.norm(span))
    size = diagonal / float(divisor) if diagonal > 1e-9 else 1.0
    for timestamp, x, y, z in points:
        key = (int(np.floor(x / size)), int(np.floor(y / size)), int(np.floor(z / size)))
        current = grouped.get(key)
        if current is None or timestamp < current[0]:
            grouped[key] = (float(timestamp), np.array([x, y, z], dtype=np.float64))
    times = np.array([item[0] for item in grouped.values()], dtype=np.float64)
    centers = np.stack([(np.array(key, dtype=np.float64) + 0.5) * size for key in grouped.keys()])
    order = np.argsort(times)
    return centers[order], times[order], size


def orbit_camera(center, yaw, pitch, distance):
    pitch = float(np.clip(pitch, -1.2, 1.2))
    direction = np.array(
        [
            np.sin(yaw) * np.cos(pitch),
            np.sin(pitch),
            np.cos(yaw) * np.cos(pitch),
        ],
        dtype=np.float64,
    )
    eye = center + direction * distance
    forward = center - eye
    forward /= np.linalg.norm(forward)
    world_up = np.array([0.0, -1.0, 0.0])
    right = np.cross(world_up, forward)
    if np.linalg.norm(right) < 1e-6:
        world_up = np.array([0.0, 0.0, 1.0])
        right = np.cross(world_up, forward)
    right /= np.linalg.norm(right)
    up = np.cross(forward, right)
    rotation = np.stack([right, -up, forward], axis=0)
    return eye, rotation


def project_points(points, rotation, eye, focal, cx, cy):
    camera = (points - eye) @ rotation.T
    depth = camera[:, 2]
    safe = np.where(np.abs(depth) < 1e-6, 1e-6, depth)
    pixels = np.empty((len(points), 2), dtype=np.float64)
    pixels[:, 0] = focal * camera[:, 0] / safe + cx
    pixels[:, 1] = focal * camera[:, 1] / safe + cy
    return pixels, depth


def fit_view(centers, size):
    if len(centers) == 0:
        return np.zeros(3), max(size * 8, 1.0)
    center = np.median(centers, axis=0)
    radii = np.linalg.norm(centers - center, axis=1)
    radius = float(np.percentile(radii, 90))
    distance = max(radius * 520.0 / 200.0, size * 8)
    return center, distance


def height_colors(centers):
    if len(centers) == 0:
        return np.zeros((0, 3), dtype=np.uint8)
    height = centers[:, 1]
    span = float(height.max() - height.min())
    unit = (height - height.min()) / span if span > 1e-9 else np.zeros(len(centers))
    blue = (40 + 180 * (1.0 - unit)).astype(np.uint8)
    green = (80 + 80 * unit).astype(np.uint8)
    red = (30 + 210 * unit).astype(np.uint8)
    return np.stack([blue, green, red], axis=1)


def render_voxels(centers, colors, size, yaw, pitch, distance, center):
    panel = np.full((WINDOW_H, LEFT_W, 3), 24, dtype=np.uint8)
    if len(centers) == 0:
        draw_empty(panel)
        return panel
    eye, rotation = orbit_camera(center, yaw, pitch, distance)
    half = size * 0.5
    focal = 520.0
    cx = LEFT_W * 0.5
    cy = WINDOW_H * 0.5
    order = np.argsort(np.linalg.norm(centers - eye, axis=1))[::-1]
    for index in order:
        origin = centers[index]
        toward = eye - origin
        visible = FACE_NORMALS @ toward > 0
        for face_index in np.flatnonzero(visible):
            corners = origin + FACE_CORNERS[face_index] * half
            pixels, depth = project_points(corners, rotation, eye, focal, cx, cy)
            if np.any(depth <= 0.05):
                continue
            polygon = np.round(pixels).astype(np.int32)
            cv2.fillConvexPoly(panel, polygon, colors[index].tolist(), lineType=cv2.LINE_8)
    return panel


def draw_empty(panel):
    from PIL import Image, ImageDraw, ImageFont

    image = Image.fromarray(cv2.cvtColor(panel, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 32)
    text = "地図点なし"
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    height = box[3] - box[1]
    origin = ((panel.shape[1] - width) // 2, (panel.shape[0] - height) // 2)
    draw.text(origin, text, font=font, fill=(220, 220, 220))
    panel[:] = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def label_panel(panel, text):
    cv2.putText(panel, text, (16, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 2, cv2.LINE_AA)


def compose(panel, frame):
    canvas = np.zeros((WINDOW_H, WINDOW_W, 3), dtype=np.uint8)
    canvas[:, :LEFT_W] = panel
    resized = cv2.resize(frame, (VIDEO_W, VIDEO_H), interpolation=cv2.INTER_AREA)
    y0 = (WINDOW_H - VIDEO_H) // 2
    canvas[y0 : y0 + VIDEO_H, LEFT_W : LEFT_W + VIDEO_W] = resized
    return canvas


def read_frame(capture, index):
    capture.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = capture.read()
    if not ok:
        raise SystemExit(f"cannot read frame {index}")
    return frame


def visible_count(times, timestamp):
    return int(np.searchsorted(times, timestamp, side="right")) if len(times) else 0


def check(video, points_path, dump_path, divisor):
    points = load_points(points_path)
    centers, times, size = build_voxels(points, divisor)
    capture = cv2.VideoCapture(video)
    if not capture.isOpened():
        raise SystemExit(f"cannot open {video}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    duration = (frame_count - 1) / fps
    early_t = float(times[0]) if len(times) else 0.0
    late_t = float(times[-1]) if len(times) else duration
    early_n = visible_count(times, early_t)
    late_n = visible_count(times, late_t + 1e-6)
    center, distance = fit_view(centers, size)
    colors = height_colors(centers)
    early_panel = render_voxels(centers[:early_n], colors[:early_n], size, 0.7, 0.35, distance, center)
    late_panel = render_voxels(centers[:late_n], colors[:late_n], size, 0.7, 0.35, distance, center)
    turned_panel = render_voxels(centers[:late_n], colors[:late_n], size, 0.7 + 0.8, 0.35, distance, center)
    last = read_frame(capture, frame_count - 1)
    image = compose(late_panel, last)
    if dump_path:
        cv2.imwrite(dump_path, image)
    right = image[(WINDOW_H - VIDEO_H) // 2 : (WINDOW_H - VIDEO_H) // 2 + VIDEO_H, LEFT_W:]
    resized = cv2.resize(last, (VIDEO_W, VIDEO_H), interpolation=cv2.INTER_AREA)
    video_error = float(np.mean(np.abs(right.astype(np.int16) - resized.astype(np.int16))))
    yaw_delta = float(np.mean(np.abs(late_panel.astype(np.int16) - turned_panel.astype(np.int16))))
    print(f"points {len(points)} voxels {len(centers)} early {early_n} late {late_n}")
    print(f"video_error {video_error:.4f} yaw_delta {yaw_delta:.4f}")
    if video_error > 1.0:
        raise SystemExit("right panel does not match the video frame")
    if len(centers) == 0:
        raise SystemExit("no voxels")
    if late_n < early_n:
        raise SystemExit("voxel count decreased over time")
    if yaw_delta < 0.5:
        raise SystemExit("yaw change did not move the voxels")
    print("check ok")


K = np.array(
    [[733.3333, 0.0, 640.0], [0.0, 733.3333, 360.0], [0.0, 0.0, 1.0]],
    dtype=np.float64,
)
DIST = np.array(
    [0.114164794, -0.262303843, -0.004601610, 0.002629248, 0.229064778],
    dtype=np.float64,
)


def quat_to_matrix(x, y, z, w):
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def load_poses(path):
    raw = np.loadtxt(path)
    raw = np.atleast_2d(raw)
    if raw.shape[1] != 9:
        raise SystemExit(f"expected t tx ty tz qx qy qz qw valid in {path}")
    return raw


def overlay_voxels(frame, centers, colors, size, pose):
    if len(centers) == 0 or pose[8] < 0.5:
        return frame
    rotation = quat_to_matrix(pose[4], pose[5], pose[6], pose[7])
    translation = pose[1:4]
    camera_center = -rotation.T @ translation
    camera_points = centers @ rotation.T + translation
    depth = camera_points[:, 2]
    keep = np.flatnonzero(depth > 0.2)
    if len(keep) == 0:
        return frame
    order = keep[np.argsort(depth[keep])[::-1]]
    layer = frame.copy()
    half = size * 0.5
    rvec = np.zeros((3, 1), dtype=np.float64)
    tvec = np.zeros((3, 1), dtype=np.float64)
    for index in order:
        visible = np.flatnonzero(FACE_NORMALS @ (camera_center - centers[index]) > 0)
        for face_index in visible:
            world = centers[index] + FACE_CORNERS[face_index] * half
            local = world @ rotation.T + translation
            if np.any(local[:, 2] <= 0.05):
                continue
            pixels, _ = cv2.projectPoints(local.reshape(-1, 1, 3), rvec, tvec, K, DIST)
            pixels = pixels.reshape(-1, 2)
            if pixels.shape != (4, 2) or not np.isfinite(pixels).all():
                continue
            span = pixels.max(axis=0) - pixels.min(axis=0)
            if span.min() < 1.5 or span.max() > 140:
                continue
            polygon = np.round(pixels).astype(np.int32)
            cv2.fillConvexPoly(layer, polygon, colors[index].tolist(), lineType=cv2.LINE_8)
    return cv2.addWeighted(layer, 0.75, frame, 0.25, 0)


def pose_table(poses):
    table = {}
    for row in poses:
        key = round(float(row[0]), 5)
        previous = table.get(key)
        if previous is None or (previous[8] < 0.5 <= row[8]):
            table[key] = row
    return table


def save_overlay(video, points_path, poses_path, out_path, divisor):
    points = load_points(points_path)
    poses = load_poses(poses_path)
    centers, times, size = build_voxels(points, divisor)
    colors = height_colors(centers)
    poses_by_time = pose_table(poses)
    capture = cv2.VideoCapture(video)
    if not capture.isOpened():
        raise SystemExit(f"cannot open {video}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise SystemExit(f"cannot write {out_path}")
    caption = f"overlay 1/{int(divisor)}  n={len(centers)}"
    drawn = 0
    for index in range(frame_count):
        ok, frame = capture.read()
        if not ok:
            break
        pose = poses_by_time.get(round(index / fps, 5))
        count = visible_count(times, index / fps)
        if pose is None:
            image = frame
        else:
            image = overlay_voxels(frame, centers[:count], colors[:count], size, pose)
            if pose[8] > 0.5:
                drawn += 1
        cv2.putText(image, caption, (16, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        writer.write(image)
        if index % 100 == 0:
            print(f"{out_path} frame {index}/{frame_count}", flush=True)
    writer.release()
    capture.release()
    print(f"wrote {out_path} voxels {len(centers)} overlaid {drawn}/{frame_count}")


def save_video(video, points_path, out_path, divisor):
    points = load_points(points_path)
    centers, times, size = build_voxels(points, divisor)
    capture = cv2.VideoCapture(video)
    if not capture.isOpened():
        raise SystemExit(f"cannot open {video}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    center, distance = fit_view(centers, size)
    colors = height_colors(centers)
    caption = f"voxel 1/{int(divisor)}  n={len(centers)}  edge={size:.4f}"
    writer = cv2.VideoWriter(
        out_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (WINDOW_W, WINDOW_H),
    )
    if not writer.isOpened():
        raise SystemExit(f"cannot write {out_path}")
    panel = None
    panel_count = -1
    for index in range(frame_count):
        ok, frame = capture.read()
        if not ok:
            break
        timestamp = index / fps
        count = visible_count(times, timestamp)
        if count != panel_count:
            panel = render_voxels(
                centers[:count],
                colors[:count],
                size,
                0.7,
                0.35,
                distance,
                center,
            )
            label_panel(panel, caption)
            panel_count = count
        writer.write(compose(panel, frame))
        if index % 100 == 0:
            print(f"{out_path} frame {index}/{frame_count} voxels {count}", flush=True)
    writer.release()
    capture.release()
    print(f"wrote {out_path} voxels {len(centers)} edge {size:.6f}")


class Player:
    def __init__(self, video, points_path, divisor=80.0):
        self.capture = cv2.VideoCapture(video)
        if not self.capture.isOpened():
            raise SystemExit(f"cannot open {video}")
        self.frame_count = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = float(self.capture.get(cv2.CAP_PROP_FPS) or 30.0)
        self.duration = max((self.frame_count - 1) / self.fps, 0.0)
        points = load_points(points_path)
        self.centers, self.times, self.size = build_voxels(points, divisor)
        self.colors = height_colors(self.centers)
        self.center, self.distance = fit_view(self.centers, self.size)
        self.yaw = 0.7
        self.pitch = 0.35
        self.dragging = False
        self.last_xy = (0, 0)
        self.paused = False
        self.clock_base = time.perf_counter()
        self.pause_time = 0.0
        self.cursor = 0
        self.frame = read_frame(self.capture, 0)
        self.panel_key = None
        self.panel = None

    def playback_time(self):
        if self.paused:
            return self.pause_time
        return min(time.perf_counter() - self.clock_base, self.duration)

    def on_mouse(self, event, x, y, flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN and x < LEFT_W:
            self.dragging = True
            self.last_xy = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging = False
        elif event == cv2.EVENT_MOUSEMOVE and self.dragging:
            dx = x - self.last_xy[0]
            dy = y - self.last_xy[1]
            self.yaw += dx * 0.01
            self.pitch += dy * 0.01
            self.last_xy = (x, y)
        elif event == cv2.EVENT_MOUSEWHEEL and x < LEFT_W:
            steps = cv2.getMouseWheelDelta(flags) / 120.0
            scale = 0.9 ** steps
            self.distance = float(np.clip(self.distance * scale, self.size * 2, self.distance * 20 + 1))

    def frame_at(self, timestamp):
        target = min(int(round(timestamp * self.fps)), self.frame_count - 1)
        if target < self.cursor:
            self.frame = read_frame(self.capture, target)
            self.cursor = target + 1
            return self.frame
        while self.cursor <= target:
            ok, frame = self.capture.read()
            if not ok:
                break
            self.frame = frame
            self.cursor += 1
        return self.frame

    def run(self):
        window = "Mini3 ORB-SLAM3"
        cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(window, self.on_mouse)
        while True:
            timestamp = self.playback_time()
            count = visible_count(self.times, timestamp)
            panel_key = (count, round(self.yaw, 4), round(self.pitch, 4), round(self.distance, 4))
            if panel_key != self.panel_key:
                self.panel = render_voxels(
                    self.centers[:count],
                    self.colors[:count],
                    self.size,
                    self.yaw,
                    self.pitch,
                    self.distance,
                    self.center,
                )
                self.panel_key = panel_key
            image = compose(self.panel, self.frame_at(timestamp))
            cv2.imshow(window, image)
            key = cv2.waitKey(15) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord(" "):
                if self.paused:
                    self.clock_base = time.perf_counter() - self.pause_time
                    self.paused = False
                else:
                    self.pause_time = self.playback_time()
                    self.paused = True
            if timestamp >= self.duration and not self.paused:
                self.pause_time = self.duration
                self.paused = True
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("points")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dump")
    parser.add_argument("--save", help="write a side-by-side mp4 and exit")
    parser.add_argument("--overlay", help="write the video with voxels projected onto it")
    parser.add_argument("--poses", help="Tcw file from offline_mono; defaults to <points>_poses.txt")
    parser.add_argument("--voxel-div", type=float, default=80.0, help="voxel edge = point-cloud diagonal / this")
    args = parser.parse_args()
    if args.overlay:
        poses = args.poses
        if not poses:
            stem = args.points.rsplit(".", 1)[0]
            poses = stem + "_poses.txt"
        save_overlay(args.video, args.points, poses, args.overlay, args.voxel_div)
        return 0
    if args.save:
        save_video(args.video, args.points, args.save, args.voxel_div)
        return 0
    if args.check or args.dump:
        check(args.video, args.points, args.dump, args.voxel_div)
        return 0
    Player(args.video, args.points, args.voxel_div).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
