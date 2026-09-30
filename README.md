
# Clone



# Android SDK

## 1. 必要パッケージを入れる
- Android SDKの展開とJavaビルドに必要なものを入れる。
```bash
sudo apt update
sudo apt install -y unzip wget openjdk-17-jdk
```

## 2. Android SDK用ディレクトリを作る
- SDKをホームディレクトリ配下にまとめる。
```bash
mkdir -p ~/work/Android/Sdk/cmdline-tools
cd ~/work/Android/Sdk/cmdline-tools
```

## 3. Android Command-line Toolsを取得する
- Android Studioを入れずにSDK管理ツールだけ取得する。
- 現時点のLinux向け公式最新版は commandlinetools-linux-15859902_latest.zip です。Android Developers
```bash
wget https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip
```

## 4. Command-line Toolsを配置する
- sdkmanager が期待する cmdline-tools/latest/ 構造にする。
```bash
unzip commandlinetools-linux-15859902_latest.zip
mkdir -p latest
mv cmdline-tools/* latest/
rmdir cmdline-tools
```

確認する。

```bash
ls ~/work/Android/Sdk/cmdline-tools/latest/bin
```

ここに、

```text
sdkmanager
avdmanager
lint
...
```

があればOKです。

## 5. Android SDKの環境変数を設定する
- CursorのターミナルからAndroid SDKを使えるようにする。

```bash
cat >> ~/.bashrc <<'EOF'

# Android SDK
export ANDROID_HOME=$HOME/work/Android/Sdk
export ANDROID_SDK_ROOT=$HOME/work/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools
alias android-sdkmanager="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
alias android-cli="$ANDROID_HOME/cmdline-tools/latest/bin/android"
EOF

source ~/.bashrc
```

確認する。

```bash
echo $ANDROID_HOME
android-sdkmanager --version
android-cli --help
```

- Android公式も、CLI利用時は ANDROID_HOME とSDKツールへのPATH設定を推奨しています。Android Developers

6. Android SDKライセンスに同意する
- GradleがAndroid SDKを使える状態にする。


今は Command-line Tools だけ入っていて、ADBやAndroid Platformはまだ未導入です。
1. platform-tools をインストールする
Pixel 8aとの接続に使う adb を入れる。
android-cli sdk install "platform-tools"

2. adb が入ったことを確認する
$ANDROID_HOME/platform-tools/adb version

3. adb のエイリアスを作る
Android SDK側のADBを確実に使う。
echo 'alias android-adb="$ANDROID_HOME/platform-tools/adb"' >> ~/.bashrc
source ~/.bashrc