# A03 根拠メモ：画像読込と時刻付与

確認日2026-10-07。A03計画確認済み。接続：D01動画・D02 FPS→D05画像/時刻→A04。画像取得はA02と重なる。

版はA01継承（主HEAD `d1265bc3`、ORB_SLAM3 `4452a3c4`）。`slam/src/offline_mono.cpp` は差分なし・SHA一致。Lは同ファイルの行番号、本体パスは `third_party/ORB_SLAM3/src/` 基準。

| # | 根拠 | 確認内容・本文で使える結論 |
| --- | --- | --- |
| 1 | コードL33-36 | `capture.get(CAP_PROP_FPS)` をdoubleへ格納し、`fps < 1.0` のときだけ30.0へ置換。撮影レートの実測ではない。 |
| 2 | 公式OpenCV get/プロパティ文書 | CAP_PROP_FPSはフレームレート。getはプロパティ値を返し、バックエンド非対応の場合0を返すと説明する。プロパティの実効挙動はバックエンド等に依存する。 |
| 3 | コードL41-47、公式read文書 | `cv::Mat frame` に次のデコード画像を受け取り、read成功時だけ `timestamp` を生成して `TrackMonocular(frame,timestamp)` を呼ぶ。 |
| 4 | コードL42、46、54 | `frame_index` は0開始で本体末尾に1増える。生成時刻は `static_cast<double>(frame_index)/fps`。整数除算ではない。 |
| 5 | コードmain全体 | 各画像のファイル内時刻、撮像時刻、現在時刻を取得してtimestampへ代入する処理はない。採用FPSから等間隔の経過時刻を構成する。 |
| 6 | `System.cc:404,419-424,471`、`Tracking.cc:1566,1584-1589`、`Frame.cc:289-291` | System→GrabImageMonocular→Frameへ、画像と同じtimestampを渡す。FrameはmTimeStampへ保存する。 |
| 7 | コードL45-55 | mainはTrackMonocularの呼出し後に次のreadへ進む逐次ループ。FPSへ合わせるsleepやwaitはない。ただし本体内部に待機が一切ないとの主張ではない。 |
| 8 | コードL44、57-65 | `steady_clock` の差はループ前から終了・保存処理後までの処理側経過秒。timestampとは別で、コンストラクタ完了前は含まず、終了・保存の時間は含む。 |
| 9 | PDF5頁/紙面5、図1・III節 | キャッシュ本文と画像を再実読。図はFrame→TrackingのExtract ORB、本文はTrackingによる入力処理を示す。k/f式や30への代替処理はこの図・節にはない。 |

整理式：`t_k=k/f`。kは0始まりの読込成功画像番号（整数、単位なし）、fはこのラッパーが採用したFPS（frames/s）、t_kは先頭を0とする秒。意味のある等間隔時刻として読むにはfが有限かつ正で、一定レートとみなせることが前提。空間座標系を扱う式ではない。f=30ならk=0,1,2に対し0,1/30,2/30秒となる。実測でなく計算例。

ネット一次資料（OpenCV 4.13.0、実読済み）：

- [VideoCapture](https://docs.opencv.org/4.13.0/d8/dfe/classcv_1_1VideoCapture.html)：get節（表示行397-417）、read節（601-617）。
- [Video I/O properties](https://docs.opencv.org/4.13.0/d4/d15/group__videoio__flags__base.html)：CAP_PROP_FPSとプロパティ一般注記（表示行208、218）。
- [ORB-SLAM3論文v2](https://arxiv.org/pdf/2007.11898v2)：`sources/ORB_SLAM3_2007.11898v2.pdf`、同名txt、`..._page-05.png`を再利用。論文式の採用なし。

未確認・限界：動画実行・再生なし。実データのFPS、可変レート、欠落、バックエンド、OpenCVリンク版は未確認。`fps<1`しか検査せずisfinite検査はないため、非有限値もすべて30へ直るとは説明しない。生成時刻が撮像時刻やファイルの個別時刻に一致する保証、実時間30fpsで処理する保証はない。コード・進捗表・他章に変更なし。
