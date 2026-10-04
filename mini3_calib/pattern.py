"""Asymmetric circle grid sized to a monitor panel."""

import math

import cv2
import numpy as np

# USER_SETTINGS
COLS = 4                    # 1行の円の数。OpenCV の patternSize の幅
ROWS = 5                    # 行数。OpenCV の patternSize の高さ
RADIUS_RATIO = 0.42         # 円の半径。中心間隔に対する割合。隣の円と重ならない
MARGIN = 0.06               # 画面の各辺に空ける余白。パネル寸法に対する割合
MM_PER_INCH = 25.4          # 1インチのミリメートル
CIRCLE_COLOR = 255          # 描く円の輝度。白
BLOB_COLOR = 255            # 検出する円の輝度。白
BLOB_MIN_AREA = 40          # 検出する円の最小面積（画素）
BLOB_MAX_AREA = 80000       # 検出する円の最大面積（画素）
BLOB_MIN_CIRCULARITY = 0.6  # 円らしい形とみなす下限
BLOB_MIN_INERTIA = 0.3      # 細長い塊を捨てる下限
BLOB_MIN_CONVEXITY = 0.8    # 欠けた塊を捨てる下限


def object_points(cols, rows, spacing_mm):
    """Circle centers in millimetres on the panel plane. Matches OpenCV."""
    points = []
    for row in range(rows):
        for col in range(cols):
            points.append(((2 * col + row % 2) * spacing_mm, row * spacing_mm, 0.0))
    return np.asarray(points, dtype=np.float64)


def panel_mm(width_px, height_px, diagonal_in):
    """Viewable panel size, assuming square pixels and the advertised diagonal."""
    diag_px = math.hypot(width_px, height_px)
    mm_per_px = diagonal_in * MM_PER_INCH / diag_px
    return width_px * mm_per_px, height_px * mm_per_px, mm_per_px


def fit_spacing_mm(width_mm, height_mm, cols, rows):
    """Largest spacing whose circles, including radius, fit inside the margins."""
    width_units = 2 * (cols - 1) + 1
    height_units = rows - 1
    usable_w = width_mm * (1.0 - 2.0 * MARGIN)
    usable_h = height_mm * (1.0 - 2.0 * MARGIN)
    return min(
        usable_w / (width_units + 2.0 * RADIUS_RATIO),
        usable_h / (height_units + 2.0 * RADIUS_RATIO),
    )


def geometry(width_px, height_px, diagonal_in, cols=COLS, rows=ROWS):
    width_mm, height_mm, mm_per_px = panel_mm(width_px, height_px, diagonal_in)
    spacing_mm = fit_spacing_mm(width_mm, height_mm, cols, rows)
    return {
        "width_px": int(width_px),
        "height_px": int(height_px),
        "diagonal_in": float(diagonal_in),
        "width_mm": width_mm,
        "height_mm": height_mm,
        "mm_per_px": mm_per_px,
        "cols": int(cols),
        "rows": int(rows),
        "spacing_mm": spacing_mm,
        "radius_mm": spacing_mm * RADIUS_RATIO,
    }


def render(spec):
    """White circles on black, centered on a panel-sized image."""
    points = object_points(spec["cols"], spec["rows"], spec["spacing_mm"])
    radius_mm = spec["radius_mm"]
    mm_per_px = spec["mm_per_px"]
    span_x = points[:, 0].max() - points[:, 0].min()
    span_y = points[:, 1].max() - points[:, 1].min()
    origin_x = (spec["width_mm"] - span_x) / 2.0 - points[:, 0].min()
    origin_y = (spec["height_mm"] - span_y) / 2.0 - points[:, 1].min()
    image = np.zeros((spec["height_px"], spec["width_px"]), dtype=np.float64)
    radius_px = radius_mm / mm_per_px
    centers_px = []
    for x_mm, y_mm, _ in points:
        center_x = (origin_x + x_mm) / mm_per_px
        center_y = (origin_y + y_mm) / mm_per_px
        centers_px.append((center_x, center_y))
        paint_disk(image, center_x, center_y, radius_px)
    return np.clip(image * CIRCLE_COLOR, 0, 255).astype(np.uint8), np.asarray(centers_px)


def paint_disk(image, center_x, center_y, radius):
    """Fill a disk from the distance to the center, with a one-pixel soft edge."""
    x0 = max(0, int(np.floor(center_x - radius - 1.0)))
    x1 = min(image.shape[1], int(np.ceil(center_x + radius + 1.0)))
    y0 = max(0, int(np.floor(center_y - radius - 1.0)))
    y1 = min(image.shape[0], int(np.ceil(center_y + radius + 1.0)))
    yy, xx = np.ogrid[y0:y1, x0:x1]
    distance = np.sqrt((xx + 0.5 - center_x) ** 2 + (yy + 0.5 - center_y) ** 2)
    coverage = np.clip(radius + 0.5 - distance, 0.0, 1.0)
    image[y0:y1, x0:x1] = np.maximum(image[y0:y1, x0:x1], coverage)


def blob_detector():
    params = cv2.SimpleBlobDetector_Params()
    params.filterByColor = True
    params.blobColor = BLOB_COLOR
    params.filterByArea = True
    params.minArea = BLOB_MIN_AREA
    params.maxArea = BLOB_MAX_AREA
    params.filterByCircularity = True
    params.minCircularity = BLOB_MIN_CIRCULARITY
    params.filterByInertia = True
    params.minInertiaRatio = BLOB_MIN_INERTIA
    params.filterByConvexity = True
    params.minConvexity = BLOB_MIN_CONVEXITY
    return cv2.SimpleBlobDetector_create(params)


def find_grid(image, cols, rows):
    """Return circle centers in object-point order, or None."""
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    flags = cv2.CALIB_CB_ASYMMETRIC_GRID | cv2.CALIB_CB_CLUSTERING
    ok, centers = cv2.findCirclesGrid(
        gray,
        (cols, rows),
        flags=flags,
        blobDetector=blob_detector(),
    )
    if not ok:
        return None
    return centers.reshape(-1, 2)
