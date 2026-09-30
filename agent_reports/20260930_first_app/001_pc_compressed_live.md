# Pixel 8a から PC へ圧縮映像を転送する計画

## 目的

DJI Mini 3 のカメラ映像を、RC-N1 経由で Pixel 8a に届いた圧縮データのまま PC へ送り、PC で表示する。

Pixel 8a 上の公式アプリでは既に映像が見えている。今回ほしいのはその再表示ではなく、同じ種類の下りデータをこちらのアプリで受け、デコードも再エンコードもせず PC へ渡すことである。

## 制約

- パッケージ名は `com.fsr.djibridge`。DJI MSDK V5 **5.18.0**（クローン済みサンプルと同じ版）を使う。
- 公式リポジトリ `Mobile-SDK-Android-V5/` は変更しない。アプリは `Mini3Bridge/` に独立して置く。
- 公式アプリのメモリや画面は取得できない。MSDK で機体に接続したこのアプリが下り映像を受け取る。公式アプリと同時に機体接続はできない。
- RC-N1 が Pixel 8a の USB-C を使う。飛行中の PC 転送経路は USB ではなく、同じ LAN の Wi-Fi とする。
- Virtual Stick、機内録画、複数カメラ切替、電話画面への映像描画は今回やらない。

## データの取り方

公式サンプル `CameraStreamDetailVM` の `ICameraStreamManager.addReceiveStreamListener` を使う。コールバックの `data`（`offset` から `length` バイト）はデコード前のバイト列で、サンプルはこれを `info.mimeType` の名前を拡張子にしてファイルへそのまま書いている。

電話側では `putCameraStreamSurface` も `addFrameListener`（YUV などの展開後フレーム）も使わない。`ILiveStreamManager` の RTMP 配信も使わない。あれは再エンコードが入る。

接続確認は転送の前提として残す。

- `SDKManager.init` のあと、`INITIALIZE_COMPLETE` で `registerApp`
- `SDKManagerCallback` の機体接続 / 切断
- `FlightControllerKey.KeyConnection`
- `ProductKey.KeyProductType`（Mini 3 であること）

主カメラは `AvailableCameraUpdatedListener` で得た一覧の先頭（通常は `LEFT_OR_MAIN`）を `addReceiveStreamListener` に渡す。

## 転送

Pixel 8a が PC の待受ポートへ TCP 接続する。ソケットは `TCP_NODELAY`、送信バッファは 64KB。送信待ちは最大8チャンクで、溢れたら古いチャンクを捨てて新しいものを送る。Mini 3 の下りは数 Mbps なので、同じ LAN の Wi-Fi では帯域より再エンコードの方が遅延になる。v1 は TCP にする。欠けると次のキーフレームまで画像が崩れるため、まずバイト列を欠かさず届ける。

メッセージは次の並び。複数バイト整数はビッグエンディアン。

| フィールド | 内容 |
|---|---|
| `uint32` | このフィールドを除く残りバイト数 |
| `uint8` type | `1` = コーデック情報、`2` = 映像チャンク |
| payload | type ごとの中身 |

type `1` の payload:

| フィールド | 内容 |
|---|---|
| `uint8` | MIME 名のバイト数 |
| UTF-8 | `info.mimeType.name`（例: `H264` / `H265`） |
| `uint16` | 幅。不明なら `0` |
| `uint16` | 高さ。不明なら `0` |

コーデック情報は受信開始時と、MIME または解像度が変わったときに送る。

type `2` の payload はコールバックのバイト列そのもの。順序はコールバック順を保つ。電話側で Annex-B 変換や NAL 分割はしない。

PC の待ち受けアドレスとポートはアプリの入力欄に置く。

## PC 側の表示

小さい受信プロセスが TCP を受け、type `1` で `-f h264` か `-f hevc` を選び、type `2` のバイト列を ffplay の標準入力へそのまま渡す。

```bash
ffplay -fflags nobuffer -flags low_delay -framedrop \
  -probesize 32 -analyzeduration 0 -fpsprobesize 0 -max_delay 0 \
  -sync ext -vf setpts=0 -framerate 30 -f h264 -i pipe:0
```

H.265 のときは `-f hevc`。

ffplay は入力を最大十数MBためて先頭から再生する。そのままだと約25秒遅れた。30fps で時刻を付け、`setpts=0` でたまったフレームを待たずに出す。スマホ側の送信待ちは最大8チャンク、TCP 送信バッファは 64KB、`TCP_NODELAY`。実測の遅れは1秒弱で、残る分は機体の圧縮、電波、PC のデコードである。

## 実装前の確認

ネットワーク転送の前に、同じリスナーのバイト列を数秒ファイル保存し、`adb pull` して PC の ffplay で再生できることを確認する。ここで MIME と、素の連結バイトが elementary stream として再生できるかを見る。再生できない場合は、DJI 固有ヘッダの有無を切り分けてから転送フォーマットを直す。

## 作るファイル

公式ツリーには手を入れない。

| ファイル | 役割 |
|---|---|
| `Mini3Bridge/settings.gradle` | `:app` のみ |
| `Mini3Bridge/build.gradle` | Android Gradle Plugin 8.7.0、Kotlin 2.1.0 |
| `Mini3Bridge/gradle.properties` | compile/target 35、min 24、`API_KEY` プレースホルダ |
| `Mini3Bridge/gradle/wrapper/gradle-wrapper.properties` | Gradle 8.12 |
| `Mini3Bridge/gradlew` `gradlew.bat` | ラッパー |
| `Mini3Bridge/app/build.gradle` | `applicationId` `com.fsr.djibridge`、`arm64-v8a`、aircraft / aircraft-provided / networkImp、DJI の `.so` を `doNotStrip` |
| `Mini3Bridge/app/proguard-rules.pro` | release 用の最小ルール |
| `Mini3Bridge/app/src/main/AndroidManifest.xml` | 権限、`com.dji.sdk.API_KEY`、USB accessory、Activity |
| `Mini3Bridge/app/src/main/java/com/fsr/djibridge/BridgeApplication.kt` | `SDKManager.init` と `registerApp` |
| `Mini3Bridge/app/src/main/java/com/fsr/djibridge/MainActivity.kt` | 登録・接続・機種、PC のアドレス、転送開始停止、送信量 |
| `Mini3Bridge/app/src/main/java/com/fsr/djibridge/UsbAttachActivity.kt` | RC-N1 の USB 接続で `MainActivity` を開く |
| `Mini3Bridge/app/src/main/java/com/fsr/djibridge/StreamForwarder.kt` | `ReceiveStreamListener` から上記 TCP メッセージを送る |
| `Mini3Bridge/app/src/main/res/layout/activity_main.xml` | 状態表示とアドレス入力。映像用 Surface は置かない |
| `Mini3Bridge/app/src/main/res/values/strings.xml` | 文言 |
| `Mini3Bridge/app/src/main/res/values/themes.xml` | テーマ |
| `Mini3Bridge/app/src/main/res/xml/accessory_filter.xml` | DJI USB accessory。このクローンには公式の同名 XML が無い |
| `Mini3Bridge/pc/recv_play.py` | TCP 待受、コーデック選択、ffplay へパイプ |

`gradle.properties` の API キーは空のプレースホルダとする。DJI 開発者サイトで `com.fsr.djibridge` に発行したキーを実行前に入れる。

## 作業順

1. `Mini3Bridge/` を上記構成で作り、Pixel 8a で SDK 登録と Mini 3 接続表示まで通す。
2. 圧縮チャンクを短時間ファイル保存し、PC で ffplay 再生できることを確認する。
3. `StreamForwarder` と `pc/recv_play.py` を足し、Wi-Fi 経由のライブ表示まで通す。
4. 送信バイト毎秒、チャンクサイズ、画面の崩れ、体感遅延を記録する。TCP のバッファリングが支配的だった場合だけ、欠落に耐える UDP へ切り替える。

## 確認手順

1. 公式アプリを終了し、RC-N1 の USB で Pixel 8a を接続する。PC と Pixel 8a は同じ LAN の Wi-Fi につなぐ。
2. アプリで登録成功、フライトコントローラ接続、機種 Mini 3 を確認する。
3. PC で `recv_play.py` を起動し、アプリにその IP とポートを入れて転送を開始する。
4. PC にライブ映像が出ること、電話側ログの MIME と PC の `-f` が一致することを見る。
