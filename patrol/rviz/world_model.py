#!/usr/bin/env python3
"""Publish the metre-scale YAML World model and optional simulated replay to RViz."""
import argparse
import bisect
import json
import math
from pathlib import Path

import numpy as np
import rclpy
from geometry_msgs.msg import Point, PoseStamped
from nav_msgs.msg import Path as RosPath
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray
from patrol.navigation import World, vec

# USER_SETTINGS
WORLD_PATH = 'patrol/maps/demo.yaml'  # 既定の合成Worldモデル
FRAME = 'patrol_world'  # メートル・Z上向き。任意尺度SLAMのmapとは分ける
PUBLISH_HZ = 10.0  # Worldと巡回ログの更新周期
PLAYBACK_SPEED = 1.0  # シミュレーション時刻の再生倍率
EDGE_WIDTH_M = 0.025  # ボックス枠の線幅
LABEL_HEIGHT_M = 0.18  # 名前と状態の文字高さ
GOAL_DIAMETER_M = 0.18  # 目的座標の球の直径
DRONE_DIAMETER_M = 0.20  # 機体位置の表示球の直径
OBSTACLE_COLOR = (0.65, 0.68, 0.73, 0.90)  # 障害物の色RGBA
FREE_COLOR = (0.35, 0.70, 0.45, 0.55)  # 確認済み通行空間の枠の色RGBA
MARGIN_COLOR = (0.95, 0.65, 0.25, 0.50)  # clearanceを含む障害物枠の色RGBA
GOAL_COLOR = (0.35, 0.75, 0.95, 1.00)  # 目的座標の色RGBA
LABEL_COLOR = (0.95, 0.95, 0.95, 1.00)  # 文字の色RGBA
DRONE_COLOR = (0.95, 0.85, 0.25, 1.00)  # 移動中の機体マーカー色RGBA
STOP_COLOR = (1.00, 0.30, 0.20, 1.00)  # 停止中の機体マーカー色RGBA


def point(x):
    return Point(x=float(x[0]), y=float(x[1]), z=float(x[2]))


def color(c):
    return ColorRGBA(r=c[0], g=c[1], b=c[2], a=c[3])


def marker(ns, idx, kind, stamp, rgba):
    m = Marker()
    m.header.frame_id = FRAME
    m.header.stamp = stamp
    m.ns, m.id, m.type, m.action = ns, idx, kind, Marker.ADD
    m.pose.orientation.w = 1.0
    m.color = color(rgba)
    return m


def box_edges(lo, hi):
    lo, hi = vec(lo), vec(hi)
    corners = np.array([[hi[j] if (i >> j) & 1 else lo[j] for j in range(3)] for i in range(8)])
    return [point(corners[k]) for i in range(8) for j in range(3) if i < (i ^ (1 << j)) for k in (i, i ^ (1 << j))]


def wire(ns, idx, lo, hi, stamp, rgba):
    m = marker(ns, idx, Marker.LINE_LIST, stamp, rgba)
    m.scale.x = EDGE_WIDTH_M
    m.points = box_edges(lo, hi)
    return m


def world_markers(world, stamp, position, state):
    a = MarkerArray()
    reset = marker('reset', 0, Marker.CUBE, stamp, LABEL_COLOR)
    reset.action = Marker.DELETEALL
    a.markers.append(reset)
    a.markers.append(wire('room_bounds', 0, world.lo, world.hi, stamp, LABEL_COLOR))
    for i, volume in enumerate(world.free):
        a.markers.append(wire('verified_free', i, volume['min'], volume['max'], stamp, FREE_COLOR))
    for i, obj in enumerate(world.boxes):
        lo, hi = vec(obj['min']), vec(obj['max'])
        m = marker('objects', i, Marker.CUBE, stamp, OBSTACLE_COLOR)
        m.pose.position = point((lo+hi)/2)
        m.scale.x, m.scale.y, m.scale.z = map(float, hi-lo)
        a.markers.append(m)
        if obj.get('obstacle', True):
            a.markers.append(wire('clearance', i, lo-world.margin, hi+world.margin, stamp, MARGIN_COLOR))
        label = marker('object_names', i, Marker.TEXT_VIEW_FACING, stamp, LABEL_COLOR)
        label.pose.position = point([(lo[0]+hi[0])/2, (lo[1]+hi[1])/2, hi[2]+LABEL_HEIGHT_M])
        label.scale.z = LABEL_HEIGHT_M
        label.text = str(obj.get('id', f'object_{i}'))+' / '+str(obj.get('kind', 'box'))
        a.markers.append(label)
    for i, goal in enumerate(world.spec.get('patrol_goals', [])):
        m = marker('goals', i, Marker.SPHERE, stamp, GOAL_COLOR)
        m.pose.position = point(vec(goal))
        m.scale.x = m.scale.y = m.scale.z = GOAL_DIAMETER_M
        a.markers.append(m)
        label = marker('goal_names', i, Marker.TEXT_VIEW_FACING, stamp, GOAL_COLOR)
        label.pose.position = point(vec(goal)+[0, 0, LABEL_HEIGHT_M])
        label.scale.z = LABEL_HEIGHT_M
        label.text = f'goal {i+1}: '+str(goal)+' m'
        a.markers.append(label)
    drone = marker('drone', 0, Marker.SPHERE, stamp, DRONE_COLOR if state in ('MOVING', 'STATIC_WORLD') else STOP_COLOR)
    drone.pose.position = point(position)
    drone.scale.x = drone.scale.y = drone.scale.z = DRONE_DIAMETER_M
    a.markers.append(drone)
    label = marker('status', 0, Marker.TEXT_VIEW_FACING, stamp, LABEL_COLOR)
    label.pose.position = point([world.lo[0], world.lo[1], world.hi[2]+.5])
    label.scale.z = LABEL_HEIGHT_M
    label.text = str(world.spec.get('source', 'YAML World'))+' [m], Z up / '+state
    a.markers.append(label)
    return a


def path_message(xyz, stamp):
    msg = RosPath()
    msg.header.frame_id = FRAME
    msg.header.stamp = stamp
    for p in xyz:
        pose = PoseStamped()
        pose.header = msg.header
        pose.pose.position = point(p)
        pose.pose.orientation.w = 1.0
        msg.poses.append(pose)
    return msg


def load_replay(path):
    records = json.loads(Path(path).read_text())
    if not records:
        raise ValueError('Replay is empty')
    times = []
    for row in records:
        t = float(row['t'])
        if not math.isfinite(t) or (times and t <= times[-1]):
            raise ValueError('Replay timestamps must be finite and strictly increasing')
        times.append(t)
        vec(row['position'])
        for p in row.get('path') or []:
            vec(p)
    return records, times


class WorldPublisher(Node):
    def __init__(self, world, replay, speed):
        super().__init__('patrol_world_model')
        self.world = world
        self.records, self.times = load_replay(replay) if replay else ([], [])
        self.speed = speed
        self.start_ns = self.get_clock().now().nanoseconds
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
        self.world_pub = self.create_publisher(MarkerArray, '/patrol/world', qos)
        self.plan_pub = self.create_publisher(RosPath, '/patrol/plan', qos)
        self.trail_pub = self.create_publisher(RosPath, '/patrol/trajectory', qos)
        self.initial_plan = []
        goals = world.spec.get('patrol_goals', [])
        if not self.records and goals:
            self.initial_plan = world.plan(world.spec['start'], goals[0]).tolist()
        self.create_timer(1/PUBLISH_HZ, self.tick)
        self.get_logger().info(f'World model: {FRAME}, metres, Z up; objects={len(world.boxes)}; replay={bool(self.records)}')

    def tick(self):
        now = self.get_clock().now()
        stamp = now.to_msg()
        if self.records:
            t = (now.nanoseconds-self.start_ns)/1e9*self.speed+self.times[0]
            i = max(0, bisect.bisect_right(self.times, t)-1)
            row = self.records[i]
            spec = dict(self.world.spec)
            spec['objects'] = row.get('objects', self.world.spec['objects'])
            current = World(spec)
            position, state, plan = row['position'], row['state'], row.get('path') or []
            trail = [r['position'] for r in self.records[:i+1]]
        else:
            current = self.world
            position, state, plan, trail = current.spec['start'], 'STATIC_WORLD', self.initial_plan, []
        self.world_pub.publish(world_markers(current, stamp, position, state))
        self.plan_pub.publish(path_message(plan, stamp))
        self.trail_pub.publish(path_message(trail, stamp))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--world', type=Path, default=Path(__file__).resolve().parents[2]/WORLD_PATH)
    parser.add_argument('--log', type=Path, help='Simulation log with optional per-frame objects snapshots')
    parser.add_argument('--speed', type=float, default=PLAYBACK_SPEED)
    args = parser.parse_args()
    if not math.isfinite(args.speed) or args.speed <= 0:
        parser.error('--speed must be positive and finite')
    world = World.load(args.world)
    rclpy.init()
    node = WorldPublisher(world, args.log, args.speed)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
