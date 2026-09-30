# DJI Mini 3 の映像で ORB-SLAM3 単眼 VSLAM を動かす計画

## 目的

RC-N1 経由で Pixel 8a に届き、`Mini3Bridge` が PC へ送っている圧縮映像を PC 上でデコードし、ORB-SLAM3 の単眼モードでカメラ軌跡と疎な地図を出す。

v1 の成果物は、任意スケールのカメラ軌跡（EuRoC 形式）と Pangolin のビューアである。メートル単位への合わせは、軌跡が安定してから GPS と高度で行う。

## 制約

- 画像源は `Mini3Bridge` の下り映像とする。`ICameraStreamManager.addReceiveStreamListener` のバイト列を、既存 TCP メッセージのまま PC で受ける。
- 電話側でデコードも再エンコードもしない。ORB-SLAM3 は PC プロセスにする。
- 公式ツリー `Mobile-SDK-Android-V5/` は変更しない。
- v1 では `Mini3Bridge` の Android 側も変更しない。転送プロトコル（type `1` コーデック、type `2` チャンク）をそのまま読む。
- 機体は単眼である。ステレオと RGB-D は対象外とする。
- ORB-SLAM3 は GPLv3 である。Android アプリにはリンクせず、`slam/` の PC プロセスとして分離する。
- 推定するのはジンバルカメラの姿勢である。機体ボディ姿勢への変換は、ジンバル角を別メッセージで送る次の作業で行う。

## 単眼にする理由

ORB-SLAM3 の慣性モードは、フレームと時刻が揃った加速度・角速度を高い頻度で必要とする。今 MSDK から確実に取れるのは `KeyAircraftLocation`、`KeyAltitude`、`KeyAircraftVelocity`、機体姿勢、`KeyGimbalAttitude` である。これらは GPS と姿勢であって、慣性モードが要求する IMU サンプルではない。

v1 は `System::MONOCULAR` と `TrackMonocular` に固定する。IMU 生データが Mini 3 の MSDK でフレーム同期して取れると確認できたときだけ、別作業で単眼慣性へ進む。

単眼の軌跡は相似変換（回転・平行移動・スケール）の不定性が残る。ビューア上の形が飛行と一致すれば v1 は成功とする。

## この PC の前提

確認日 2026-09-30。

| 項目 | 状態 |
|---|---|
| g++ | 13.3.0 |
| CMake | 3.28.3 |
| OpenCV | 4.6.0（pkg-config 済み） |
| Eigen | 3.4.0 |
| FFmpeg | 6.1.1 |
| Pangolin | 未導入。ソースからビルドする |
| CPU / メモリ | 20 スレッド、62 GiB |

gcc 13 と OpenCV 4.6 では、上流 ORB-SLAM3 が `std::random_shuffle` や `usleep` でビルドに失敗することがある。修正は `slam/patches/` に置き、上流ディレクトリへの手編集はパッチ適用で再現できるようにする。

## データの流れ

```
Mini 3
  → RC-N1 → Pixel 8a
  → Mini3Bridge ReceiveStreamListener
  → TCP（既存。uint32 長、type 1 / type 2）
  → slam 受信
  → FFmpeg でデコード（-f h264 または hevc）
  → 固定解像度のグレー画像と単調増加の時刻
  → ORB_SLAM3::System::TrackMonocular
  → CameraTrajectory.txt と Pangolin
```

type `1` の MIME で `-f h264` か `-f hevc` を選ぶ。幅と高さが変わったら追跡を止め、新しい設定で初期化し直す。デコード後にビューア用の縮小を掛ける場合、キャリブレーションも縮小後の画像で行う。

時刻は、デコードし終えたフレームを PC が読み切った時点の `CLOCK_MONOTONIC` 秒とする。DJI のチャンクにコンテナの PTS は無い。実装の最初にフレーム間隔の中央値とばらつきをログし、間隔が荒れる場合は名義 fps で刻む方へ切り替える。

リアルタイムで `TrackMonocular` が間に合わないフレームは捨てる。捨てたフレームの時刻は進め、処理したフレームの時刻だけを渡す。

## カメラモデル

Mini 3 の公称は対角画角 82.1°、35mm 換算 24mm、f/1.7、ピント 1 m〜∞ である。下り解像度は録画設定と一致しない。`info.width` と `info.height` を正とする。

公称画角からの焦点距離は、キャリブレーション前にパイプラインを通すための初期値にだけ使う。ピンホールモデルで歪み係数は 0 から始める。追跡の合否は、同じ解像度・同じ縮小で撮ったキャリブレーション後の値で判断する。

キャリブレーションは OpenCV のチェスボード（内角 9×6 程度）とする。ピントが 1 m より先なので、ボードは 1.5 m 以上に置き、プロペラを外した機体を手で持って下り映像を録る。デジタルズームは使わない。集めた画像はデコードと縮小を SLAM と同じ経路に通してから `calibrateCamera` にかける。

`slam/config/mini3_mono.yaml` に書く項目:

- `Camera.type: PinHole`
- `Camera.fx fy cx cy`
- `Camera.k1 k2 p1 p2`
- `Camera.fps`（実測の名義値。下りが 30fps なら 30、処理間引き後ならその値）
- `Camera.RGB: 0`（グレーで渡す）
- `ORBextractor.nFeatures: 1500`
- `ORBextractor.scaleFactor: 1.2`
- `ORBextractor.nLevels: 8`
- `ORBextractor.iniThFAST: 20`
- `ORBextractor.minThFAST: 7`

特徴点を 1500 にしたのは、地上テクスチャが細かい空撮で 1000 だと初期化が遅れ、2000 だとこの CPU でも取りこぼしが増える、その中間である。実測で追跡が落ちるなら 2000 まで上げる。

## 飛ばし方

初期化には並進視差が要る。ホバリングしたままヨーだけ回すと単眼は初期化できない。

- 高度 15〜40 m
- ジンバル俯角 30〜60°（地面が画面の大半を占める）
- 前進 2〜4 m/s を 10 秒以上
- その後、同じ場所へ戻る周回を 1 回（ループクローズの確認）
- 道路、建物、岩など模様がある場所。水面、雪、一様な芝生、空は避ける
- 露出が激しく跳ねる場面は避ける

## 作るもの

上流 ORB-SLAM3 は `slam/third_party/ORB_SLAM3` に固定コミットで置く。語彙ファイル `ORBvoc.txt` はリポジトリ付属のものを使う。

| パス | 役割 |
|---|---|
| `slam/third_party/ORB_SLAM3` | 固定コミット。パッチ適用後にビルド |
| `slam/patches/` | gcc 13 / OpenCV 4.6 向けの差分 |
| `slam/third_party/Pangolin` | ビューア依存。まず 0.8。コンパイル不能なら 0.6 に固定 |
| `slam/CMakeLists.txt` | `libORB_SLAM3.so` をリンクする自前ターゲット |
| `slam/config/mini3_mono.yaml` | 上記カメラと ORB 設定 |
| `slam/src/tcp_stream.cpp` | 既存 TCP の type 1 / 2 を読む。`recv_play.py` と同じ並び |
| `slam/src/decode.cpp` | FFmpeg へ elementary stream を渡し、固定サイズのグレーフレームを返す |
| `slam/src/offline_mono.cpp` | 保存済み `.bin` または動画から `TrackMonocular` |
| `slam/src/live_mono.cpp` | 待受してライブ追跡。ビューアオン |
| `slam/src/calib_capture.cpp` | キャリブレーション用にデコードフレームを間隔を空けて保存 |

`offline_mono` を先に作る。ライブの前に、同じバイト列で初期化と軌跡保存が再現できる状態にする。

ビルドの健全性確認は EuRoC の `mono_euroc` で行う。ここで失敗した場合は Mini 3 の映像の問題ではない。

## 作業順

各ステップの結果は、このフォルダに連番で残す。

1. `002_orbslam3_build.md`  
   Pangolin と ORB-SLAM3 をビルドし、EuRoC 単眼サンプルが軌跡ファイルを書くところまで。パッチ内容と固定したコミットを残す。
2. `003_downlink_frames.md`  
   実機の下りを短時間 `.bin` 保存し、MIME、幅、高さ、デコード後 fps、フレーム間隔を記録する。SLAM 解像度をここで固定する。
3. `004_calibration.md`  
   同じ解像度でチェスボードを撮り、`mini3_mono.yaml` の内部パラメータを更新する。再投影誤差を残す。
4. `005_offline_track.md`  
   前進を含む飛行の `.bin` を `offline_mono` に入れ、初期化、キーフレーム軌跡、可能ならループクローズを確認する。
5. `006_live_track.md`  
   `live_mono` で飛行しながらビューアが追従することを確認する。処理 fps、捨てたフレーム数、ロスト回数を残す。
6. `007_metric_scale.md`  
   電話から GPS・高度・ジンバル角を type `3` で追加し、軌跡と Sim(3) で合わせる。Android 側の変更はこのステップで初めて入る。

ステップ 6 まで Android の再ビルドは不要である。

## 確認手順

### ビルド

1. `mono_euroc` が Machine Hall のサンプルで完走し、`CameraTrajectory.txt` が空でないこと。
2. 自前の `offline_mono --help` が語彙ファイルと yaml のパスを要求すること。

### オフライン追跡

1. 前進を含む 30 秒以上の `.bin` を入力する。
2. ログに初期化成功が出ること。
3. 軌跡の水平形状が、飛んだ直線または周回に対応すること。スケールは問わない。
4. 周回データでは、終端が始端の近くへ戻ること。

### ライブ

1. 公式アプリを終了し、RC-N1 で Pixel 8a を接続する。PC と電話は同じ LAN の Wi-Fi にする。
2. `live_mono` を起動し、アプリにその IP とポートを入れて転送を開始する。
3. ホバリングのあと前進したとき、ビューアの地図が伸びること。
4. 解像度変更が来たら追跡をリセットしたログが出ること。

## うまくいかないときの切り分け

| 現象 | 次に見ること |
|---|---|
| 初期化しない | 並進があるか。画面の大半が地面か。`nFeatures` を 2000 にする |
| すぐにロストする | 下り解像度と yaml の解像度が一致しているか。歪み係数が 0 のままか |
| 軌跡が曲がる | フレーム間隔のログ。キャリブレーションをやり直す |
| 処理が追いつかない | 幅を 960 以下に固定してから内部パラメータをスケールする |
| 圧縮で特徴が潰れる | 機内録画の MP4 を同じ `offline_mono` に通す。ライブ下りは使わない |

機内録画へ切り替える場合も ORB-SLAM3 の呼び出しは同じである。入力が `.bin` から MP4 に変わるだけとする。
