#!/usr/bin/env bash
# 追跡結果を表示する。追加引数はそのまま view.py に渡す。
# 使い方: view.sh VIDEO POINTS_TXT [--voxel-div 80] [--overlay out.mp4] [--save out.mp4]
set -euo pipefail

# USER_SETTINGS
VIEWER=slam/viewer/view.py  # 点と映像を出すスクリプト
VOXEL_DIV=80                # 箱の一辺。点群の対角長さをこの数で割る。小さいほど箱は大きい

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ $# -lt 2 ]]; then
  echo "usage: $0 VIDEO POINTS_TXT [view.py options...]" >&2
  exit 1
fi

VIDEO="$1"
POINTS="$2"
shift 2
exec python3 "$ROOT/$VIEWER" "$VIDEO" "$POINTS" --voxel-div "$VOXEL_DIV" "$@"
