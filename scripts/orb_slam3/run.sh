#!/usr/bin/env bash
# 保存済み映像を ORB-SLAM3 で追跡し、点と姿勢を slam/out に書く。
# 使い方: run.sh VIDEO [POINTS_TXT]
# POINTS_TXT を省略すると slam/out/<動画名>_points.txt。姿勢は同じ幹の _poses.txt。
set -euo pipefail

# USER_SETTINGS
SLAM_DIR=slam                                              # 実行ファイルがあるディレクトリ
OUT_DIR=slam/out                                           # 点ファイルの初期の出力先
BIN_NAME=offline_mono                                      # 追跡する実行ファイル
BUILD_SCRIPT=scripts/orb_slam3/build.sh                    # 実行ファイルが無いときに呼ぶ
VOCAB=third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt          # ORB の語彙
SETTINGS=mini3_calib/out/mini3.yaml                        # 円パターンで測ったカメラ設定。重ね表示も同じファイルを読む

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 VIDEO [POINTS_TXT]" >&2
  exit 1
fi

VIDEO="$1"
STEM="$(basename "${VIDEO%.*}")"
POINTS="${2:-$ROOT/$OUT_DIR/${STEM}_points.txt}"
BIN="$ROOT/$SLAM_DIR/$BIN_NAME"

if [[ ! -x "$BIN" ]]; then
  "$ROOT/$BUILD_SCRIPT"
fi

mkdir -p "$(dirname "$POINTS")"
exec "$BIN" \
  "$ROOT/$VOCAB" \
  "$ROOT/$SETTINGS" \
  "$VIDEO" \
  "$POINTS"
