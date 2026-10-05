"""Conservative 3D voxel planning and guarded velocity control; no aircraft I/O."""
import heapq
import math
import numpy as np
import yaml

# USER_SETTINGS
RESOLUTION_M = 0.20  # voxel edge in metres
CLEARANCE_M = 0.35  # aircraft enclosing radius plus margin
MAX_SPEED_MPS = 0.25  # simulated / proposed velocity cap
MAX_POSE_AGE_S = 0.30  # stale localization forces zero velocity
MAX_GEOMETRY_AGE_S = 0.30  # stale online geometry forces zero velocity
MAX_POSITION_SIGMA_M = 0.10  # uncertainty cap for motion
GOAL_TOLERANCE_M = 0.12  # arrival tolerance
BRAKING_ACCEL_MPS2 = 0.30  # conservative stopping acceleration assumption
CONTROL_DT_S = 0.10  # controller tick period


def vec(value):
    a = np.asarray(value, float)
    if a.shape != (3,) or not np.isfinite(a).all():
        raise ValueError('Expected finite xyz')
    return a


class World:
    def __init__(self, spec):
        if spec.get('units') != 'm' or spec.get('frame') != 'local_xyz_z_up':
            raise ValueError('World must use metres and local_xyz_z_up')
        self.spec = spec
        self.res = float(spec.get('resolution_m', RESOLUTION_M))
        self.margin = float(spec.get('clearance_m', CLEARANCE_M))
        self.lo, self.hi = vec(spec['bounds']['min']), vec(spec['bounds']['max'])
        if not np.isfinite([self.res,self.margin]).all() or self.res <= 0 or self.margin <= 0 or np.any(self.hi <= self.lo):
            raise ValueError('Invalid bounds/resolution/clearance')
        self.shape = np.ceil((self.hi-self.lo)/self.res).astype(int)
        self.free = spec.get('verified_free', [])
        self.boxes = list(spec.get('objects', []))
        for b in self.free+self.boxes:
            if np.any(vec(b['max']) <= vec(b['min'])):
                raise ValueError('Invalid box extents')
        self.version = 0

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls(yaml.safe_load(f))

    def cell(self, xyz):
        return tuple(np.floor((vec(xyz)-self.lo)/self.res).astype(int))

    def point(self, cell):
        return self.lo+(np.asarray(cell)+.5)*self.res

    def safe(self, xyz):
        p = vec(xyz)
        if np.any(p-self.margin < self.lo) or np.any(p+self.margin > self.hi):
            return False
        # Unknown space is blocked. A whole aircraft envelope must fit a verified volume.
        if not any(np.all(p-self.margin >= vec(b['min'])) and np.all(p+self.margin <= vec(b['max'])) for b in self.free):
            return False
        return not any(b.get('obstacle', True) and np.all(p >= vec(b['min'])-self.margin)
                       and np.all(p <= vec(b['max'])+self.margin) for b in self.boxes)

    def segment_safe(self, a, b):
        a, b = vec(a), vec(b)
        # Exact segment intersections with expanded AABBs; no thin-wall sampling gaps.
        if not self.safe(a) or not self.safe(b):
            return False
        if not any(np.all(np.minimum(a,b)-self.margin >= vec(v['min'])) and
                   np.all(np.maximum(a,b)+self.margin <= vec(v['max'])) for v in self.free):
            return False
        delta = b-a
        for box in self.boxes:
            if not box.get('obstacle', True):
                continue
            lower, upper = vec(box['min'])-self.margin, vec(box['max'])+self.margin
            enter, leave = 0., 1.
            for axis in range(3):
                if abs(delta[axis]) < 1e-12:
                    if a[axis] < lower[axis] or a[axis] > upper[axis]:
                        enter, leave = 1., 0.
                        break
                else:
                    ts = sorted(((lower[axis]-a[axis])/delta[axis], (upper[axis]-a[axis])/delta[axis]))
                    enter, leave = max(enter, ts[0]), min(leave, ts[1])
            if enter <= leave:
                return False
        return True

    def add_obstacle(self, minimum, maximum, name='dynamic'):
        lo, hi = vec(minimum), vec(maximum)
        if np.any(hi <= lo):
            raise ValueError('Invalid obstacle')
        self.boxes.append({'id': name, 'min': lo.tolist(), 'max': hi.tolist(), 'obstacle': True})
        self.version += 1

    def plan(self, start, goal):
        start, goal = vec(start), vec(goal)
        source, target = self.cell(start), self.cell(goal)
        if not self.safe(start) or not self.safe(goal):
            raise ValueError('Start/goal is blocked, outside bounds, or unknown')
        if not self.segment_safe(start, self.point(source)) or not self.segment_safe(self.point(target), goal):
            raise ValueError('No safe connection to grid')
        frontier, cost, parent = [(0., source)], {source: 0.}, {}
        while frontier:
            _, current = heapq.heappop(frontier)
            if current == target:
                cells = [current]
                while cells[-1] != source:
                    cells.append(parent[cells[-1]])
                route = [start]+[self.point(c) for c in reversed(cells)]+[goal]
                smooth, index = [route[0]], 0
                while index < len(route)-1:
                    nxt = next(j for j in range(len(route)-1, index, -1)
                               if self.segment_safe(route[index], route[j]))
                    smooth.append(route[nxt]); index = nxt
                return np.asarray(smooth)
            for axis in range(3):
                for sign in (-1, 1):
                    nxt = list(current); nxt[axis] += sign; nxt = tuple(nxt)
                    if any(n < 0 or n >= s for n, s in zip(nxt, self.shape)):
                        continue
                    if not self.segment_safe(self.point(current), self.point(nxt)):
                        continue
                    g = cost[current]+self.res
                    if g < cost.get(nxt, math.inf):
                        cost[nxt], parent[nxt] = g, current
                        h = np.linalg.norm(self.point(nxt)-self.point(target))
                        heapq.heappush(frontier, (g+h, nxt))
        raise ValueError('No collision-free route')


class Controller:
    def __init__(self, world, goals):
        self.world, self.goals = world, [vec(g) for g in goals]
        self.goal_index, self.path, self.path_index = 0, None, 1
        self.map_version = -1

    def tick(self, position, now, pose_stamp, valid, sigma_m, geometry_stamp,
             metric_aligned, camera_body_calibrated, emergency=False):
        zero = np.zeros(3)
        if emergency:
            return zero, 'EMERGENCY_STOP'
        if not metric_aligned or not camera_body_calibrated:
            return zero, 'WAIT_CALIBRATION'
        if not valid or not np.isfinite(sigma_m) or sigma_m > MAX_POSITION_SIGMA_M or sigma_m < 0:
            return zero, 'WAIT_LOCALIZATION'
        if not np.isfinite([now, pose_stamp, geometry_stamp]).all() or not 0 <= now-pose_stamp <= MAX_POSE_AGE_S:
            return zero, 'STALE_POSE'
        if not 0 <= now-geometry_stamp <= MAX_GEOMETRY_AGE_S:
            return zero, 'STALE_GEOMETRY'
        p = vec(position)
        if self.goal_index >= len(self.goals):
            return zero, 'COMPLETE'
        goal = self.goals[self.goal_index]
        if np.linalg.norm(p-goal) <= GOAL_TOLERANCE_M:
            self.goal_index += 1; self.path = None
            return zero, 'ARRIVED'
        try:
            if self.path is None or self.map_version != self.world.version or not self.world.segment_safe(p, self.path[self.path_index]):
                self.path = self.world.plan(p, goal); self.path_index = 1; self.map_version = self.world.version
            while self.path_index < len(self.path)-1 and np.linalg.norm(p-self.path[self.path_index]) <= GOAL_TOLERANCE_M:
                self.path_index += 1
        except ValueError:
            self.path = None
            return zero, 'BLOCKED'
        delta = self.path[self.path_index]-p
        speed = min(MAX_SPEED_MPS, np.linalg.norm(delta)/CONTROL_DT_S)
        direction = delta/max(np.linalg.norm(delta), 1e-12)
        stopping = speed*MAX_POSE_AGE_S + speed*speed/(2*BRAKING_ACCEL_MPS2)
        if not self.world.segment_safe(p, p+direction*max(stopping, speed*CONTROL_DT_S)):
            return zero, 'STOPPING_ENVELOPE_BLOCKED'
        return direction*speed, 'MOVING'
