#!/usr/bin/env bash
# mini3_bridge をビルドして端末へ入れ、PC の待受先を渡して起動する。
# 使い方: install_and_start.sh [host] [port]
set -euo pipefail

# USER_SETTINGS
HOST_DEFAULT=192.168.10.14                      # 引数を省略したときの PC の IP
PORT_DEFAULT=5000                               # 引数を省略したときの待受ポート
ANDROID_HOME_DEFAULT="$HOME/work/Android/Sdk"   # ANDROID_HOME が未設定のときの SDK
BRIDGE_DIR=mini3_bridge                         # アプリのディレクトリ
DJI_FLY_PACKAGE=dji.go.v5                       # 起動前に止める公式アプリ
ACTIVITY=com.fsr.djibridge/.MainActivity        # 起動する Activity

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="${1:-$HOST_DEFAULT}"
PORT="${2:-$PORT_DEFAULT}"
export ANDROID_HOME="${ANDROID_HOME:-$ANDROID_HOME_DEFAULT}"
ADB="${ANDROID_HOME}/platform-tools/adb"

cd "$ROOT/$BRIDGE_DIR"
./gradlew :app:assembleDebug
"$ADB" install -r app/build/outputs/apk/debug/app-debug.apk
"$ADB" shell am force-stop "$DJI_FLY_PACKAGE"
"$ADB" shell am start -n "$ACTIVITY" --es host "$HOST" --ei port "$PORT"
