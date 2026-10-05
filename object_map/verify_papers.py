#!/usr/bin/env python3
"""同じフレームで、論文の観測と深度一致を比べる。

QuadricSLAM は箱だけでは楕円体の大きさが決まらない。
Liao らは支持平面を除いた点を物体にする。
CubeSLAM は消失点から直方体を提案する。
Kimera は広い面を壁や床として、家具と分ける。
ここでは各論文の最適化器は回さず、その観測がこの映像で成立するかを数える。
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_objects as obs

# USER_SETTINGS
FOCAL_RATIO = 0.90  # 校正が無い映像の fx。画像の幅に掛ける
MINI3_YAML = Path("mini3_calib/out/mini3.yaml")  # Mini 3 の実測焦点。この映像だけ使う
PLANE_BAND = 0.05  # 平面までの距離。その点群の深度中央値に掛ける
PLANE_ITERS = 40  # RANSAC の回数
PLANE_KEEP = 3  # 1枚から取る平面の数
POINT_LIMIT = 6000  # 平面推定に使う点数
POINT_STRIDE = 4  # 平面推定の画素間隔
SUPPORT_ANGLE_DEG = 10.0  # Liao ら。重力方向との角度がこれ未満を支持平面にする
STRUCTURE_MIN = 0.12  # Kimera の構造。画像のこの割合以上を占める面
PLANAR_AXIS = 0.20  # 厚み / 長辺。これ未満は楕円体ではなく平面
VP_MIN_LINES = 12  # 1点に交わる直線の本数。これ未満は消失点にしない
VP_AIM_DEG = 3.0  # 直線の向きと消失点への方向の許容角
FIGURE_DIR = Path("agent_reports/20261006_object_map/figures")  # 比較画像。Git に残す
SUMMARY_PATH = Path(
    "agent_reports/20261006_object_map/paper_verify.yaml"
)  # 論文ごとの集計。Git に残す
FIGURE_SOURCES = (
    "20261002_001816",
    "004_8lz3Qs23cMg",
    "015_pexels",
    "003_HtFq9C_vbOc",
)  # 比較画像にする映像


def log(message):
    print(message, flush=True)


def camera_for(width, height, source):
    if "20261002_001816" in str(source) and MINI3_YAML.is_file():
        text = MINI3_YAML.read_text(encoding="utf-8")

        def grab(key):
            for line in text.splitlines():
                if line.startswith(key + ":"):
                    return float(line.split(":", 1)[1].strip())
            raise SystemExit(f"missing {key}")

        scale_x = width / grab("Camera.width")
        scale_y = height / grab("Camera.height")
        return (
            grab("Camera1.fx") * scale_x,
            grab("Camera1.fy") * scale_y,
            grab("Camera1.cx") * scale_x,
            grab("Camera1.cy") * scale_y,
        )
    focal = FOCAL_RATIO * width
    return focal, focal, width / 2.0, height / 2.0


def sample_points(depth, fx, fy, cx, cy, rng):
    vs = np.arange(0, depth.shape[0], POINT_STRIDE)
    us = np.arange(0, depth.shape[1], POINT_STRIDE)
    grid_u, grid_v = np.meshgrid(us, vs)
    z = depth[grid_v, grid_u]
    valid = np.isfinite(z) & (z > 1e-6)
    grid_u = grid_u[valid]
    grid_v = grid_v[valid]
    z = z[valid]
    if z.size == 0:
        return np.zeros((0, 3), dtype=np.float64)
    if z.size > POINT_LIMIT:
        pick = rng.choice(z.size, POINT_LIMIT, replace=False)
        grid_u, grid_v, z = grid_u[pick], grid_v[pick], z[pick]
    x = (grid_u - cx) * z / fx
    y = (grid_v - cy) * z / fy
    return np.stack([x, y, z], axis=1)


def fit_plane(points, band, rng):
    count = int(points.shape[0])
    if count < 30:
        return None
    median_z = float(np.median(points[:, 2]))
    thresh = max(band * median_z, 1e-6)
    best = None
    best_count = 0
    for _ in range(PLANE_ITERS):
        choice = rng.choice(count, 3, replace=False)
        p0, p1, p2 = points[choice]
        normal = np.cross(p1 - p0, p2 - p0)
        length = float(np.linalg.norm(normal))
        if length < 1e-8:
            continue
        normal = normal / length
        offset = float(-np.dot(normal, p0))
        distance = np.abs(points @ normal + offset)
        inliers = distance < thresh
        inlier_count = int(inliers.sum())
        if inlier_count > best_count:
            best_count = inlier_count
            best = (normal, offset, inliers)
    if best is None or best_count < 30:
        return None
    return best


def plane_angles(normal):
    up = np.array([0.0, -1.0, 0.0])
    cosine = float(np.clip(abs(np.dot(normal, up)), 0.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))


def sequential_planes(points, rng):
    remaining = points
    planes = []
    for _ in range(PLANE_KEEP):
        found = fit_plane(remaining, PLANE_BAND, rng)
        if found is None:
            break
        normal, offset, inliers = found
        planes.append(
            {
                "normal": normal,
                "offset": offset,
                "sample_ratio": float(inliers.mean()),
                "angle_deg": round(plane_angles(normal), 2),
            }
        )
        remaining = remaining[~inliers]
        if remaining.shape[0] < 30:
            break
    return planes


def coverage(depth, plane, fx, fy, cx, cy):
    vs = np.arange(0, depth.shape[0], POINT_STRIDE)
    us = np.arange(0, depth.shape[1], POINT_STRIDE)
    grid_u, grid_v = np.meshgrid(us, vs)
    z = depth[grid_v, grid_u]
    valid = np.isfinite(z) & (z > 1e-6)
    if int(valid.sum()) < 30:
        return 0.0
    z_valid = z[valid]
    thresh = max(PLANE_BAND * float(np.median(z_valid)), 1e-6)
    x = (grid_u[valid] - cx) * z_valid / fx
    y = (grid_v[valid] - cy) * z_valid / fy
    normal, offset = plane["normal"], plane["offset"]
    distance = np.abs(x * normal[0] + y * normal[1] + z_valid * normal[2] + offset)
    return float((distance < thresh).mean())


def box_masks(depth, box, planes, fx, fy, cx, cy):
    left, top, right, bottom = box
    z = depth[top:bottom, left:right]
    valid = np.isfinite(z) & (z > 1e-6)
    our_ratio, _median, our_mask = obs.dominant_depth(z, obs.DEPTH_REL_TOL)
    empty = np.zeros(z.shape, dtype=bool)
    if int(valid.sum()) < 30:
        return our_ratio, our_mask, empty, empty, None
    ys, xs = np.mgrid[top:bottom, left:right]
    x = (xs - cx) * z / fx
    y = (ys - cy) * z / fy
    median_z = float(np.median(z[valid]))
    thresh = max(PLANE_BAND * median_z, 1e-6)
    support = empty.copy()
    structure = empty.copy()
    for plane in planes:
        normal = plane["normal"]
        distance = np.abs(x * normal[0] + y * normal[1] + z * normal[2] + plane["offset"])
        on_plane = valid & (distance < thresh)
        if plane["structure"]:
            structure |= on_plane
        if plane["support"]:
            support |= on_plane
    return our_ratio, our_mask, support, structure, z


def axis_ratio(depth, mask, box, fx, fy, cx, cy):
    left, top, _right, _bottom = box
    if int(mask.sum()) < 30:
        return None
    ys, xs = np.nonzero(mask)
    z = depth[top:top + mask.shape[0], left:left + mask.shape[1]][ys, xs]
    valid = np.isfinite(z) & (z > 1e-6)
    if int(valid.sum()) < 30:
        return None
    points = np.stack(
        [
            (xs[valid] + left - cx) * z[valid] / fx,
            (ys[valid] + top - cy) * z[valid] / fy,
            z[valid],
        ],
        axis=1,
    )
    centered = points - points.mean(axis=0)
    values = np.linalg.eigvalsh(centered.T @ centered / points.shape[0])
    values = np.sqrt(np.maximum(values, 0.0))
    if values[2] < 1e-8:
        return None
    return float(values[0] / values[2])


def line_intersection(a, b):
    x1, y1, x2, y2 = [float(value) for value in a]
    x3, y3, x4, y4 = [float(value) for value in b]
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-6:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / den
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / den
    return px, py


def aims_at(segment, point):
    x1, y1, x2, y2 = [float(value) for value in segment]
    dx, dy = x2 - x1, y2 - y1
    length = float(np.hypot(dx, dy))
    vx, vy = point[0] - (x1 + x2) * 0.5, point[1] - (y1 + y2) * 0.5
    toward = float(np.hypot(vx, vy))
    if length < 1.0 or toward < 1.0:
        return False
    sine = abs(dx * vy - dy * vx) / (length * toward)
    return sine < np.sin(np.deg2rad(VP_AIM_DEG))


def vanishing_count(gray, rng):
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 50, minLineLength=40, maxLineGap=6)
    if lines is None:
        return 0
    remaining = [segment for segment in lines[:, 0]]
    if len(remaining) > 80:
        remaining = remaining[:80]
    height, width = gray.shape[:2]
    peaks = 0
    for _ in range(2):
        count = len(remaining)
        if count < VP_MIN_LINES:
            break
        best_votes = 0
        best_inliers = None
        trials = min(60, count * (count - 1) // 2)
        for _trial in range(trials):
            i, j = rng.choice(count, 2, replace=False)
            point = line_intersection(remaining[i], remaining[j])
            if point is None:
                continue
            if abs(point[0]) > width * 6 or abs(point[1]) > height * 6:
                continue
            inliers = [index for index, segment in enumerate(remaining) if aims_at(segment, point)]
            if len(inliers) > best_votes:
                best_votes = len(inliers)
                best_inliers = inliers
        if best_inliers is None or best_votes < VP_MIN_LINES:
            break
        peaks += 1
        drop = set(best_inliers)
        remaining = [segment for index, segment in enumerate(remaining) if index not in drop]
    return peaks


def iou(a, b):
    union = int(np.count_nonzero(a | b))
    if union == 0:
        return None
    return float(np.count_nonzero(a & b) / union)


def match_pairs(frames):
    grouped = {}
    for frame in frames:
        grouped.setdefault(frame["source"], []).append(frame["records"])
    pairs = 0
    for records in grouped.values():
        if len(records) < 2:
            continue
        used = set()
        for left in records[0]:
            best_iou = 0.1
            best_index = None
            for index, right in enumerate(records[1]):
                if index in used or left["class_name"] != right["class_name"]:
                    continue
                overlap = box_iou(left["bbox_xyxy"], right["bbox_xyxy"])
                if overlap > best_iou:
                    best_iou = overlap
                    best_index = index
            if best_index is not None:
                used.add(best_index)
                pairs += 1
    return pairs


def box_iou(a, b):
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area += max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area - inter
    if union <= 0:
        return 0.0
    return inter / union


def draw_mask(frame, mask, color):
    image = frame.copy()
    tint = image.copy()
    tint[mask] = color
    return cv2.addWeighted(image, 0.4, tint, 0.6, 0)


def save_figure(frame, records, structure_mask, path):
    our = np.zeros(frame.shape[:2], dtype=bool)
    support = np.zeros(frame.shape[:2], dtype=bool)
    canvas = frame.copy()
    for record in records:
        left, top, right, bottom = record["inner_xyxy"]
        our[top:bottom, left:right] = record["our_mask"]
        support[top:bottom, left:right] = record["support_mask"]
        color = (40, 160, 40) if record["on_structure"] else (0, 140, 220)
        cv2.rectangle(canvas, (left, top), (right, bottom), color, 2)
    panels = [
        canvas,
        draw_mask(frame, our, (40, 180, 40)),
        draw_mask(frame, support, (200, 80, 40)),
        draw_mask(frame, structure_mask, (180, 180, 40)),
    ]
    height = 360
    resized = []
    for panel in panels:
        scale = height / panel.shape[0]
        resized.append(cv2.resize(panel, (int(panel.shape[1] * scale), height)))
    titles = ("boxes", "depth agree", "support plane", "large plane")
    labeled = []
    for panel, title in zip(resized, titles):
        cv2.putText(panel, title, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        labeled.append(panel)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.hstack(labeled))


def structure_mask_image(depth, planes, fx, fy, cx, cy, key="structure"):
    mask = np.zeros(depth.shape, dtype=bool)
    chosen = [plane for plane in planes if plane[key]]
    if not chosen:
        return mask
    stride = 2
    vs = np.arange(0, depth.shape[0], stride)
    us = np.arange(0, depth.shape[1], stride)
    grid_u, grid_v = np.meshgrid(us, vs)
    z = depth[grid_v, grid_u]
    valid = np.isfinite(z) & (z > 1e-6)
    if not valid.any():
        return mask
    median_z = float(np.median(z[valid]))
    thresh = max(PLANE_BAND * median_z, 1e-6)
    x = (grid_u - cx) * z / fx
    y = (grid_v - cy) * z / fy
    on_any = np.zeros(z.shape, dtype=bool)
    for plane in chosen:
        normal = plane["normal"]
        distance = np.abs(x * normal[0] + y * normal[1] + z * normal[2] + plane["offset"])
        on_any |= valid & (distance < thresh)
    mask[grid_v, grid_u] = on_any
    kernel = np.ones((stride, stride), dtype=np.uint8)
    return cv2.dilate(mask.astype(np.uint8), kernel).astype(bool)


def verify_frame(frame, depth, detections, source, fx, fy, cx, cy, rng):
    points = sample_points(depth, fx, fy, cx, cy, rng)
    planes = sequential_planes(points, rng)
    for plane in planes:
        ratio = coverage(depth, plane, fx, fy, cx, cy)
        plane["coverage"] = round(ratio, 4)
        plane["support"] = plane["angle_deg"] <= SUPPORT_ANGLE_DEG
        plane["structure"] = ratio >= STRUCTURE_MIN
    records = []
    for detection in detections:
        inner = obs.shrink_box(detection["bbox_xyxy"], obs.BBOX_SHRINK, depth.shape[1], depth.shape[0])
        if inner is None:
            continue
        area = (inner[2] - inner[0]) * (inner[3] - inner[1])
        if area < obs.MIN_BOX_PIXELS:
            continue
        our_ratio, our_mask, support_mask, structure_box, _z = box_masks(
            depth, inner, planes, fx, fy, cx, cy
        )
        ratio = axis_ratio(depth, our_mask, inner, fx, fy, cx, cy)
        overlap = iou(our_mask, structure_box)
        records.append(
            {
                "class_name": detection["class_name"],
                "bbox_xyxy": detection["bbox_xyxy"],
                "inner_xyxy": list(inner),
                "our_ratio": round(float(our_ratio), 4),
                "support_ratio": round(float(support_mask.mean()), 4),
                "structure_iou": None if overlap is None else round(overlap, 4),
                "on_structure": overlap is not None and overlap >= 0.70,
                "axis_ratio": None if ratio is None else round(ratio, 4),
                "planar": ratio is not None and ratio < PLANAR_AXIS,
                "our_mask": our_mask,
                "support_mask": support_mask,
            }
        )
    return planes, records


def summarize(frames):
    boxes = [record for frame in frames for record in frame["records"]]
    eligible = [record for record in boxes if record["axis_ratio"] is not None]
    planar = sum(1 for record in eligible if record["planar"])
    thickness = sorted(record["axis_ratio"] for record in eligible)
    on_structure = sum(1 for record in boxes if record["on_structure"])
    support_frames = sum(1 for frame in frames if any(plane["support"] for plane in frame["planes"]))
    structure_frames = sum(1 for frame in frames if any(plane["structure"] for plane in frame["planes"]))
    vp2 = sum(1 for frame in frames if frame["vanishing_points"] >= 2)
    vp1 = sum(1 for frame in frames if frame["vanishing_points"] >= 1)
    touched = [record for record in boxes if record["support_ratio"] >= 0.20]
    return {
        "schema": "paper_verify_v1",
        "frames": len(frames),
        "detections": len(boxes),
        "quadricslam": {
            "citation": "Nicholson, Milford, Suenderhauf, RA-L 2019",
            "two_view_pairs": match_pairs(frames),
            "boxes_with_axes": len(eligible),
            "thickness_median": None if not thickness else round(thickness[len(thickness) // 2], 4),
            "planar_boxes": planar,
            "volumetric_boxes": len(eligible) - planar,
        },
        "liao2020": {
            "citation": "Liao, Wang, Qi, Zhang, Sensors 2020",
            "frames_with_support_plane": support_frames,
            "boxes_touching_support": len(touched),
        },
        "cubeslam": {
            "citation": "Yang, Scherer, TRO 2019",
            "frames_with_vanishing_point": vp1,
            "frames_with_two_vanishing_points": vp2,
        },
        "kimera": {
            "citation": "Rosinol et al., IJRR 2021",
            "frames_with_structure_plane": structure_frames,
            "boxes_on_structure": on_structure,
        },
    }


def public_frame(frame):
    return {
        "source": frame["source"],
        "frame_index": frame["frame_index"],
        "vanishing_points": frame["vanishing_points"],
        "planes": [
            {
                "angle_deg": plane["angle_deg"],
                "coverage": plane["coverage"],
                "support": plane["support"],
                "structure": plane["structure"],
            }
            for plane in frame["planes"]
        ],
        "detections": [
            {key: value for key, value in record.items() if key not in ("our_mask", "support_mask")}
            for record in frame["records"]
        ],
    }


def self_check():
    rng = np.random.default_rng(0)
    plane_points = np.zeros((80, 3))
    plane_points[:, 0] = rng.uniform(-1, 1, 80)
    plane_points[:, 2] = rng.uniform(1, 3, 80)
    plane_points[:, 1] = 1.5
    outliers = rng.uniform(-1, 1, (20, 3))
    outliers[:, 2] += 2
    found = fit_plane(np.vstack([plane_points, outliers]), 0.05, rng)
    assert found is not None
    _normal, _offset, inliers = found
    assert int(inliers.sum()) >= 70
    assert plane_angles(np.array([0.0, -1.0, 0.0])) < 1.0
    assert plane_angles(np.array([0.0, 0.0, 1.0])) > 80.0
    assert box_iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    log("self-check ok")


def main():
    self_check()
    videos = obs.video_list(None, obs.VIDEO_DIR)
    if not videos:
        raise SystemExit("no videos")
    detector = obs.load_detector()
    depth_model = obs.load_depth_model()
    rng = np.random.default_rng(0)
    frames = []
    for video in videos:
        capture = cv2.VideoCapture(str(video))
        if not capture.isOpened():
            raise SystemExit(f"cannot open {video}")
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        indices = obs.sample_indices(frame_count, obs.SAMPLE_COUNT)
        log(f"{video} sample={indices}")
        for index in indices:
            frame = obs.read_frame(capture, index)
            if frame is None:
                continue
            depth = obs.infer_depth(depth_model, frame)
            fx, fy, cx, cy = camera_for(frame.shape[1], frame.shape[0], video)
            planes, records = verify_frame(
                frame, depth, obs.detect(detector, frame), video, fx, fy, cx, cy, rng
            )
            document = {
                "source": str(video),
                "frame_index": index,
                "vanishing_points": vanishing_count(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), rng),
                "planes": planes,
                "records": records,
            }
            frames.append(document)
            if any(name in video.stem for name in FIGURE_SOURCES):
                mask = structure_mask_image(depth, planes, fx, fy, cx, cy)
                save_figure(
                    frame,
                    records,
                    mask,
                    FIGURE_DIR / f"{video.stem}_f{index:06d}.jpg",
                )
            log(
                f"frame {index} boxes={len(records)} "
                f"planes={len(planes)} vp={document['vanishing_points']}"
            )
        capture.release()
    summary = summarize(frames)
    summary["frames_detail"] = [public_frame(frame) for frame in frames]
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        yaml.safe_dump(summary, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    log(
        f"wrote {SUMMARY_PATH} detections={summary['detections']} "
        f"planar={summary['quadricslam']['planar_boxes']} "
        f"support_frames={summary['liao2020']['frames_with_support_plane']} "
        f"vp2={summary['cubeslam']['frames_with_two_vanishing_points']} "
        f"on_structure={summary['kimera']['boxes_on_structure']}"
    )


if __name__ == "__main__":
    sys.exit(main())
