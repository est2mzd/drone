#!/usr/bin/env bash
set -euo pipefail

# USER_SETTINGS
ROS_SETUP=/opt/ros/jazzy/setup.bash  # ROS 2 Jazzy環境
RVIZ_CONFIG=patrol/rviz/world_model.rviz  # Worldモデル表示設定
DOMAIN_DEFAULT=77  # この可視化に使うROSドメイン
RMW_DEFAULT=rmw_cyclonedds_cpp  # この環境で配信を検証したDDS実装
SOFTWARE_RENDERING_DEFAULT=1  # GPU描画に失敗する場合はソフトウェア描画

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
set +u
source "$ROS_SETUP"
set -u
export ROS_LOG_DIR="${ROS_LOG_DIR:-$ROOT/patrol/out/ros-logs}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-$DOMAIN_DEFAULT}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-$RMW_DEFAULT}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-$SOFTWARE_RENDERING_DEFAULT}"
unset ROS_LOCALHOST_ONLY
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
cd "$ROOT"
rviz2 -d "$ROOT/$RVIZ_CONFIG" &
rviz_pid=$!
trap 'kill "$rviz_pid" 2>/dev/null || true' EXIT
python3 -m patrol.rviz.world_model "$@"
