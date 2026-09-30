# 保存動画の単眼追跡と左右表示

## 結果

`20260930_233924.mp4` を ORB-SLAM3 単眼に通し、地図点 5628 個を書いた。ビューアは左にボクセル 1557 個、右に同じ動画を出す。時刻 7.1 秒では 307 ボクセル、終端では 1557 ボクセル。視点を変えると左の画像が変わる。

追跡が OK だったフレームは 1141 枚中 828 枚。処理時間は 26 秒。初期化は約 7 秒で一度失敗して地図を作り直し、その後マージしている。

## ビルド

| 部品 | 固定 | 備考 |
|---|---|---|
| Pangolin | v0.6 `dd801d24` | v0.8 は gcc 13 で `cstdint` が無く失敗。v0.6 も同じ欠落があり、`slam/patches/pangolin_gcc13.h` を強制 include した。FFmpeg 6 と合わないので FFmpeg 対応は切った |
| ORB-SLAM3 | `4452a3c4` | そのままビルドできた。地図点の書き出しだけ `slam/patches/orbslam3_timed_points.patch` |
| 語彙 | `Vocabulary/ORBvoc.txt` | 同梱アーカイブを展開 |

`Examples/Monocular/mono_euroc` はビルドされた。Machine Hall の公式 zip は取得先が応答しなかった。代わりにこの mp4 の 240 フレーム目から 6 フレームおきの 141 枚を EuRoC のディレクトリ形へ書き、同じ実行ファイルへ渡した。軌跡 `slam/out/f_mini3_check.txt` は 54 行、キーフレーム軌跡は 34 行。確認用の画像列は削除した。

## この動画の数値

- 入力: `Mini3Bridge/pc/recordings/20260930_233924.mp4`（1280×720、30 fps、1141 フレーム）
- 点: `slam/out/20260930_233924_points.txt`（5628 行、`t x y z`、t は 7.133 秒から 34.967 秒）
- ボクセル一辺: 点群の対角の 1/80（0.049）
- 確認画像: `slam/out/viewer_check.png`

## 表示の起動

```bash
python3 slam/viewer/view.py \
  Mini3Bridge/pc/recordings/20260930_233924.mp4 \
  slam/out/20260930_233924_points.txt
```

ウィンドウは 1600×720。左 640 が立方体、右は 960×540 の動画。左ドラッグで回転、ホイールで拡大縮小、スペースで一時停止、`q` で終了。再生時刻より後に観測されたボクセルは出さない。点が無いあいだは「地図点なし」。

点を作り直すとき:

```bash
./slam/offline_mono \
  slam/third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt \
  slam/config/mini3_1280x720.yaml \
  Mini3Bridge/pc/recordings/20260930_233924.mp4 \
  slam/out/20260930_233924_points.txt
```

内部パラメータは対角 82.1° からの初期値のまま。左は疎なボクセルで、部屋の密な立体ではない。
