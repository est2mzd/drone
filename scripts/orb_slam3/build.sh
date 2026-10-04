#!/usr/bin/env bash
# slam/offline_mono をビルドする。Pangolin は third_party/pangolin-install を使う。
set -euo pipefail

# USER_SETTINGS
SLAM_DIR=slam                              # CMake のプロジェクト
PANGOLIN_DIR=third_party/pangolin-install  # Pangolin のインストール先
TARGET=offline_mono                        # ビルドする実行ファイル

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cmake -S "$ROOT/$SLAM_DIR" -B "$ROOT/$SLAM_DIR/build" \
  -DCMAKE_PREFIX_PATH="$ROOT/$PANGOLIN_DIR" \
  -DPangolin_DIR="$ROOT/$PANGOLIN_DIR/lib/cmake/Pangolin"
cmake --build "$ROOT/$SLAM_DIR/build" --target "$TARGET" -j"$(nproc)"
