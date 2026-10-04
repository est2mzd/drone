#!/usr/bin/env bash
# 開始カメラを原点にして、箱の地図と自己位置を rviz2 に出す。
set -euo pipefail

# USER_SETTINGS
POINTS=slam/out/20261002_001816_points.txt          # 地図点
POSES=slam/out/20261002_001816_points_poses.txt    # カメラ姿勢
VOXEL_DIV=80                                       # 箱の一辺。view.sh の VOXEL_DIV と同じ
RVIZ_CONFIG=slam/rviz/mini3_map.rviz               # 原点、箱、軌跡、座標軸の表示設定
PLAYER=slam/rviz/play_map.py                       # 地図を順に出すノード

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
set +u
source /opt/ros/jazzy/setup.bash
set -u
rviz2 -d "$ROOT/$RVIZ_CONFIG" &
rviz_pid=$!
trap 'kill "$rviz_pid" 2>/dev/null || true' EXIT
python3 "$ROOT/$PLAYER" \
  --points "$ROOT/$POINTS" \
  --poses "$ROOT/$POSES" \
  --voxel-div "$VOXEL_DIV"
