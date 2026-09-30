
# 環境設定

このリポジトリのアプリは `Mini3Bridge/`。機体接続と映像の API は Maven の DJI MSDK 5.18.0 を使う。公式ソースは参照用で、ビルドには含めない。`Mobile-SDK-Android-V5/` は `.gitignore` に入っている。

## 1. パッケージを入れる

```bash
sudo apt update
sudo apt install -y unzip wget openjdk-17-jdk ffmpeg
```

`ffmpeg` は PC 側の `ffplay` と保存用の `ffmpeg` に使う。

## 2. 公式 Android SDK をクローンする

リポジトリのルートで実行する。ブランチは `dev-sdk-main`。この環境で参照したコミットは `a48aa4e7`。

```bash
cd ~/work/drone
git clone --branch dev-sdk-main https://github.com/dji-sdk/Mobile-SDK-Android-V5.git
```

公式ツリーは変更しない。Mini3Bridge からこのディレクトリを Gradle のモジュールとしては参照しない。

## 3. Android Command-line Tools を置く

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

## 4. 環境変数を設定する

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

## 5. ライセンス、platform、build-tools、adb を入れる

```bash
yes | android-sdkmanager --licenses
android-sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0"
android-adb version
```

`android-adb version` が表示され、`$ANDROID_HOME/platforms/android-35` と `$ANDROID_HOME/build-tools/35.0.0` があればビルドに使える。

# Mini 3 の映像を PC に出す

## 背景

DJI Mini 3 のカメラ映像は、RC-N1 経由で Pixel 8a に H.264 の圧縮データのまま届く。公式の DJI Fly でもその映像は見られる。ほしいのは、その圧縮データを再エンコードせず PC へ送り、PC で表示すること。

公式アプリと Mini3Bridge は同時に機体へ接続できない。作業中は DJI Fly を終了しておく。

## 目的

次の経路で、1280×720 の H.264 ライブ映像を PC に出す。

```text
Mini 3 → RC-N1 → Pixel 8a（Mini3Bridge）→ 同じ LAN の Wi-Fi → PC（ffplay）
```

## ハードウェア

1. Mini 3 の電源を入れ、RC-N1 とペアリングする。
2. RC-N1 の USB ケーブルを Pixel 8a の USB-C に挿す。この端子は RC が使う。PC との有線接続には使わない。
3. Pixel 8a と PC を同じ LAN の Wi-Fi につなぐ。

## ソフトウェア

- アプリ: `Mini3Bridge/`
- パッケージ名: `com.fsr.djibridge`
- DJI MSDK V5: 5.18.0
- この PC の debug 署名 SHA1: `BC:FB:ED:B4:CE:1C:49:3E:C8:30:2E:27:80:F4:8B:E0:D2:EC:41:D5`
- DJI 開発者サイトで、上のパッケージ名と SHA1 に対して App Key を発行しておく。
- PC に `ffplay` があること。冒頭の `ffmpeg` パッケージに含まれる。
- Android SDK の platform 35、build-tools 35.0.0、adb は冒頭の環境設定で入っている。

## 手順

### 1. 秘密情報を書く

`.secrets/dji_secrets` は Git に入らない。次の3行を書く。

```text
DJI_API_KEY=発行した App Key
DJI_EMAIL=DJI アカウントのメール
DJI_PASSWORD=DJI アカウントのパスワード
```

### 2. PC の IP を確認する

```bash
ip -4 addr show | awk '/inet / && $2 !~ /^127\./ {print $2, $NF}'
```

Wi-Fi のアドレスをメモする。アプリの初期値は `192.168.10.14`、待受ポートは `5000`。

### 3. アプリをビルドして入れる

Pixel 8a が `adb devices` に出ていること。USB は RC が使うので、出ていなければワイヤレスデバッグで接続する。

```bash
cd ~/work/drone/Mini3Bridge
export ANDROID_HOME=$HOME/work/Android/Sdk
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am force-stop dji.go.v5
adb shell am start -n com.fsr.djibridge/.MainActivity --es host 192.168.10.14 --ei port 5000
```

`host` は手順 2 の PC の IP に合わせる。

Android が「16KB compatible」と出たら、その画面を閉じてアプリに戻る。DJI のライブラリが 16KB 境界に揃っていないという警告で、4KB ページの端末では映像転送は続行できる。

### 4. PC で待受を開始する

転送開始より先に、このコマンドを動かしたままにする。

```bash
python3 ~/work/drone/Mini3Bridge/pc/recv_play.py --port 5000
```

`listening 0.0.0.0:5000` と出れば待受できている。表示に使った受信データは、同じプロセスが `pc/recordings/日時.h264` に書く。スマホは 5000 のまま。別ポートは開かない。

止めるのはスマホの「転送停止」か、PC の Ctrl-C。止めたあと `.mp4` ができる。画像列も欲しいときは `--tum` を付ける。

再生は届いたフレームをすぐ出す。ffplay は入力を最大十数MBためて先頭から再生するため、そのまま使うと約25秒遅れた。`recv_play.py` は次でその待ちを捨てる。

- 入力は 30fps として時刻を付ける
- `setpts=0` で、たまったフレームを時刻どおりに待たず表示する
- プローブと demux の待ちを切る

スマホ側は送信待ちを最大8チャンクにし、TCP 送信バッファは 64KB、`TCP_NODELAY` にする。遅れた分を送り続けず、新しいチャンクを優先する。

この状態で、機体を動かしてから PC の絵が追うまでの遅れは1秒弱だった。残る分は機体の圧縮、電波、PC のデコードである。

### 5. スマホで接続を確認する

Mini3Bridge の表示が次になっていれば、転送できる。

```text
SDK: 登録成功
アカウント: LOGGED_IN
USB: 許可済み
機体: 接続
FC: 接続
機種: DJI_MINI_3
```

USB が未許可のときは「USBを許可」を押す。ダイアログが裏に隠れることがある。出ないときは、Mini3Bridge を前面にしたまま RC-N1 の USB を一度抜き差しする。

### 6. 転送を開始する

スマホで「転送開始」を押す。PC に次のように出て、ffplay の窓に映像が出る。

```text
client ('192.168.10.11', ...)
codec H264 1280x720 ffplay -f h264
video ... ~2600 kbps
```

スマホ側は「PC 接続済み。映像待ち」のあと、送信バイトが増えていれば転送中。

# ORB-SLAM3 用に映像を保存する

## 背景

ORB-SLAM3 の動作確認には、同じ映像を繰り返し再生できるファイルがいる。Mini3Bridge が PC に届けるデータは再エンコード前の H.264 なので、そのバイト列をそのまま保存する。

## 目的

スマホは送信先が1つなので、再生と保存でポートを分けない。`recv_play.py` が受け取ったバイト列を、表示しながらそのまま書く。

1 回の転送で次のファイルを作る。

- `recordings/日時.h264` … 受信した素の映像
- `recordings/日時.mp4` … 上をコピーしただけのもの。再生とフレーム取り出しに使う
- `--tum` を付けたとき `recordings/日時/rgb.txt` と `rgb/*.png` … ORB-SLAM3 の `mono_tum` が読む並び

## 手順

### 1. 待受を開始する

```bash
cd ~/work/drone/Mini3Bridge
python3 pc/recv_play.py --port 5000 --tum
```

画像列が不要なら `--tum` を外す。スマホのポートは `5000` のまま。

### 2. スマホで転送開始を押す

PC に `client` と `video ... kbps` が出て、ffplay に映像が出ていれば保存も始まっている。`save ...h264` がそのファイルである。

### 3. 止めてファイルを確定する

スマホの「転送停止」か、PC の Ctrl-C。そのあと `.mp4` と、`--tum` なら画像列ができる。接続を待つあいだに Ctrl-C したときは、`client` が出ていないのでファイルはできない。

```text
Mini3Bridge/pc/recordings/20260930_231500.h264
Mini3Bridge/pc/recordings/20260930_231500.mp4
Mini3Bridge/pc/recordings/20260930_231500/rgb.txt
Mini3Bridge/pc/recordings/20260930_231500/rgb/000000.png
```

`recordings/` は Git に入らない。

### 4. 保存できていることを確認する

```bash
ffprobe -hide_banner Mini3Bridge/pc/recordings/20260930_231500.mp4
```

`1280x720` の H.264 と出れば、受信した解像度のまま保存できている。

### 5. ORB-SLAM3 に渡す

`mono_tum` の引数は、`rgb.txt` があるディレクトリ。

```bash
./Examples/Monocular/mono_tum Vocabulary/ORBvoc.txt カメラ設定.yaml \
  ~/work/drone/Mini3Bridge/pc/recordings/20260930_231500
```

TUM 付属の yaml は 640×480 用なので、この映像には使わない。1280×720 用のカメラ内部パラメータを書いた yaml を別に用意する。この保存では内部パラメータは測っていない。