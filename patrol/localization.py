"""ORB descriptors / calibrated multi-view triangulation / map-relative PnP.
Input poses are the repository's Tcw export, NOT camera positions.
"""
from pathlib import Path
import cv2
import numpy as np

# USER_SETTINGS
FEATURES = 2500  # ORB features per reference/query image
RATIO = 0.72  # nearest descriptor ratio limit
MIN_INLIERS = 18  # minimum unique 3D landmarks for valid localization
REPROJECTION_PX = 3.0  # triangulation and PnP reprojection limit
MIN_PARALLAX_DEG = 0.8  # reject unstable triangulated depth
REFERENCE_INTERVAL_S = 1.0  # keyframe sampling interval
PAIR_GAP_S = 2.0  # reference pair time baseline
MAX_DESCRIPTOR_DISTANCE = 55  # ORB Hamming distance limit


def camera(path):
    fs = cv2.FileStorage(str(path), cv2.FILE_STORAGE_READ)
    if not fs.isOpened():
        raise ValueError(f'Cannot read calibration: {path}')
    def read(key):
        n = fs.getNode(key)
        if n.empty():
            raise ValueError(f'Missing calibration field: {key}')
        return n.real()
    k = np.array([[read('Camera1.fx'), 0, read('Camera1.cx')],
                  [0, read('Camera1.fy'), read('Camera1.cy')], [0, 0, 1.]])
    d = np.array([read('Camera1.' + n) for n in ('k1', 'k2', 'p1', 'p2', 'k3')])
    fs.release()
    return k, d


def rotation(q):
    q = np.asarray(q, float)
    if not np.isfinite(q).all() or np.linalg.norm(q) < 1e-8:
        raise ValueError('Invalid quaternion')
    x, y, z, w = q / np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def tcw(row):
    return np.column_stack([rotation(row[4:8]), row[1:4]])


def center(p):
    return -p[:, :3].T @ p[:, 3]


def matches(a, b):
    if a is None or b is None or len(b) < 2:
        return []
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(a, b, k=2)
    candidates = [m for pair in pairs if len(pair) == 2 for m, n in [pair]
                  if m.distance < RATIO*n.distance and m.distance <= MAX_DESCRIPTOR_DISTANCE]
    # One feature/landmark must not support multiple correspondences.
    result, used = [], set()
    for m in sorted(candidates, key=lambda m: m.distance):
        if m.trainIdx not in used:
            result.append(m)
            used.add(m.trainIdx)
    return result


def triangulate(p1, p2, uv1, uv2, k, d):
    a = cv2.undistortPoints(np.asarray(uv1, float).reshape(-1, 1, 2), k, d).reshape(-1, 2)
    b = cv2.undistortPoints(np.asarray(uv2, float).reshape(-1, 1, 2), k, d).reshape(-1, 2)
    h = cv2.triangulatePoints(p1, p2, a.T, b.T)
    with np.errstate(divide='ignore', invalid='ignore'):
        xyz = (h[:3] / h[3]).T
    valid = np.isfinite(xyz).all(1)
    for p, uv in ((p1, uv1), (p2, uv2)):
        depth = (xyz @ p[:, :3].T + p[:, 3])[:, 2]
        projected, _ = cv2.projectPoints(xyz, cv2.Rodrigues(p[:, :3])[0], p[:, 3], k, d)
        valid &= (depth > 0) & (np.linalg.norm(projected.reshape(-1, 2)-uv, axis=1) < REPROJECTION_PX)
    rays1, rays2 = xyz-center(p1), xyz-center(p2)
    with np.errstate(divide='ignore', invalid='ignore'):
        cosine = np.sum(rays1*rays2, axis=1)/(np.linalg.norm(rays1, axis=1)*np.linalg.norm(rays2, axis=1))
    valid &= np.degrees(np.arccos(np.clip(cosine, -1, 1))) >= MIN_PARALLAX_DEG
    return xyz, valid


def build_map(video, poses, calibration, output, reference_end=None):
    k, d = camera(calibration)
    rows = np.atleast_2d(np.loadtxt(poses))
    if rows.shape[1] != 9 or not np.isfinite(rows).all() or np.any(np.diff(rows[:, 0]) <= 0):
        raise ValueError('Expected monotonically timed finite t tx ty tz qx qy qz qw valid')
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        raise ValueError('Cannot open video')
    orb = cv2.ORB_create(nfeatures=FEATURES)
    references, next_t = [], 0.
    for row in rows:
        if row[-1] != 1 or row[0] < next_t or (reference_end is not None and row[0] >= reference_end):
            continue
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(row[0]*fps)))
        ok, frame = cap.read()
        if not ok:
            continue
        kp, desc = orb.detectAndCompute(frame, None)
        if desc is not None:
            references.append((row, np.array([x.pt for x in kp]), desc))
            next_t = row[0]+REFERENCE_INTERVAL_S
    cap.release()
    points, descriptors, provenance = [], [], []
    for i, (row, uv, desc) in enumerate(references):
        partner = next((r for r in references[i+1:] if r[0][0]-row[0] >= PAIR_GAP_S), None)
        if partner is None:
            continue
        row2, uv2, desc2 = partner
        ms = matches(desc, desc2)
        if len(ms) < MIN_INLIERS:
            continue
        idx = np.array([m.queryIdx for m in ms]); jdx = np.array([m.trainIdx for m in ms])
        xyz, good = triangulate(tcw(row), tcw(row2), uv[idx], uv2[jdx], k, d)
        points.extend(xyz[good]); descriptors.extend(desc[idx[good]])
        provenance.extend([[row[0], row2[0]]]*int(good.sum()))
    if len(points) < MIN_INLIERS:
        raise ValueError('Insufficient triangulated landmarks; capture more translation/textured views')
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, xyz=np.asarray(points), descriptors=np.asarray(descriptors),
                        k=k, d=d, reference_times=np.asarray(provenance),
                        units='slam_units', pose_convention='Tcw', version=1)
    return {'landmarks': len(points), 'reference_frames': len(references), 'units': 'slam_units'}


class Localizer:
    def __init__(self, path):
        with np.load(path, allow_pickle=False) as m:
            self.xyz, self.desc = m['xyz'].copy(), m['descriptors'].copy()
            self.k, self.d = m['k'].copy(), m['d'].copy()
        self.orb = cv2.ORB_create(nfeatures=FEATURES)

    def estimate(self, frame):
        kp, desc = self.orb.detectAndCompute(frame, None)
        ms = matches(desc, self.desc)
        failure = {'valid': False, 'matches': len(ms), 'inliers': 0, 'reason': 'insufficient_matches'}
        if len(ms) < MIN_INLIERS:
            return failure
        xyz = self.xyz[[m.trainIdx for m in ms]]
        uv = np.array([kp[m.queryIdx].pt for m in ms], dtype=float)
        ok, rv, tv, inliers = cv2.solvePnPRansac(xyz, uv, self.k, self.d, iterationsCount=200,
                          reprojectionError=REPROJECTION_PX, confidence=.999, flags=cv2.SOLVEPNP_EPNP)
        if not ok or inliers is None or len(inliers) < MIN_INLIERS:
            failure['reason'] = 'pnp_rejected'
            return failure
        ids = inliers.ravel()
        rv, tv = cv2.solvePnPRefineLM(xyz[ids], uv[ids], self.k, self.d, rv, tv)
        r = cv2.Rodrigues(rv)[0]
        proj = cv2.projectPoints(xyz[ids], rv, tv, self.k, self.d)[0].reshape(-1, 2)
        residual = float(np.sqrt(np.mean(np.sum((proj-uv[ids])**2, axis=1))))
        if residual > REPROJECTION_PX or np.any((xyz[ids] @ r.T + tv.ravel())[:, 2] <= 0):
            failure['reason'] = 'geometry_rejected'
            return failure
        return {'valid': True, 'matches': len(ms), 'inliers': len(ids), 'position': (-r.T@tv).ravel().tolist(),
                'rotation_cw': r.tolist(), 'rms_px': residual, 'reason': 'localized'}
