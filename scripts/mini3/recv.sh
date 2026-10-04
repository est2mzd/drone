#!/usr/bin/env bash
# PC で Mini 3 の映像を待受し、表示しながら保存する。
# 使い方: recv.sh [--port 5000] [--tum] ほか recv_play.py の引数
# 転送開始より先に起動したままにする。止めるのは Ctrl-C。
set -euo pipefail

# USER_SETTINGS
BRIDGE_DIR=mini3_bridge          # アプリのディレクトリ
RECV_SCRIPT=pc/recv_play.py      # PC 側の待受スクリプト

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$ROOT/$BRIDGE_DIR/$RECV_SCRIPT" "$@"
