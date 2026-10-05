#!/usr/bin/env python3
"""1フレームの検出箱と深度の一致から、物体観測の YAML を書く。

世界座標には載せない。オフラインの地図とリアルタイムの自己位置は、
あとで同じ観測を使う。深度は DA3-SMALL の相対値で、メートルではない。
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

# USER_SETTINGS
VIDEO = Path(
    "mini3_bridge/pc/recordings/20261002_001816.mp4"
)  # 引数を省略したときの Mini 3 映像
VIDEO_DIR = Path("object_map/videos")  # ネットから取った室内映像
OUT_DIR = Path("object_map/out")  # フレームごとの YAML と重ね画像
MODEL_ID = "depth-anything/DA3-SMALL"  # 深度。overlay.py と同じ単眼モデル
PROCESS_RES = 504  # モデルに入れる長辺。overlay.py と同じ
DETECT_WEIGHTS = "yolo11n.pt"  # COCO の箱。重みは object_map/weights に置く
DETECT_IMGSZ = 640  # 検出器に入れる辺
CONF_MIN = 0.25  # 検出の最低スコア
SAMPLE_COUNT = 2  # 1本から等間隔で取るフレーム数
DEPTH_AGREE_MIN = 0.50  # 箱の内側で深度が揃った画素の割合。これ未満は物体にしない
DEPTH_REL_TOL = 0.15  # 採用判定に使う相対差。この中を「おおよそ一致」とする
DEPTH_REL_TOLS = (0.05, 0.10, 0.15)  # 比べる相対差。採用判定は DEPTH_REL_TOL だけを使う
BBOX_SHRINK = 0.10  # 箱の縁は背景が混ざるので、各辺この割合だけ内側を見る
MIN_BOX_PIXELS = 400  # 内側の面積がこれ未満の箱は割合が不安定なので捨てる
DYNAMIC_CLASSES = ("person", "dog", "cat", "bird")  # 動くもの。深度が揃っても地図の静止物にはしない
SCHEMA = "object_observation_v1"  # この観測 YAML の版


def log(message):
    print(message, flush=True)


def dominant_depth(crop, rel_tol):
    """最も多くの画素が収まる相対幅の深度を探す。

    戻り値は (割合, その画素の深度中央値, 一致マスク)。
    割合の分母は、有限で正の深度を持つ画素である。
    """
    finite = np.isfinite(crop) & (crop > 1e-6)
    values = crop[finite]
    count = int(values.size)
    empty = np.zeros(crop.shape, dtype=bool)
    if count == 0:
        return 0.0, None, empty
    logs = np.log(values.astype(np.float64))
    order = np.argsort(logs)
    sorted_logs = logs[order]
    width = float(np.log((1.0 + rel_tol) / (1.0 - rel_tol)))
    start = 0
    best = 1
    best_start = 0
    best_stop = 0
    for stop in range(count):
        while sorted_logs[stop] - sorted_logs[start] > width:
            start += 1
        length = stop - start + 1
        if length > best:
            best = length
            best_start = start
            best_stop = stop
    chosen = np.zeros(count, dtype=bool)
    chosen[order[best_start : best_stop + 1]] = True
    mask = empty.copy()
    mask[finite] = chosen
    median = float(np.exp(np.median(sorted_logs[best_start : best_stop + 1])))
    return best / count, median, mask


def component_count(mask):
    if mask is None or int(np.count_nonzero(mask)) == 0:
        return 0
    count, _labels = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
    return int(count - 1)


def shrink_box(box, shrink, width, height):
    x1, y1, x2, y2 = [float(value) for value in box]
    dx = (x2 - x1) * shrink * 0.5
    dy = (y2 - y1) * shrink * 0.5
    left = max(0, min(width - 1, int(np.floor(x1 + dx))))
    top = max(0, min(height - 1, int(np.floor(y1 + dy))))
    right = max(0, min(width, int(np.ceil(x2 - dx))))
    bottom = max(0, min(height, int(np.ceil(y2 - dy))))
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def sample_indices(frame_count, sample_count):
    if frame_count <= 0 or sample_count <= 0:
        return []
    count = min(sample_count, frame_count)
    if count == 1:
        return [frame_count // 2]
    indices = []
    for position in range(count):
        index = int(round((position + 0.5) * (frame_count - 1) / count))
        index = max(0, min(frame_count - 1, index))
        if index not in indices:
            indices.append(index)
    return indices


def read_frame(capture, index):
    capture.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = capture.read()
    if not ok:
        return None
    return frame


def load_depth_model():
    import torch
    from depth_anything_3.api import DepthAnything3

    torch.set_num_threads(max(1, torch.get_num_threads()))
    log(f"loading {MODEL_ID}")
    model = DepthAnything3.from_pretrained(MODEL_ID).to("cpu")
    model.eval()
    return model


def infer_depth(model, frame_bgr):
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    prediction = model.inference(
        image=[rgb],
        process_res=PROCESS_RES,
        process_res_method="upper_bound_resize",
    )
    depth = np.asarray(prediction.depth[0], dtype=np.float32)
    height, width = frame_bgr.shape[:2]
    if depth.shape != (height, width):
        depth = cv2.resize(depth, (width, height), interpolation=cv2.INTER_LINEAR)
    return depth


def load_detector():
    from ultralytics import YOLO

    weights = Path(__file__).resolve().parent / "weights" / DETECT_WEIGHTS
    log(f"loading {weights}")
    return YOLO(str(weights))


def detect(model, frame_bgr):
    found = model.predict(
        frame_bgr,
        imgsz=DETECT_IMGSZ,
        conf=CONF_MIN,
        verbose=False,
    )[0]
    names = found.names
    boxes = []
    if found.boxes is None:
        return boxes
    for box in found.boxes:
        xyxy = [float(value) for value in box.xyxy[0].tolist()]
        class_id = int(box.cls[0])
        boxes.append(
            {
                "class_name": str(names[class_id]),
                "score": float(box.conf[0]),
                "bbox_xyxy": [round(value, 1) for value in xyxy],
            }
        )
    return boxes


def observe_box(depth, detection):
    height, width = depth.shape[:2]
    inner = shrink_box(detection["bbox_xyxy"], BBOX_SHRINK, width, height)
    record = {
        "class_name": detection["class_name"],
        "score": round(detection["score"], 4),
        "dynamic": detection["class_name"] in DYNAMIC_CLASSES,
        "bbox_xyxy": detection["bbox_xyxy"],
        "inner_xyxy": list(inner) if inner is not None else None,
        "depth_median": None,
        "depth_agree_ratio": None,
        "agree_by_tol": None,
        "components_by_tol": None,
        "centroid_xy": None,
        "accepted": False,
        "reason": "empty_depth",
    }
    if inner is None:
        record["reason"] = "small_box"
        return record
    left, top, right, bottom = inner
    area = (right - left) * (bottom - top)
    crop = depth[top:bottom, left:right]
    agree_by_tol = {}
    components_by_tol = {}
    ratio, median, mask = 0.0, None, None
    for tol in DEPTH_REL_TOLS:
        tol_ratio, tol_median, tol_mask = dominant_depth(crop, tol)
        key = f"{tol:.2f}"
        agree_by_tol[key] = round(float(tol_ratio), 4)
        components_by_tol[key] = component_count(tol_mask)
        if abs(tol - DEPTH_REL_TOL) < 1e-9:
            ratio, median, mask = tol_ratio, tol_median, tol_mask
    record["agree_by_tol"] = agree_by_tol
    record["components_by_tol"] = components_by_tol
    record["depth_agree_ratio"] = round(float(ratio), 4)
    if median is not None:
        record["depth_median"] = round(float(median), 4)
        ys, xs = np.nonzero(mask)
        if len(xs) > 0:
            record["centroid_xy"] = [
                round(float(xs.mean()) + left, 1),
                round(float(ys.mean()) + top, 1),
            ]
    if area < MIN_BOX_PIXELS:
        record["reason"] = "small_box"
        return record
    if median is None:
        record["reason"] = "empty_depth"
        return record
    if ratio >= DEPTH_AGREE_MIN:
        record["accepted"] = True
        record["reason"] = "agree"
        return record
    record["reason"] = "depth_split"
    return record


def draw(frame, records):
    image = frame.copy()
    for record in records:
        box = record["inner_xyxy"] or record["bbox_xyxy"]
        x1, y1, x2, y2 = [int(round(value)) for value in box]
        color = (40, 160, 40) if record["accepted"] else (0, 120, 220)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        ratio = record["depth_agree_ratio"]
        ratio_text = "none" if ratio is None else f"{ratio:.0%}"
        label = f"{record['class_name']} {ratio_text} {record['reason']}"
        cv2.putText(
            image,
            label,
            (x1, max(16, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )
    return image


def frame_document(source, index, time_s, frame_shape, records):
    height, width = frame_shape[:2]
    return {
        "schema": SCHEMA,
        "source": str(source),
        "frame_index": int(index),
        "time_s": None if time_s is None else round(float(time_s), 3),
        "width": int(width),
        "height": int(height),
        "depth_model": MODEL_ID,
        "depth_unit": "relative",
        "detector": DETECT_WEIGHTS,
        "depth_rel_tol": DEPTH_REL_TOL,
        "depth_agree_min": DEPTH_AGREE_MIN,
        "bbox_shrink": BBOX_SHRINK,
        "detections": records,
    }


def write_yaml(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def video_list(videos, video_dir):
    if videos:
        return [Path(video) for video in videos]
    found = []
    if VIDEO.is_file():
        found.append(VIDEO)
    if video_dir.is_dir():
        found.extend(sorted(video_dir.glob("*.mp4")))
    return found


def process_video(video, depth_model, detector, sample_count, out_dir):
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise SystemExit(f"cannot open {video}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    indices = sample_indices(frame_count, sample_count)
    log(f"{video} frames={frame_count} fps={fps:.2f} sample={indices}")
    stem = video.stem
    written = []
    for index in indices:
        frame = read_frame(capture, index)
        if frame is None:
            log(f"skip unreadable frame {index}")
            continue
        depth = infer_depth(depth_model, frame)
        records = [observe_box(depth, detection) for detection in detect(detector, frame)]
        time_s = None if fps <= 0 else index / fps
        document = frame_document(video, index, time_s, frame.shape, records)
        out_yaml = out_dir / stem / f"f{index:06d}.yaml"
        out_image = out_dir / stem / f"f{index:06d}.jpg"
        write_yaml(out_yaml, document)
        cv2.imwrite(str(out_image), draw(frame, records))
        accepted = sum(1 for record in records if record["accepted"])
        log(f"wrote {out_yaml} detections={len(records)} accepted={accepted}")
        written.append(document)
    capture.release()
    return written


def summarize(documents):
    by_class = {}
    reasons = {}
    for document in documents:
        for record in document["detections"]:
            name = record["class_name"]
            bucket = by_class.setdefault(
                name,
                {"detections": 0, "accepted": 0, "ratios": []},
            )
            bucket["detections"] += 1
            if record["accepted"]:
                bucket["accepted"] += 1
            if record["depth_agree_ratio"] is not None:
                bucket["ratios"].append(record["depth_agree_ratio"])
            reason = record["reason"]
            reasons[reason] = reasons.get(reason, 0) + 1
    classes = {}
    for name in sorted(by_class):
        bucket = by_class[name]
        ratios = bucket["ratios"]
        classes[name] = {
            "detections": bucket["detections"],
            "accepted": bucket["accepted"],
            "agree_ratio_median": (
                None if not ratios else round(float(np.median(ratios)), 4)
            ),
        }
    detection_count = sum(item["detections"] for item in classes.values())
    accepted_count = sum(item["accepted"] for item in classes.values())
    eligible = 0
    accepted_if_tol = {f"{tol:.2f}": 0 for tol in DEPTH_REL_TOLS}
    one_component_at_005 = 0
    passed_005 = 0
    for document in documents:
        for record in document["detections"]:
            ratios = record.get("agree_by_tol") or {}
            if record["reason"] == "small_box" or not ratios:
                continue
            eligible += 1
            for key, ratio in ratios.items():
                if ratio >= DEPTH_AGREE_MIN and key in accepted_if_tol:
                    accepted_if_tol[key] += 1
            if ratios.get("0.05", 0.0) >= DEPTH_AGREE_MIN:
                passed_005 += 1
                components = (record.get("components_by_tol") or {}).get("0.05")
                if components == 1:
                    one_component_at_005 += 1
    return {
        "schema": "object_observation_summary_v1",
        "frames": len(documents),
        "detections": detection_count,
        "accepted": accepted_count,
        "eligible": eligible,
        "accepted_if_tol": accepted_if_tol,
        "passed_rel_0.05": passed_005,
        "one_component_at_rel_0.05": one_component_at_005,
        "reasons": reasons,
        "by_class": classes,
    }


def self_check():
    uniform = np.full((8, 8), 2.0, dtype=np.float32)
    ratio, median, mask = dominant_depth(uniform, DEPTH_REL_TOL)
    assert ratio == 1.0 and abs(median - 2.0) < 1e-6 and mask.all()

    split = np.concatenate(
        [np.full((6, 10), 1.0), np.full((4, 10), 5.0)],
        axis=0,
    ).astype(np.float32)
    ratio, median, mask = dominant_depth(split, 0.15)
    assert abs(ratio - 0.6) < 1e-6, ratio
    assert abs(median - 1.0) < 1e-6
    assert int(mask.sum()) == 60

    near = np.concatenate(
        [np.full((5, 4), 1.0), np.full((5, 4), 1.1)],
        axis=0,
    ).astype(np.float32)
    ratio, median, _mask = dominant_depth(near, 0.15)
    assert ratio == 1.0, ratio
    assert 1.0 <= median <= 1.1

    empty = np.zeros((3, 3), dtype=np.float32)
    ratio, median, mask = dominant_depth(empty, 0.15)
    assert ratio == 0.0 and median is None and not mask.any()

    rng = np.random.default_rng(0)
    width = float(np.log((1.0 + 0.15) / (1.0 - 0.15)))
    for _ in range(30):
        values = rng.uniform(0.2, 8.0, size=40).astype(np.float32)
        ratio, _median, _mask = dominant_depth(values.reshape(5, 8), 0.15)
        logs = np.sort(np.log(values.astype(np.float64)))
        best = 1
        for start in range(len(logs)):
            stop = start
            while stop < len(logs) and logs[stop] - logs[start] <= width:
                best = max(best, stop - start + 1)
                stop += 1
        assert abs(ratio - best / len(logs)) < 1e-6

    box = shrink_box([10, 20, 110, 220], 0.10, 200, 300)
    assert box == (15, 30, 105, 210)
    assert shrink_box([0, 0, 4, 4], 1.0, 10, 10) is None
    pieces = np.zeros((10, 10), dtype=bool)
    pieces[0:2, 0:2] = True
    pieces[8:10, 8:10] = True
    assert component_count(pieces) == 2
    assert component_count(np.ones((4, 4), dtype=bool)) == 1
    assert component_count(np.zeros((4, 4), dtype=bool)) == 0
    assert sample_indices(100, 2) == [25, 74]
    log("self-check ok")


def main():
    parser = argparse.ArgumentParser(description="検出箱の深度一致から物体観測 YAML を書く")
    parser.add_argument("--video", action="append", default=None)
    parser.add_argument("--video-dir", type=Path, default=VIDEO_DIR)
    parser.add_argument("--sample-count", type=int, default=SAMPLE_COUNT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return
    videos = video_list(args.video, args.video_dir)
    if not videos:
        raise SystemExit("no videos")
    self_check()
    detector = load_detector()
    depth_model = load_depth_model()
    documents = []
    for video in videos:
        if not video.is_file():
            raise SystemExit(f"missing {video}")
        documents.extend(
            process_video(video, depth_model, detector, args.sample_count, args.out_dir)
        )
    summary = summarize(documents)
    summary_path = args.out_dir / "summary.yaml"
    write_yaml(summary_path, summary)
    log(f"wrote {summary_path} frames={summary['frames']} accepted={summary['accepted']}")


if __name__ == "__main__":
    sys.exit(main())
