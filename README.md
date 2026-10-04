# 工程

コマンドはリポジトリのルート `~/work/drone` で実行する。

1. 環境を一度だけ用意する。
2. 機体とつなぐ。DJI Fly と mini3_bridge は同時にはつながれない。
3. 映像を PC に保存する。
4. 円パターンでカメラを校正する。
5. ORB-SLAM3 で追跡し、結果を見る。

# 環境設定

このリポジトリに入るのは、mini3_bridge、校正、追跡の自前コードと手順だけである。次の場所は別途用意する。`third_party/` のうち Git に入るのは `README.md` だけである。

| 場所 | 内容 | この環境の固定 |
| --- | --- | --- |
| `third_party/Mobile-SDK-Android-V5/` | DJI Mobile SDK V5 の公式ツリー。参照用。アプリのビルドは Maven の MSDK 5.18.0 を使い、このディレクトリは Gradle モジュールにしない | `dev-sdk-main` の `a48aa4e7` |
| `third_party/ORB_SLAM3/` | 追跡ライブラリ。地図点と姿勢の書き出しは、このリポジトリのパッチを当てた差分である | `master` の `4452a3c4` |
| `third_party/Pangolin/` | ORB-SLAM3 をビルドするためのビューアライブラリ。v0.6 | `dd801d24` |
| `third_party/pangolin-install/` | Pangolin のインストール先。Git リポジトリではない | 下の cmake install |
| `~/work/Android/Sdk/` | Android のコマンドライン SDK。Android Studio は使わない | platform 35、build-tools 35.0.0 |
| `/opt/ros/jazzy/` | rviz2。Ubuntu のパッケージ | ROS 2 Jazzy desktop |
| `.secrets/dji_secrets` | DJI の App Key とアカウント | 手元で書く |

実行してできる次のものも Git に入らない。`mini3_bridge/pc/recordings/`、`mini3_calib/out/`、`slam/out/`、`slam/build/`、`slam/offline_mono`。

OS はこの環境と同じ Ubuntu 24.04 を想定する。コマンドはリポジトリのルートで実行する。

## 1. パッケージを入れる

```bash
sudo apt update
sudo apt install -y \
  unzip wget curl openjdk-17-jdk ffmpeg \
  build-essential cmake pkg-config \
  libopencv-dev python3-opencv python3-numpy python3-pyqt5 \
  libeigen3-dev libboost-serialization-dev libssl-dev \
  libglew-dev libx11-dev
```

`ffmpeg` は PC 側の `ffplay` と保存用の `ffmpeg` に使う。OpenCV は 4.6、校正の円表示は PyQt5 を使う。

## 2. 管理していないリポジトリをクローンする

```bash
git clone --branch dev-sdk-main https://github.com/dji-sdk/Mobile-SDK-Android-V5.git third_party/Mobile-SDK-Android-V5
git -C third_party/Mobile-SDK-Android-V5 checkout a48aa4e7811d824c27abfa973f5655579bfb8a77

git clone https://github.com/UZ-SLAMLab/ORB_SLAM3.git third_party/ORB_SLAM3
git -C third_party/ORB_SLAM3 checkout 4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4

git clone https://github.com/stevenlovegrove/Pangolin.git third_party/Pangolin
git -C third_party/Pangolin checkout dd801d244db3a8e27b7fe8020cd751404aa818fd
```

公式の Mobile SDK ツリーは変更しない。ORB-SLAM3 には、時刻付きの点と姿勢を書く差分を当てる。この差分は上流には無い。

```bash
git -C third_party/ORB_SLAM3 apply "$PWD/slam/patches/orbslam3_timed_points.patch"
```

## 3. Pangolin をインストールする

v0.8 は gcc 13 で `cstdint` が無く失敗する。v0.6 も同じ欠落があるので、`slam/patches/pangolin_gcc13.h` を全翻訳単位で読ませる。FFmpeg 6 とは合わないので、FFmpeg 対応は切る。

```bash
cmake -S third_party/Pangolin -B third_party/Pangolin/build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PWD/third_party/pangolin-install" \
  -DBUILD_PANGOLIN_FFMPEG=OFF \
  -DBUILD_EXAMPLES=OFF \
  -DBUILD_TOOLS=OFF \
  -DCMAKE_CXX_FLAGS="-include $PWD/slam/patches/pangolin_gcc13.h"
cmake --build third_party/Pangolin/build -j"$(nproc)"
cmake --install third_party/Pangolin/build
```

`third_party/pangolin-install/lib/cmake/Pangolin/PangolinConfig.cmake` があればインストールできている。

## 4. ORB-SLAM3 をビルドする

語彙は同梱の `ORBvoc.txt.tar.gz` を展開する。約 145 MB の `Vocabulary/ORBvoc.txt` になる。DBoW2、g2o、Sophus を先にビルドし、本体は手順 3 の Pangolin を参照する。

```bash
tar -xf third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt.tar.gz -C third_party/ORB_SLAM3/Vocabulary
cmake -S third_party/ORB_SLAM3/Thirdparty/DBoW2 -B third_party/ORB_SLAM3/Thirdparty/DBoW2/build -DCMAKE_BUILD_TYPE=Release
cmake --build third_party/ORB_SLAM3/Thirdparty/DBoW2/build -j"$(nproc)"
cmake -S third_party/ORB_SLAM3/Thirdparty/g2o -B third_party/ORB_SLAM3/Thirdparty/g2o/build -DCMAKE_BUILD_TYPE=Release
cmake --build third_party/ORB_SLAM3/Thirdparty/g2o/build -j"$(nproc)"
cmake -S third_party/ORB_SLAM3/Thirdparty/Sophus -B third_party/ORB_SLAM3/Thirdparty/Sophus/build -DCMAKE_BUILD_TYPE=Release
cmake --build third_party/ORB_SLAM3/Thirdparty/Sophus/build -j"$(nproc)"
cmake -S third_party/ORB_SLAM3 -B third_party/ORB_SLAM3/build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$PWD/third_party/pangolin-install"
cmake --build third_party/ORB_SLAM3/build -j"$(nproc)"
```

`third_party/ORB_SLAM3/lib/libORB_SLAM3.so` ができていれば、追跡用の実行ファイルは次で作れる。`run.sh` は、`slam/offline_mono` が無いときに同じビルドを呼ぶ。

```bash
scripts/orb_slam3/build.sh
```

## 5. ROS 2 Jazzy を入れる

rviz2 は `/opt/ros/jazzy` のパッケージである。このリポジトリにはクローンしない。`scripts/orb_slam3/show_rviz.sh` が `setup.bash` を自分で読む。

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo apt update
sudo apt install -y curl
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F tag_name | awk -F\" '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo "${UBUNTU_CODENAME:-${VERSION_CODENAME}}")_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install -y ros-jazzy-desktop
```

`/opt/ros/jazzy/setup.bash` があれば使える。

## 6. Android Command-line Tools を置く

Android Studio は入れない。SDK 管理ツールだけを `~/work/Android/Sdk` に置く。

```bash
mkdir -p ~/work/Android/Sdk/cmdline-tools
cd ~/work/Android/Sdk/cmdline-tools
wget https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip
unzip commandlinetools-linux-15859902_latest.zip
mkdir -p latest
mv cmdline-tools/* latest/
rmdir cmdline-tools
```

`~/work/Android/Sdk/cmdline-tools/latest/bin/sdkmanager` があれば配置できている。

## 7. 環境変数を設定する

```bash
cat >> ~/.bashrc <<'EOF'

# Android SDK
export ANDROID_HOME=$HOME/work/Android/Sdk
export ANDROID_SDK_ROOT=$HOME/work/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools
alias android-sdkmanager="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
alias android-adb="$ANDROID_HOME/platform-tools/adb"
EOF

source ~/.bashrc
```

確認する。

```bash
echo "$ANDROID_HOME"
android-sdkmanager --version
```

## 8. ライセンス、platform、build-tools、adb を入れる

```bash
yes | android-sdkmanager --licenses
android-sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0"
android-adb version
```

`android-adb version` が表示され、`$ANDROID_HOME/platforms/android-35` と `$ANDROID_HOME/build-tools/35.0.0` があればビルドに使える。

## 9. 秘密情報を書く

`.secrets/dji_secrets` は Git に入らない。次の3行を書く。

```text
DJI_API_KEY=発行した App Key
DJI_EMAIL=DJI アカウントのメール
DJI_PASSWORD=DJI アカウントのパスワード
```

パッケージ名は `com.fsr.djibridge`。この PC の debug 署名 SHA1 は `BC:FB:ED:B4:CE:1C:49:3E:C8:30:2E:27:80:F4:8B:E0:D2:EC:41:D5`。DJI 開発者サイトで、このパッケージ名と SHA1 に対して App Key を発行しておく。

# 機体とつなぐ

Mini 3 の電源を入れ、RC-N1 とペアリングする。RC-N1 の USB を Pixel 8a の USB-C に挿す。この端子は RC が使う。PC との有線接続には使わない。Pixel 8a と PC は同じ LAN の Wi-Fi につなぐ。

USB デバッグのオンオフでは、どちらのアプリが機体につながるかは変わらない。ホームに戻しただけではアプリは裏で接続を持ったままになる。切り替えるときは、最近のアプリを全部落としてから、相手のプロセスを止める。機体の電源は切らない。

## DJI Fly でつなぐ

1. Pixel 8a で、最近のアプリを全部落とす。画面下から上へスワイプし、開いているアプリをすべて上へスワイプして消す。
2. PC で次を実行する。

```bash
adb shell am force-stop com.fsr.djibridge
```

このあと DJI Fly は機体と自動でつながった。

## mini3_bridge でつなぐ

1. Pixel 8a で、最近のアプリを全部落とす。
2. PC で次を実行する。

```bash
adb shell am force-stop dji.go.v5
```

3. mini3_bridge を開く。ホームで下から上へスワイプし、アプリ一覧の `mini3_bridge` をタップする。PC から開くときは次を実行する。

```bash
adb shell am start -n com.fsr.djibridge/.MainActivity
```

4. 表示が「機体: 接続」ならそのまま使える。「機体: 未接続」のときは、mini3_bridge を前面にしたまま RC-N1 の USB を一度抜き、2 秒待って挿す。USB が未許可なら「USBを許可」を押す。

つながっているときの表示は次のとおり。

```text
SDK: 登録成功
アカウント: LOGGED_IN
USB: 許可済み
機体: 接続
FC: 接続
機種: DJI_MINI_3
```

# 映像を PC に保存する

経路は次のとおり。1280×720 の H.264 を、再エンコードせず PC へ送る。

```text
Mini 3 → RC-N1 → Pixel 8a（mini3_bridge）→ 同じ LAN の Wi-Fi → PC（ffplay）
```

待受より先に転送を始めると失敗する。PC は `192.168.10.14` のポート `5000` で待つ。IP が違うときは次で確認し、アプリのアドレスを合わせる。

```bash
ip -4 addr show | awk '/inet / && $2 !~ /^127\./ {print $2, $NF}'
```

## 1. PC で待受を開始する

このコマンドを動かしたままにする。

```bash
scripts/mini3/recv.sh --port 5000
```

`listening 0.0.0.0:5000` と出れば待受できている。

## 2. アプリを入れて起動する

まだ入っていなければ、PC の IP とポートを渡して起動する。省略すると `192.168.10.14` と `5000`。DJI Fly は止めてから起動する。

```bash
scripts/mini3/install_and_start.sh 192.168.10.14 5000
```

Android が「16KB compatible」と出たら、その画面を閉じてアプリに戻る。4KB ページの端末では映像転送は続行できる。

## 3. 転送を開始する

スマホの表示が「機体: 接続」になってから「転送開始」を押す。PC に `client` と `codec H264 1280x720` が出て、ffplay に映像が出る。

止めるのはスマホの「転送停止」か、PC の Ctrl-C。止めたあと次ができる。`recordings/` は Git に入らない。

```text
mini3_bridge/pc/recordings/20261002_001816.h264
mini3_bridge/pc/recordings/20261002_001816.mp4
```

`1280x720` の H.264 と出れば、受信した解像度のまま保存できている。

```bash
ffprobe -hide_banner mini3_bridge/pc/recordings/20261002_001816.mp4
```

# カメラを校正する

追跡と重ね表示は、同じ `mini3_calib/out/mini3.yaml` を読む。これは円パターンで測った値である。`slam/config/mini3_1280x720.yaml` は、測る前の初期値で、追跡には使わない。校正も 1280×720 のまま行う。

パターンは 27 型フルHD（1920×1080）のモニタに出す。円は 1 行 4 個、5 行、合計 20 個。間隔は 61.1 mm、直径は 51.4 mm。表示スケールは 100% にする。出す画面は `mini3_calib/show_pattern.py` 冒頭の `DISPLAY_NAME` で、初期値は `HDMI-1`（ノートは `eDP-1`）である。

ジンバルは機体を傾けてもカメラを水平に戻す。角度はモニタ側で変える。スタンドは前に約 5°、後ろに約 20° 倒れ、縦に ±90° 回る。機体はほぼ水平のまま、円が映像の端に来る位置へずらす。プロペラは外す。距離は 1.5 m 以上。デジタルズームは使わない。

## 1. モニタに円を出す

```bash
python3 mini3_calib/show_pattern.py
```

閉じるのは `q` か Esc。同じ実行が `mini3_calib/out/pattern.json` に間隔を書く。

## 2. 校正用の映像を保存する

上の「映像を PC に保存する」と同じ待受と転送で、円が写った `.mp4` を作る。

## 3. 動画から画像を選ぶ

動画を先頭から 1 枚ずつ見る。円が 20 個そろい、画面の端で切れていなければ画像にする。そのあと `SKIP_FRAMES` 枚を飛ばす。個数が違う画像と、円が欠けた画像は削除する。条件は `mini3_calib/select_frames.py` 冒頭の `USER_SETTINGS` である。

引数を省略すると `mini3_bridge/pc/recordings/` の mp4 を一つずつ処理する。

```bash
python3 mini3_calib/select_frames.py
```

1 本だけ見るときはパスを渡す。

```bash
python3 mini3_calib/select_frames.py \
  mini3_bridge/pc/recordings/20261002_001816.mp4
```

画像は `mini3_calib/out/frames/動画名/*.png` に書く。同じ動画をもう一度選ぶと、そのフォルダだけ入れ替わる。

## 4. 校正する

引数を付けないと、フォルダを番号で選ぶ。

```bash
python3 mini3_calib/calibrate.py
```

結果は `mini3_calib/out/mini3.yaml`。再投影誤差の RMS と `fx` `fy` `cx` `cy` を標準出力に出す。画像が 6 枚未満だと終了する。1280×720 でないときは、その旨を出す。

## 5. 測ったファイルが両方から読まれる

`scripts/orb_slam3/run.sh` の `SETTINGS` と、`slam/viewer/view.py` の `CAMERA_YAML` は、どちらも `mini3_calib/out/mini3.yaml` を指している。校正をやり直したら、追跡と重ね動画もやり直す。古い点ファイルは、以前の焦点距離で作られている。

# ORB-SLAM3 で追跡する

保存した `.mp4` を PC 上で追跡する。ORB-SLAM3 は Android アプリにはリンクしない。語彙は `third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt`。`slam/offline_mono` が無いときは `run.sh` が `scripts/orb_slam3/build.sh` を先に呼ぶ。

## 1. 追跡する

終わるまで待つ。

```bash
scripts/orb_slam3/run.sh \
  mini3_bridge/pc/recordings/20261002_001816.mp4
```

次ができる。`slam/out/` は Git に入らない。点の 1 行は `t x y z`。`t` は秒。

```text
slam/out/20261002_001816_points.txt
slam/out/20261002_001816_points_poses.txt
```

## 2. 結果を見る

ボクセルを元の映像へ重ねた動画を書く。箱の一辺は `--voxel-div` で、点群の対角長さをこの数で割る。数を小さくすると箱は大きくなる。初期値は `scripts/orb_slam3/view.sh` 冒頭の `VOXEL_DIV` で、いまは 80 である。

```bash
scripts/orb_slam3/view.sh \
  mini3_bridge/pc/recordings/20261002_001816.mp4 \
  slam/out/20261002_001816_points.txt \
  --voxel-div 80 \
  --overlay
```

できたファイルは、入力動画と同じフォルダの `20261002_001816_div_080.mp4` である。名前は入力動画の日時と、`voxel-div` の値である。追跡が落ちたフレームと、大きい方の地図に属さないフレームには重ねない。

# 結果がずれたので、校正からやり直す

`20261002_001816_overlay.mp4` では、箱が壁に貼り付かず、取れる場所も少なかった。校正をやり直すのは、箱の位置を映像に合わせるためである。白い壁を箱で埋めるためではない。

## なぜずれたか

ORB-SLAM3 は、物の名前や面を見ていない。周囲より明るい、または暗い点だけを拾い、その奥行きを単眼で推定する。テレビの絵や文字は点になる。白い壁は点ができない。だから箱は疎らになる。これは校正を直しても変わらない。

箱が映像の上でずれるのは、カメラの焦点距離が実物と違うからである。今回の追跡は `slam/config/mini3_1280x720.yaml` の焦点距離 733 画素を使った。これは公称の画角から作った初期値である。円パターンで測った値は、約 895 画素である。奥行きを計算するときと、箱を映像へ戻すときで、レンズの広がりの前提が違うと、箱は点があった場所からずれる。

単眼では、ほとんど動かなかった点の奥行きは一点に決まらない。その点は壁の手前に浮かぶ。ジンバルは機体の傾きを打ち消すので、機体を傾けても視差は増えない。

## なぜこの順か

1. 円をモニタに出す。円の間隔をミリメートルで知るためである。間隔が分かると、写った円の位置からレンズの広がりを計算できる。
2. その円を、追跡と同じ 1280×720 の転送で撮る。別の解像度で測った焦点距離は、この映像には使えない。
3. 円が欠けたフレームを捨てる。欠けた円を使うと、中心がずれて焦点距離が悪くなる。
4. 残った画像で `mini3.yaml` を作る。
5. 追跡とその yaml を同じにし、重ね表示の焦点距離も同じにする。追跡だけ変えて、重ねる側が 733 のままだと、またずれる。
6. 部屋の映像を、測った設定で追跡し直す。

## 手順

プロペラを外す。距離は 1.5 m 以上。Mini 3 のピントは 1 m より先なので、それより近いと円がぼける。デジタルズームは使わない。

角度はモニタで作る。スタンドは前に約 5°、後ろに約 20°、縦に ±90° 動く。機体はほぼ水平のまま、円が映像の中央と端に来るよう位置をずらす。端まで円が写らないと、周辺の歪みが測れない。

### 1. 円を出す

```bash
python3 mini3_calib/show_pattern.py
```

27 型モニタ（`HDMI-1`）に全画面で出る。表示スケールは 100% にする。閉じるのは `q`。

### 2. 円の映像を保存する

先に PC の待受を動かす。待受が無いと転送は失敗する。

```bash
scripts/mini3/recv.sh --port 5000
```

mini3_bridge が「機体: 接続」になってから「転送開始」を押す。円をいろいろな位置と傾きで映し、「転送停止」で `.mp4` を確定する。

### 3. 使えるフレームだけ残す

```bash
python3 mini3_calib/select_frames.py \
  mini3_bridge/pc/recordings/ここに保存した日時.mp4
```

円が 20 個そろい、画面の端で切れていないフレームだけが `mini3_calib/out/frames/動画名/*.png` に残る。最初の画像を開き、円が欠けていたら `select_frames.py` の `EDGE_PAD` を大きくして、同じコマンドをもう一度実行する。

### 4. 校正する

```bash
python3 mini3_calib/calibrate.py
```

番号で、いま作った動画名のフォルダを選ぶ。`fx` と `fy` が近く、再投影誤差が 1 画素前後なら、その `mini3_calib/out/mini3.yaml` を次へ使う。

### 5. 測ったファイルを使う

追跡は `scripts/orb_slam3/run.sh` の `SETTINGS`、重ね表示は `slam/viewer/view.py` の `CAMERA_YAML` を読む。どちらも `mini3_calib/out/mini3.yaml` を指している。ここを別のファイルに分けない。分けたまま追跡すると、箱を戻すレンズの広がりが追跡と違う。

### 6. 部屋の映像を追跡し直す

校正の前に撮った mp4 を、測った設定でもう一度追跡する。古い点ファイルは、733 画素で作ったものなので使わない。

```bash
scripts/orb_slam3/run.sh \
  mini3_bridge/pc/recordings/20261002_001816.mp4
```

```bash
scripts/orb_slam3/view.sh \
  mini3_bridge/pc/recordings/20261002_001816.mp4 \
  slam/out/20261002_001816_points.txt \
  --voxel-div 80 \
  --overlay
```

`--voxel-div` は箱の一辺である。初期値は `scripts/orb_slam3/view.sh` の `VOXEL_DIV` である。80 のとき、出力は `mini3_bridge/pc/recordings/20261002_001816_div_080.mp4` である。

白い壁が埋まっていなくても、校正は失敗ではない。見るのは、箱がテレビの枠や棚の物の上に載っているかである。まだ浮かんでいる点は、機体を前後に動かした映像が足りない。傾きだけでは奥行きは決まらない。

# rviz2 で地図と自己位置を見る

ORB-SLAM3 の点は、面を埋める点群ではない。角がまばらに並んでいるだけなので、点群として出しても壁には見えない。rviz2 に出すのは次の3つである。

- 箱。重ね動画と同じ立方体を `visualization_msgs/Marker` の `CUBE_LIST` で出す。
- 自己位置。開始カメラを原点にした軌跡を `nav_msgs/Path` で出し、今のカメラを `map` から `camera` への tf で出す。再生が進むと、通った道と今の位置が増えていく。
- 原点。最初に追跡できたカメラの位置を `(0, 0, 0)` にした白い球と、rviz2 の格子である。格子の交点が原点である。

```bash
scripts/orb_slam3/show_rviz.sh
```

点と姿勢のファイル、箱の分割数は `scripts/orb_slam3/show_rviz.sh` 冒頭の `USER_SETTINGS` で変える。Fixed Frame は `map` のままにする。別の枠にすると原点がずれる。止めるのは Ctrl-C。
