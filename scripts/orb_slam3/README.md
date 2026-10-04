# 保存した映像を ORB-SLAM3 で追跡する

## 背景

ORB-SLAM3 の動作確認には、同じ映像を繰り返し再生できるファイルがいる。mini3_bridge が PC に届けるデータは再エンコード前の H.264 なので、`scripts/mini3/recv.sh` がそのバイト列を `.mp4` として保存する。追跡はそのファイルに対して PC 上で行う。

機体は単眼である。電話側ではデコードも再エンコードもしない。ORB-SLAM3 は GPLv3 なので、Android アプリにはリンクせず `slam/` の PC プロセスとして分離している。

この映像は 1280×720 である。TUM 付属の yaml は 640×480 用なので使わない。カメラ設定は `slam/config/mini3_1280x720.yaml`。焦点距離と主点は FHD 用の値に 1280/1920 を掛けた初期値で、歪み係数は Mini 3 Pro の公開値を出発点にしている。この保存だけでは内部パラメータは測っていない。

## 目的

保存済みの `.mp4` から、単眼の地図点とカメラ姿勢をファイルに書く。必要なら、その結果を動画の横に出したり、映像へボクセルを重ねたりする。

このフォルダのスクリプトは次の3つ。

- `build.sh` … `slam/offline_mono` をビルドする
- `run.sh` … 映像を追跡し、点と姿勢を書く
- `view.sh` … 追跡結果を表示する。または動画ファイルに書く

## 使い方

ORB-SLAM3 と Pangolin は `third_party/ORB_SLAM3` と `third_party/pangolin-install` に置いてあること。どちらもこのリポジトリでは管理しない。置き方はリポジトリ直下の README「環境設定」にある。語彙ファイルは `third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt`。

入力の例は `mini3_bridge/pc/recordings/日時.mp4`。`scripts/mini3/recv.sh` がこれを作る。

### 1. 追跡する

```bash
scripts/orb_slam3/run.sh \
  mini3_bridge/pc/recordings/20260930_231500.mp4
```

`slam/offline_mono` が無いときは、先に `build.sh` を呼ぶ。ビルドだけ先に行うときは次。

```bash
scripts/orb_slam3/build.sh
```

`run.sh` は次を固定で渡す。

- 語彙: `third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt`
- 設定: `slam/config/mini3_1280x720.yaml`

点ファイルを省略すると `slam/out/<動画名>_points.txt` になる。姿勢は同じディレクトリに `<動画名>_poses.txt` として書かれる。点の1行は `t x y z`。`t` は秒。

出力先を自分で指定するとき:

```bash
scripts/orb_slam3/run.sh \
  mini3_bridge/pc/recordings/20260930_231500.mp4 \
  slam/out/my_points.txt
```

このとき姿勢は `slam/out/my_points_poses.txt`。`slam/out/` は Git に入らない。

### 2. 結果を見る

左に地図点のボクセル、右に元動画を出す。

```bash
scripts/orb_slam3/view.sh \
  mini3_bridge/pc/recordings/20260930_231500.mp4 \
  slam/out/20260930_231500_points.txt
```

左ドラッグで回転、ホイールで拡大縮小、スペースで一時停止、`q` で終了。再生時刻より後に観測されたボクセルは出さない。点が無いあいだは「地図点なし」。

第3引数以降は `slam/viewer/view.py` に渡る。

| 引数 | 意味 |
| --- | --- |
| `--voxel-div N` | ボクセルの一辺を、点群の対角長さの 1/N にする。初期値は 80 |
| `--poses FILE` | カメラ姿勢。省略すると点ファイルの幹に `_poses.txt` を付けたパス |
| `--save FILE.mp4` | 左右を並べた動画を書いて終了する |
| `--overlay FILE.mp4` | その時刻までのボクセルを元映像へ投影した動画を書いて終了する |
| `--check` | 窓を出さず、点数などを確認して終了する |
| `--dump FILE` | 確認用の数値をファイルに書く |

重ね動画の例:

```bash
scripts/orb_slam3/view.sh \
  mini3_bridge/pc/recordings/20260930_231500.mp4 \
  slam/out/20260930_231500_points.txt \
  --voxel-div 80 \
  --overlay slam/out/overlay_div80.mp4
```

追跡が落ちたフレームと、大きい方の地図に属さないフレームには重ねない。
