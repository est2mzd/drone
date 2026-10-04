# Mini 3 の映像を PC に出す

## 背景

DJI Mini 3 のカメラ映像は、RC-N1 経由で Pixel 8a に H.264 の圧縮データのまま届く。公式の DJI Fly でもその映像は見られる。ほしいのは、その圧縮データを再エンコードせず PC へ送り、PC で表示して保存すること。

公式アプリと mini3_bridge は同時に機体へ接続できない。作業中は DJI Fly を終了しておく。

## 目的

次の経路で、1280×720 の H.264 ライブ映像を PC に出す。

```text
Mini 3 → RC-N1 → Pixel 8a（mini3_bridge）→ 同じ LAN の Wi-Fi → PC（ffplay）
```

このフォルダのスクリプトは、その両端を起動する。

- `install_and_start.sh` … スマホ側。アプリをビルドして入れ、PC の待受先を渡して起動する
- `recv.sh` … PC 側。映像を待受し、表示しながら保存する

スマホは送信先が1つなので、再生と保存でポートを分けない。`recv.sh` が受け取ったバイト列を、表示しながらそのまま書く。

## 使い方

事前に、リポジトリ直下の README にある環境設定と `.secrets/dji_secrets` を済ませておく。Pixel 8a は `adb devices` に出ていること。USB は RC が使うので、出ていなければワイヤレスデバッグで接続する。Pixel 8a と PC は同じ LAN の Wi-Fi につなぐ。

PC の IP を確認する。

```bash
ip -4 addr show | awk '/inet / && $2 !~ /^127\./ {print $2, $NF}'
```

### 1. PC で待受を開始する

転送開始より先に、このコマンドを動かしたままにする。

```bash
scripts/mini3/recv.sh --port 5000
```

`listening 0.0.0.0:5000` と出れば待受できている。表示に使った受信データは `mini3_bridge/pc/recordings/日時.h264` に書く。止めるのはスマホの「転送停止」か、PC の Ctrl-C。止めたあと `.mp4` ができる。

画像列も欲しいときは `--tum` を付ける。`recordings/日時/rgb.txt` と `rgb/*.png` ができる。

```bash
scripts/mini3/recv.sh --port 5000 --tum
```

`recv.sh` の引数はそのまま `mini3_bridge/pc/recv_play.py` に渡る。

| 引数 | 意味 |
| --- | --- |
| `--host` | 待受アドレス。初期値は `0.0.0.0` |
| `--port` | 待受ポート。初期値は `5000` |
| `--fps` | 保存時のフレームレート。初期値は `30` |
| `--tum` | 停止後に TUM 形式の画像列も書く |
| `--no-save` | 表示だけしてファイルを書かない |
| `--out` | 保存先ディレクトリ。初期値は `mini3_bridge/pc/recordings` |

### 2. アプリを入れて起動する

```bash
scripts/mini3/install_and_start.sh 192.168.10.14 5000
```

第1引数は PC の IP、第2引数は待受ポート。省略すると `192.168.10.14` と `5000`。スクリプトは debug APK をビルドして入れ、DJI Fly（`dji.go.v5`）を止めてから mini3_bridge を起動する。

Android が「16KB compatible」と出たら、その画面を閉じてアプリに戻る。DJI のライブラリが 16KB 境界に揃っていないという警告で、4KB ページの端末では映像転送は続行できる。

### 3. スマホで接続を確認して転送する

mini3_bridge の表示が次になっていれば、転送できる。

```text
SDK: 登録成功
アカウント: LOGGED_IN
USB: 許可済み
機体: 接続
FC: 接続
機種: DJI_MINI_3
```

USB が未許可のときは「USBを許可」を押す。ダイアログが裏に隠れることがある。

スマホで「転送開始」を押す。PC に `client` と `codec H264 1280x720` が出て、ffplay の窓に映像が出る。スマホ側は「PC 接続済み。映像待ち」のあと、送信バイトが増えていれば転送中。

接続を待つあいだに Ctrl-C したときは、`client` が出ていないのでファイルはできない。`recordings/` は Git に入らない。

### 4. DJI Fly で機体につなぐ

機体の電源は切らない。

1. Pixel 8a で、最近のアプリを全部落とす。画面下から上へスワイプし、開いているアプリをすべて上へスワイプして消す。
2. PC で次を実行する。

```bash
adb shell am force-stop com.fsr.djibridge
```

このあと DJI Fly は機体と自動でつながった。

### 5. mini3_bridge で機体につなぐ

Fly と mini3_bridge は同時に機体へつながれない。戻すときも、同じ順で相手を落とす。機体の電源は切らない。

1. Pixel 8a で、最近のアプリを全部落とす。
2. PC で次を実行する。

```bash
adb shell am force-stop dji.go.v5
```

3. mini3_bridge を開く。Pixel 8a のホームで下から上へスワイプし、アプリ一覧で `mini3_bridge` をタップする。PC から開くときは次を実行する。表示が「機体: 接続」ならそのまま使える。

```bash
adb shell am start -n com.fsr.djibridge/.MainActivity
```
4. 「機体: 未接続」のときは、mini3_bridge を前面にしたまま RC-N1 の USB を一度抜き、2 秒待って挿す。USB が未許可なら「USBを許可」を押す。
