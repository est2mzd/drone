# 保存動画を ORB-SLAM3 に通して左右に表示する

## 結論

できる。入力は `mini3_bridge/pc/recordings/20260930_233924.mp4` とする。1 つのウィンドウの左に地図点のボクセル、右にその動画を出す。

左は部屋の密な立体ではない。ORB-SLAM3 が追えた点を格子に入れた疎なボクセルである。テレビの映像や白い壁では点が少なく、棚や段ボールや机の縁に点が寄る。

## この動画

| 項目 | 値 |
|---|---|
| ファイル | `mini3_bridge/pc/recordings/20260930_233924.mp4` |
| コーデック | H.264 High、yuv420p、B フレーム無し |
| 解像度 | 1280×720 |
| フレーム | 30 fps、1141 枚、38.03 秒 |
| 同じバイト列 | `20260930_233924.h264` |

mp4 を使う。中身は室内をパンした映像で、時計、テレビ、棚、段ボール、机がある。並進があるので単眼の初期化は見込める。同じ elementary stream の `.h264` はコンテナ時刻が無く、ffprobe が 25 fps と読む。追跡には mp4 の 30 fps 時刻を使う。

公称対角 82.1° からの初期内部パラメータ（1280×720）:

- fx = fy = 844
- cx = 640
- cy = 360
- k1 = k2 = p1 = p2 = 0

校正前の値である。この表示確認にはこれで足りる。

## 画面

ウィンドウは横 1600、縦 720。

- 左 640×720。占有ボクセルを立方体として描く。ドラッグで回転、ホイールで拡大縮小。
- 右 960×540 に縮小した動画。余白は黒。スペースで一時停止、`q` で終了。

SLAM が終わってから再生する。再生中に左のボクセルは、その時刻までに観測された点だけを出す。

## 処理

```
20260930_233924.mp4
  → OpenCV でフレームと時刻
  → ORB-SLAM3 TrackMonocular（1280×720 のまま）
  → 地図点 x y z と、その点を初めて見た時刻
  → viewer.py
       左: ボクセル
       右: 同じ mp4
```

ボクセル一辺は、点群の対角長さの 1/80 とする。1 点以上入ったマスを描く。色は高さで分ける。

地図点の取り出しは `Atlas::GetAllMapPoints()` を呼ぶ小さな追加にする。Pangolin の標準ビューアは使わない。左右分割は Python の OpenCV ウィンドウで行う。ORB-SLAM3 のビルド自体は Pangolin を必要とするので、Pangolin は依存として入れる。

追跡に失敗した区間があっても、それまでにできた点は左に出す。点が 0 のときは左に「地図点なし」と書く。

## 作るファイル

| パス | 役割 |
|---|---|
| `third_party/Pangolin` | ORB-SLAM3 のビルド依存 |
| `third_party/ORB_SLAM3` | 固定コミット。gcc 13 用パッチを `slam/patches/` から当てる |
| `slam/config/mini3_1280x720.yaml` | 上の初期内部パラメータ、fps 30、特徴点 1500 |
| `slam/src/offline_mono.cpp` | mp4 を読み、`TrackMonocular` し、点と初観測時刻を書く |
| `slam/viewer/view.py` | 左ボクセル、右動画 |

出力は `slam/out/20260930_233924_points.txt`。1 行が `t x y z`。`t` は秒。

## 作業順

1. Pangolin と ORB-SLAM3 をビルドする。公式の EuRoC 単眼例が軌跡ファイルを書くことだけ確認する。
2. `offline_mono` でこの mp4 を処理し、`points.txt` の行数を記録する。
3. `view.py` で左右表示を出す。動画が最後まで再生でき、左をマウスで回せることを確認する。

Android とライブ TCP はこの範囲に入れない。

## 確認

```bash
./slam/offline_mono \
  third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt \
  slam/config/mini3_1280x720.yaml \
  mini3_bridge/pc/recordings/20260930_233924.mp4 \
  slam/out/20260930_233924_points.txt

python3 slam/viewer/view.py \
  mini3_bridge/pc/recordings/20260930_233924.mp4 \
  slam/out/20260930_233924_points.txt
```

成功は次の 3 つ。

- 右にこの室内動画が再生される。
- 左に立方体のボクセルがあり、ドラッグで視点が変わる。
- 再生が進むと、後から観測された点のボクセルが増える。
