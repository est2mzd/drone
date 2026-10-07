# O02 根拠メモ：mini3_bridge から保存動画まで

Mini 3/RC-N1/Android→PC→保存動画→offline_mono の入力境界に限定。以下の Android ファイルは `mini3_bridge/app/src/main/java/com/fsr/djibridge/`、PC ファイルは `mini3_bridge/pc/` 基準。秘密設定・認証ファイルは読まず、接続先・認証・機器識別の実値を収録しない。実機接続・アプリ起動・録画・実行・改修なし。

| 論点 | 現行コードの根拠と限定 |
|---|---|
| SDK と Android 入口 | `mini3_bridge/app/build.gradle:81–82` は DJI Mobile SDK V5 aircraft/provided **5.18.0**。`SdkController.kt:22–72` は SDK 初期化・登録・製品接続状態のコールバック、`MainActivity.kt:79,94–101,164–174,203–229` は StreamForwarder 生成、転送開始、USB accessory の権限経路。これは接続を扱うコードの存在であり、今回の実機接続成立を示さない。操縦系は別の PatrolCommandBridge（MainActivity:103–127）で、映像転送のパケットと混同しない。 |
| 映像の取得境界 | `StreamForwarder.kt:44–52,60–75,151–165`：利用可能カメラから LEFT_OR_MAIN を優先して選び、ReceiveStreamListener を登録。data の offset/length 範囲を copy し、info から MIME/幅/高さを読む。公式APIは自己復号にも使う生映像ストリームのコールバックであり、復号済みの cv::Mat 画像ではない。この橋渡しコードで画像を再圧縮しているわけでもない。 |
| 独自 TCP メッセージ | `StreamForwarder.kt:171–187,222–234`：4 byte big-endian の body 長、その後1 byte type、payload。type1 は MIME文字列長1 byte＋文字列＋幅/高さ各2 byte、type2 は取得バイト列。撮像時刻・独自連番・フレーム到達確認を追加するフィールドはない。コールバック数/メッセージ数を完全な復号画像数と同一視しない。 |
| キューと送信の限界 | `StreamForwarder.kt:25,75–81,94–111`：容量8のキュー、type2投入失敗時に clear して新しいpacketを再投入。type1 の offer 戻り値は未検査（187）。workerがTCPへwrite/flushし sentBytes を加算するが、sentChunksはコールバック側で増える。これらはPCで全画像を受信・復号した確認値ではなく、アプリ段階でデータを捨て得る。遅延や欠落量は未測定。 |
| PC の主入口と保存 | `scripts/mini3/recv.sh:8–12` が起動するのは **recv_play.py**。`recv_play.py:13` は recv_save の remux/export_tum をimport。`16–30,117–148` は read_exact と長さ/type解析、MIMEによる h264/hevc 選択、type2 payloadをrawファイルへそのまま書き、別途ffplay stdinへ渡す。--no-save分岐あり（74–108）。recv_saveを直接使う経路もあるが主入口と分ける。圧縮ストリーム保存と再生用復号は別処理。 |
| 終了後の MP4 化 | `recv_play.py:156–174` は後始末後、保存あり/受信byteありなら remux。実体 `recv_save.py:73–94` は ffmpeg に `-fflags +genpts -r fps -f fmt -i ... -c copy` を渡し、再エンコードせずコンテナへ格納する指定。fpsはPC引数（既定30）。任意の--tumはPNG列とindex/fpsの時刻表を作る別分岐（97–120）で、今回の通常wrapper入力に必須ではない。 |
| 時刻・時計の境界 | SDK StreamInfoにはフレームレート情報もあるが、この送信コードはMIME/幅/高さだけを送る。PCファイル名の datetime はPC側命名時刻、monotonic は受信量報告、recv_saveのsecondsは受信処理の経過値（143,165–166,221–230）。露光/撮像時刻として保存する設計ではない。FFmpegの入力側-rは一定fpsを仮定して時刻を生成するため、MP4化だけで元の撮像間隔・欠落区間・伝送遅延を復元できるとはしない。 |
| オフライン SLAM との分離 | `slam/src/offline_mono.cpp:27–47` は保存動画を VideoCapture で開き、readで復号画像を得て、k/f秒と組にして TrackMonocular へ渡す。Androidの圧縮チャンクを直接SLAMへ渡す経路ではない。fは動画CAP_PROP_FPS、1未満は30（D02）。映像経路に操縦/テレメトリが存在しても、このMONOCULAR呼出しにIMU/GNSS測定を渡すコードにはならない。 |

最小の境界整理：`SDK圧縮ストリーム → 独自メッセージ化/TCP → PCのraw保存 → MP4への格納 → OpenCV復号 → (画像 I_k, t_k=k/f) → SLAM`。rawはここでは圧縮elementary streamの意味で、未圧縮の画素配列ではない。kは復号してwrapperが処理した入力順、fはfps、tは相対秒。送信チャンク番号でも撮像時計でもない。

仮定例として、転送前のキューclearで一部圧縮データが失われた場合、後段が30fpsのファイルを生成できたとしても、欠落前の露光時刻間隔が正しく記録された証拠にはならない。復号不能・表示乱れ・何画像失うかは実ストリーム依存であり、今回は再現していない。

## 公式一次資料・PDF実読

- DJI公式 [ReceiveStreamListener](https://developer.dji.com/api-reference-v5/android-api/Components/IMediaDataCenter/ICameraStreamManager_ReceiveStreamListener.html)：worker threadのdata/offset/length/StreamInfoコールバック仕様を実読（5.8.0以降）。[ICameraStreamManager](https://developer.dji.com/api-reference-v5/android-api/Components/IMediaDataCenter/ICameraStreamManager.html) はストリーム取得とframe取得のAPIを区別し、受信ストリームの自己復号用途を説明する。[StreamInfo](https://developer.dji.com/api-reference-v5/android-api/Components/IMediaDataCenter/ICameraStreamManager_StreamInfo.html) のMIME/幅/高さ/フレームレートの説明も確認。実依存版は上記Gradleを優先。
- [FFmpeg公式マニュアル](https://ffmpeg.org/ffmpeg.html) のStreamcopy、入力側-r、codec copyを実読。copyは再エンコードなし、入力側-rは一定fps前提の時刻生成。この指定は欠落修復や撮像時計の復元を保証しない。
- [ORB-SLAM3 v2](https://arxiv.org/pdf/2007.11898v2) PDF5頁 §III/図1の入力Frame→Trackingの本文と `sources/ORB_SLAM3_2007.11898v2_page-05.png` を再読。論文はSLAM入力の背景で、このAndroid/TCPプロトコルの仕様ではない。
- 主要一次資料の取得障害なし。DJIリリースページの検索結果には5.18.0情報があるが、本文再取得が空だったため詳細な製品/firmware対応表は根拠に採らない。実際のcodec/FPS/画像寸法・欠落・遅延・同期・通信/保存の完全性は未測定。O03/O04や制御仕様へは進んでいない。
