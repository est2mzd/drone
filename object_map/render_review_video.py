#!/usr/bin/env python3
"""検出、深度の一致、支持平面、広い面を、静止画ではなく動画で並べる。

同じ深度で、勾配の滑らかさと第二の深度の山も数える。論文の最適化は回さない。
"""

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_objects as obs
import verify_papers as papers

# USER_SETTINGS
SAMPLE_FPS = 2.0  # 深度を計算する枚数/秒。短い室内映像
LONG_SAMPLE_FPS = 1.0  # 20秒を超える映像。Mini 3 の保存がこれ
LONG_SECONDS = 20.0  # これより長い映像は LONG_SAMPLE_FPS
PLAY_FPS = 8.0  # 書き出す動画の表示速度。サンプルを繰り返して元の長さに近づける
PANEL_HEIGHT = 360  # 1面の高さ
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"  # 動画の日本語
GRAD_MAX = 0.08  # 対数深度の勾配。これ未満を滑らかな面とする
SECOND_MODE_MIN = 0.25  # 第一の山の外に、これ以上の第二の山があれば混在
OUT_DIR = Path("agent_reports/20261006_object_map/videos")  # 比較動画。Git に残す
TRIAL_PATH = Path(
    "agent_reports/20261006_object_map/video_trials.yaml"
)  # 動画化と同時に数えた追加試行


def log(message):
    print(message, flush=True)


def even(value):
    value = int(value)
    return value if value % 2 == 0 else value - 1


def open_ffmpeg(path, width, height, fps):
    path.parent.mkdir(parents=True, exist_ok=True)
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


def sample_every(frame_count, fps, sample_fps):
    step = max(1, int(round(fps / sample_fps)))
    return list(range(0, frame_count, step))


def keep_only(frame, mask):
    image = np.zeros_like(frame)
    if mask is not None and int(np.count_nonzero(mask)) > 0:
        image[mask] = frame[mask]
    return image


def draw_text(image, text, origin, size, color):
    canvas = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT_PATH, size)
    draw.text(origin, text, font=font, fill=(color[2], color[1], color[0]))
    image[:] = cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR)


def header(width, title, note):
    bar = np.zeros((64, width, 3), dtype=np.uint8)
    draw_text(bar, title, (8, 4), 22, (255, 255, 255))
    draw_text(bar, note, (8, 34), 16, (140, 210, 255))
    return bar


def mosaic(frame, records, structure_mask, support_mask):
    our = np.zeros(frame.shape[:2], dtype=bool)
    boxes = np.zeros(frame.shape[:2], dtype=bool)
    for record in records:
        left, top, right, bottom = record["inner_xyxy"]
        boxes[top:bottom, left:right] = True
        our[top:bottom, left:right] = record["our_mask"]
    box_view = keep_only(frame, boxes)
    for record in records:
        left, top, right, bottom = record["inner_xyxy"]
        cv2.rectangle(box_view, (left, top), (right, bottom), (0, 220, 255), 2)
    panels = [
        (
            box_view,
            "1 箱だけ",
            "矩形だけ。奥行きが無く、地図の位置にならない",
        ),
        (
            keep_only(frame, our),
            "2 深度が揃った所",
            "箱の中で深度が揃った画素。物体の候補",
        ),
        (
            keep_only(frame, support_mask),
            "3 支持平面",
            "水平に近い面。床や机。無ければ真っ黒",
        ),
        (
            keep_only(frame, structure_mask),
            "4 広い面",
            "画面の大きな面。壁や床として地図に置く",
        ),
    ]
    resized = []
    for image, title, note in panels:
        scale = PANEL_HEIGHT / image.shape[0]
        panel = cv2.resize(image, (even(max(2, image.shape[1] * scale)), PANEL_HEIGHT))
        if int(panel.sum()) == 0:
            draw_text(panel, "このフレームには無い", (16, PANEL_HEIGHT // 2 - 16), 28, (80, 80, 255))
        resized.append(panel)
    width = min(panel.shape[1] for panel in resized)
    blocks = []
    for panel, (_image, title, note) in zip(resized, panels):
        blocks.append(np.vstack([header(width, title, note), panel[:, :width]]))
    top = np.hstack(blocks[:2])
    bottom = np.hstack(blocks[2:])
    body = np.vstack([top, bottom])
    foot = np.zeros((40, body.shape[1], 3), dtype=np.uint8)
    draw_text(
        foot,
        "オフラインではこの観測を地図へ積む。リアルタイムでは同じ観測を地図と照合して自己位置にする",
        (8, 8),
        18,
        (230, 230, 230),
    )
    return np.vstack([body, foot])


def smooth_ratio(crop):
    valid = np.isfinite(crop) & (crop > 1e-6)
    count = int(valid.sum())
    if count < 30:
        return None
    log_depth = np.log(np.clip(crop, 1e-3, None)).astype(np.float32)
    gx = cv2.Sobel(log_depth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(log_depth, cv2.CV_32F, 0, 1, ksize=3)
    smooth = valid & (np.hypot(gx, gy) < GRAD_MAX)
    components, labels = cv2.connectedComponents(smooth.astype(np.uint8))
    if components <= 1:
        return 0.0
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return float(sizes.max() / count)


def second_share(crop):
    valid = np.isfinite(crop) & (crop > 1e-6)
    count = int(valid.sum())
    if count < 30:
        return None
    _ratio, _median, mask = obs.dominant_depth(crop, obs.DEPTH_REL_TOL)
    rest = np.where(mask, np.nan, crop)
    rest_count = int(np.isfinite(rest).sum())
    if rest_count < 30:
        return 0.0
    ratio2, _median2, _mask2 = obs.dominant_depth(rest, obs.DEPTH_REL_TOL)
    return float(ratio2 * rest_count / count)


def render_video(video, depth_model, detector, rng):
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise SystemExit(f"cannot open {video}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    duration = frame_count / fps if fps else 0.0
    sample_fps = LONG_SAMPLE_FPS if duration > LONG_SECONDS else SAMPLE_FPS
    indices = sample_every(frame_count, fps, sample_fps)
    repeats = max(1, int(round(PLAY_FPS / sample_fps)))
    log(f"{video.name} duration={duration:.1f}s samples={len(indices)} repeats={repeats}")
    out_path = OUT_DIR / f"{video.stem}_compare.mp4"
    process = None
    stats = {
        "source": str(video),
        "samples": 0,
        "boxes": 0,
        "smooth_ge_half": 0,
        "second_mode": 0,
        "support_frames": 0,
        "structure_frames": 0,
    }
    for index in indices:
        frame = obs.read_frame(capture, index)
        if frame is None:
            continue
        depth = obs.infer_depth(depth_model, frame)
        fx, fy, cx, cy = papers.camera_for(frame.shape[1], frame.shape[0], video)
        planes, records = papers.verify_frame(
            frame, depth, obs.detect(detector, frame), video, fx, fy, cx, cy, rng
        )
        structure = papers.structure_mask_image(depth, planes, fx, fy, cx, cy)
        support_image = papers.structure_mask_image(depth, planes, fx, fy, cx, cy, key="support")
        image = mosaic(frame, records, structure, support_image)
        if process is None:
            process = open_ffmpeg(out_path, image.shape[1], image.shape[0], PLAY_FPS)
        raw = np.ascontiguousarray(image).tobytes()
        for _ in range(repeats):
            process.stdin.write(raw)
        stats["samples"] += 1
        stats["boxes"] += len(records)
        if any(plane["support"] for plane in planes):
            stats["support_frames"] += 1
        if any(plane["structure"] for plane in planes):
            stats["structure_frames"] += 1
        for record in records:
            left, top, right, bottom = record["inner_xyxy"]
            crop = depth[top:bottom, left:right]
            smooth = smooth_ratio(crop)
            second = second_share(crop)
            if smooth is not None and smooth >= 0.50:
                stats["smooth_ge_half"] += 1
            if second is not None and second >= SECOND_MODE_MIN:
                stats["second_mode"] += 1
        log(f"{video.stem} {stats['samples']}/{len(indices)}")
    capture.release()
    if process is None:
        raise SystemExit(f"no frames in {video}")
    process.stdin.close()
    code = process.wait()
    if code != 0:
        raise SystemExit(f"ffmpeg exited {code}")
    stats["video"] = str(out_path)
    log(f"wrote {out_path}")
    return stats


def main():
    videos = obs.video_list(None, obs.VIDEO_DIR)
    if not videos:
        raise SystemExit("no videos")
    detector = obs.load_detector()
    depth_model = obs.load_depth_model()
    rng = np.random.default_rng(0)
    rows = []
    for video in videos:
        rows.append(render_video(video, depth_model, detector, rng))
    document = {
        "schema": "video_trials_v1",
        "sample_fps": SAMPLE_FPS,
        "long_sample_fps": LONG_SAMPLE_FPS,
        "play_fps": PLAY_FPS,
        "grad_max": GRAD_MAX,
        "second_mode_min": SECOND_MODE_MIN,
        "videos": rows,
        "totals": {
            "boxes": sum(row["boxes"] for row in rows),
            "smooth_ge_half": sum(row["smooth_ge_half"] for row in rows),
            "second_mode": sum(row["second_mode"] for row in rows),
            "support_frames": sum(row["support_frames"] for row in rows),
            "structure_frames": sum(row["structure_frames"] for row in rows),
            "samples": sum(row["samples"] for row in rows),
        },
    }
    TRIAL_PATH.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    log(f"wrote {TRIAL_PATH} {document['totals']}")


if __name__ == "__main__":
    sys.exit(main())
