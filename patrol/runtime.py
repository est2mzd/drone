"""Connect a calibrated visual pose to planning and a dry-run command transport.
No motion without measured Sim(3), fixed camera/body extrinsics, and fresh geometry.
"""
import json
import math
import re
import secrets
import socket
import time
import numpy as np
from .navigation import Controller, vec

# USER_SETTINGS
COMMAND_TTL_MS = 250  # receiver discards expired commands (PC/phone clocks must be synchronized)
COMMAND_PORT = 5001  # independent of H264 video port
SOCKET_TIMEOUT_S = 0.25  # no unbounded I/O in control loop


def proper_rotation(value):
    r = np.asarray(value, float)
    if r.shape != (3, 3) or not np.isfinite(r).all() or not np.allclose(r.T@r, np.eye(3), atol=1e-5) or not np.isclose(np.linalg.det(r), 1, atol=1e-5):
        raise ValueError('Expected right-handed orthonormal 3x3 rotation')
    return r


class Alignment:
    def __init__(self, spec):
        if not spec.get('metric_verified') or not spec.get('extrinsics_verified') or not spec.get('gimbal_fixed'):
            raise ValueError('Measured metric alignment, camera/body extrinsics and fixed gimbal required')
        self.scale = float(spec['metres_per_slam_unit'])
        if not math.isfinite(self.scale) or self.scale <= 0:
            raise ValueError('Invalid metric scale')
        self.r_ws = proper_rotation(spec['rotation_world_from_slam'])
        self.t_ws = vec(spec['translation_world_from_slam_m'])
        self.r_bc = proper_rotation(spec['rotation_body_from_camera'])
        self.t_bc = vec(spec['camera_origin_in_body_m'])

    def pose(self, result):
        r_sc = proper_rotation(result['rotation_cw']).T
        r_wc = self.r_ws@r_sc
        r_wb = r_wc@self.r_bc.T
        camera_w = self.scale*(self.r_ws@vec(result['position']))+self.t_ws
        body_w = camera_w-r_wb@self.t_bc
        return body_w, r_wb


class CommandClient:
    """NDJSON socket; SDK-axis values are explicit, never guessed from camera axes."""
    def __init__(self, host, token, port=COMMAND_PORT):
        if re.fullmatch(r'[a-fA-F0-9]{64}', token) is None:
            raise ValueError('Use a per-session 64-character random hexadecimal token')
        self.sock=socket.create_connection((host, port), timeout=SOCKET_TIMEOUT_S)
        self.token, self.session, self.sequence = token, secrets.token_hex(16), 0

    def send(self, roll_mps, pitch_mps, up_mps, reason):
        self.sequence += 1
        packet={'version':1,'token':self.token,'session':self.session,'seq':self.sequence,
                'expires_unix_ms':int(time.time()*1000)+COMMAND_TTL_MS,
                'roll_mps':roll_mps,'pitch_mps':pitch_mps,'up_mps':up_mps,'yaw_dps':0.,'reason':reason}
        self.sock.sendall((json.dumps(packet,allow_nan=False)+'\n').encode())
        return packet

    def close(self):
        try:self.send(0.,0.,0.,'CLIENT_STOP')
        finally:self.sock.close()


class PatrolRuntime:
    def __init__(self, world, goals, alignment, sdk_axes_verified=False):
        self.controller=Controller(world,goals)
        self.alignment=alignment
        self.sdk_axes_verified=sdk_axes_verified

    def tick(self, estimate, capture_monotonic_s, geometry_monotonic_s, sigma_m, emergency=False):
        now=time.monotonic()
        valid=bool(estimate.get('valid'))
        p,r=(self.alignment.pose(estimate) if valid else (np.zeros(3),np.eye(3)))
        v,reason=self.controller.tick(p,now,capture_monotonic_s,valid,sigma_m,geometry_monotonic_s,
                  metric_aligned=True,camera_body_calibrated=True,emergency=emergency)
        # r_wb maps forward/right/down body coordinates into world XYZ z-up.
        # MSDK axis polarity must be checked on the actual model before any flight.
        if not self.sdk_axes_verified:
            return {'roll_mps':0.,'pitch_mps':0.,'up_mps':0.,'reason':'SDK_AXES_UNVERIFIED',
                    'proposed_world_velocity':v.tolist()}
        body_v=r.T@v
        return {'roll_mps':float(body_v[0]),'pitch_mps':float(body_v[1]),
                'up_mps':float(-body_v[2]),'reason':reason,'proposed_world_velocity':v.tolist()}
