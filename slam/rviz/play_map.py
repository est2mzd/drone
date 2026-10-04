#!/usr/bin/env python3
"""Play the saved map in rviz2, with the first valid camera pose at the origin."""

import argparse
from pathlib import Path

import numpy as np
import rclpy
from geometry_msgs.msg import Point, PoseStamped, TransformStamped
from nav_msgs.msg import Path as Trajectory
from rclpy.node import Node
from std_msgs.msg import ColorRGBA
from tf2_ros import TransformBroadcaster
from visualization_msgs.msg import Marker

# USER_SETTINGS
POINTS = "slam/out/20261002_001816_points.txt"  # 地図点。1行は t x y z
POSES = "slam/out/20261002_001816_points_poses.txt"  # カメラ姿勢。1行は t tx ty tz qx qy qz qw valid
VOXEL_DIV = 80.0  # 箱の一辺。点群の対角長さをこの数で割る。view.sh の VOXEL_DIV と同じ
PLAY_FPS = 30.0  # 自己位置を進める速さ。動画と同じ 30 なら実時間
FRAME = "map"  # rviz2 の Fixed Frame。開始カメラがこの原点


def quat_to_matrix(x, y, z, w):
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def matrix_to_quat(rotation):
    trace = float(np.trace(rotation))
    if trace > 0.0:
        scale = np.sqrt(trace + 1.0) * 2.0
        w = 0.25 * scale
        x = (rotation[2, 1] - rotation[1, 2]) / scale
        y = (rotation[0, 2] - rotation[2, 0]) / scale
        z = (rotation[1, 0] - rotation[0, 1]) / scale
    elif rotation[0, 0] > rotation[1, 1] and rotation[0, 0] > rotation[2, 2]:
        scale = np.sqrt(1.0 + rotation[0, 0] - rotation[1, 1] - rotation[2, 2]) * 2.0
        w = (rotation[2, 1] - rotation[1, 2]) / scale
        x = 0.25 * scale
        y = (rotation[0, 1] + rotation[1, 0]) / scale
        z = (rotation[0, 2] + rotation[2, 0]) / scale
    elif rotation[1, 1] > rotation[2, 2]:
        scale = np.sqrt(1.0 + rotation[1, 1] - rotation[0, 0] - rotation[2, 2]) * 2.0
        w = (rotation[0, 2] - rotation[2, 0]) / scale
        x = (rotation[0, 1] + rotation[1, 0]) / scale
        y = 0.25 * scale
        z = (rotation[1, 2] + rotation[2, 1]) / scale
    else:
        scale = np.sqrt(1.0 + rotation[2, 2] - rotation[0, 0] - rotation[1, 1]) * 2.0
        w = (rotation[1, 0] - rotation[0, 1]) / scale
        x = (rotation[0, 2] + rotation[2, 0]) / scale
        y = (rotation[1, 2] + rotation[2, 1]) / scale
        z = 0.25 * scale
    return np.array([x, y, z, w], dtype=np.float64)


def camera_pose(row):
    rotation = quat_to_matrix(row[4], row[5], row[6], row[7])
    translation = row[1:4]
    center = -rotation.T @ translation
    return rotation, translation, center


def build_voxels(points, divisor):
    xyz = points[:, 1:4]
    span = xyz.max(axis=0) - xyz.min(axis=0)
    diagonal = float(np.linalg.norm(span))
    size = diagonal / float(divisor) if diagonal > 1e-9 else 1.0
    grouped = {}
    for timestamp, x, y, z in points:
        key = (int(np.floor(x / size)), int(np.floor(y / size)), int(np.floor(z / size)))
        current = grouped.get(key)
        if current is None or timestamp < current[0]:
            grouped[key] = (float(timestamp), np.array([x, y, z], dtype=np.float64))
    order = sorted(grouped.values(), key=lambda item: item[0])
    times = np.array([item[0] for item in order], dtype=np.float64)
    centers = np.stack([(item[1]) for item in order])
    return centers, times, size


def to_start_frame(points, poses, divisor):
    valid = poses[poses[:, 8] >= 0.5]
    if len(valid) == 0:
        raise SystemExit("no valid camera pose")
    rotation0, translation0, center0 = camera_pose(valid[0])
    voxel_centers, voxel_times, size = build_voxels(points, divisor)
    voxels = (voxel_centers - center0) @ rotation0.T
    path = []
    for row in valid:
        rotation, _translation, center = camera_pose(row)
        position = rotation0 @ (center - center0)
        orientation = matrix_to_quat(rotation0 @ rotation.T)
        path.append((float(row[0]), position, orientation))
    return voxels, voxel_times, size, path


def color_from_height(z, low, high):
    unit = 0.0 if high - low < 1e-9 else float(np.clip((z - low) / (high - low), 0.0, 1.0))
    color = ColorRGBA()
    color.r = unit
    color.g = 0.4
    color.b = 1.0 - unit
    color.a = 1.0
    return color


class MapPlayer(Node):
    def __init__(self, voxels, voxel_times, size, path, play_fps):
        super().__init__("mini3_map")
        self.voxels = voxels
        self.voxel_times = voxel_times
        self.size = size
        self.path = path
        self.index = 0
        self.voxels_pub = self.create_publisher(Marker, "voxels", 1)
        self.origin_pub = self.create_publisher(Marker, "origin", 1)
        self.path_pub = self.create_publisher(Trajectory, "trajectory", 1)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.low = float(voxels[:, 2].min()) if len(voxels) else 0.0
        self.high = float(voxels[:, 2].max()) if len(voxels) else 1.0
        self.timer = self.create_timer(1.0 / play_fps, self.tick)
        self.get_logger().info(
            f"voxels {len(voxels)} poses {len(path)} edge {size:.4f} origin is the first valid camera"
        )

    def tick(self):
        stamp = self.get_clock().now().to_msg()
        timestamp, position, orientation = self.path[self.index]
        self.publish_origin(stamp)
        self.publish_voxels(stamp, timestamp)
        self.publish_path(stamp)
        self.publish_tf(stamp, position, orientation)
        if self.index + 1 < len(self.path):
            self.index += 1

    def publish_origin(self, stamp):
        marker = Marker()
        marker.header.frame_id = FRAME
        marker.header.stamp = stamp
        marker.ns = "origin"
        marker.id = 0
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD
        marker.scale.x = marker.scale.y = marker.scale.z = max(self.size, 0.05)
        marker.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
        marker.pose.orientation.w = 1.0
        self.origin_pub.publish(marker)

    def publish_voxels(self, stamp, timestamp):
        keep = np.flatnonzero(self.voxel_times <= timestamp)
        marker = Marker()
        marker.header.frame_id = FRAME
        marker.header.stamp = stamp
        marker.ns = "voxels"
        marker.id = 1
        marker.type = Marker.CUBE_LIST
        marker.action = Marker.ADD
        marker.scale.x = marker.scale.y = marker.scale.z = self.size
        marker.pose.orientation.w = 1.0
        for center in self.voxels[keep]:
            marker.points.append(Point(x=float(center[0]), y=float(center[1]), z=float(center[2])))
            marker.colors.append(color_from_height(center[2], self.low, self.high))
        self.voxels_pub.publish(marker)

    def publish_path(self, stamp):
        message = Trajectory()
        message.header.frame_id = FRAME
        message.header.stamp = stamp
        for timestamp, position, orientation in self.path[: self.index + 1]:
            pose = PoseStamped()
            pose.header.frame_id = FRAME
            pose.header.stamp = stamp
            pose.pose.position.x = float(position[0])
            pose.pose.position.y = float(position[1])
            pose.pose.position.z = float(position[2])
            pose.pose.orientation.x = float(orientation[0])
            pose.pose.orientation.y = float(orientation[1])
            pose.pose.orientation.z = float(orientation[2])
            pose.pose.orientation.w = float(orientation[3])
            message.poses.append(pose)
        self.path_pub.publish(message)

    def publish_tf(self, stamp, position, orientation):
        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = FRAME
        transform.child_frame_id = "camera"
        transform.transform.translation.x = float(position[0])
        transform.transform.translation.y = float(position[1])
        transform.transform.translation.z = float(position[2])
        transform.transform.rotation.x = float(orientation[0])
        transform.transform.rotation.y = float(orientation[1])
        transform.transform.rotation.z = float(orientation[2])
        transform.transform.rotation.w = float(orientation[3])
        self.tf_broadcaster.sendTransform(transform)


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", type=Path, default=root / POINTS)
    parser.add_argument("--poses", type=Path, default=root / POSES)
    parser.add_argument("--voxel-div", type=float, default=VOXEL_DIV)
    args = parser.parse_args()
    points = np.loadtxt(args.points)
    poses = np.loadtxt(args.poses)
    voxels, voxel_times, size, path = to_start_frame(points, poses, args.voxel_div)
    start = path[0][1]
    if np.linalg.norm(start) > 1e-6:
        raise SystemExit(f"start is not the origin: {start}")
    rclpy.init()
    node = MapPlayer(voxels, voxel_times, size, path, PLAY_FPS)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
