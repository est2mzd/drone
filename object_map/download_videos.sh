#!/bin/bash
# video_sources.txt の室内映像を object_map/videos/ に保存する。
set -u
cd "$(dirname "$0")/.."

# USER_SETTINGS
MAX_HEIGHT=720 # 保存するときの縦の上限
OUT_DIR=object_map/videos # 保存先。Git には入れない
SOURCE_LIST=object_map/video_sources.txt # 種別、ファイル名、秒範囲、URL

mkdir -p "$OUT_DIR"
while read -r kind name range url _; do
  case "$kind" in
    ""|\#*) continue ;;
  esac
  out="$OUT_DIR/${name}.mp4"
  if [ -s "$out" ]; then
    echo "skip $name"
    continue
  fi
  start="${range%-*}"
  length=$(( ${range#*-} - start ))
  if [ "$kind" = "youtube" ]; then
    .venv-da3/bin/yt-dlp --no-playlist --retries 3 --no-continue \
      --force-keyframes-at-cuts --download-sections "*${range}" \
      --merge-output-format mp4 \
      -f "bv*[height<=${MAX_HEIGHT}][ext=mp4]/b[height<=${MAX_HEIGHT}]/b" \
      -o "$out" "$url" || echo "failed $name"
  elif [ "$kind" = "pexels" ]; then
    src="$(.venv-da3/bin/yt-dlp --extractor-args generic:impersonate -f 0 --print "%(url)s" "$url" | sed 's/#.*//')"
    ffmpeg -y -t "$length" -i "$src" -vf "scale=-2:${MAX_HEIGHT}" -an \
      -c:v libx264 -preset veryfast -crf 23 "$out" || echo "failed $name"
  else
    echo "unknown kind $kind"
  fi
done < "$SOURCE_LIST"
