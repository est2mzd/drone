# D05 根拠メモ：画像とフレーム時刻

A03/D01/D02を再利用し、入力対の接続だけを確認。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。下記はローカル行番号。動画・アプリ・校正は実行していない。

| # | 根拠 | 確認した接続・区別 |
|---|---|---|
| 1 | `slam/src/offline_mono.cpp:33–36,41–47,54` | read成功画像を `cv::Mat frame` で受け、0開始の `int frame_index` から `double timestamp=k/f` を生成して同じ呼出しへ渡す。呼出し後にkを増やす。画像配列と時刻の対であり、画像に時計値を描き込む処理ではない。 |
| 2 | `System.cc:404,419–424,471` | APIは画像 `const cv::Mat&` と時刻 `const double&` を受ける。画像を内部でcloneし、設定が要求するときだけresizeした `imToFeed` と同じtimestampを `GrabImageMonocular` へ渡す。現行YAMLには新寸法指定なし（D03）。 |
| 3 | `Tracking.cc:1566,1584–1589`、`Frame.cc:289–296`、`include/Frame.h:199,271–272` | グレー化後の画像とtimestampをFrame構築へ渡し、`mTimeStamp(timeStamp)` でdoubleの値として保存。`mnId=nNextId++` は別の採番で、`mnId` とstatic `nNextId` は `long unsigned int`。wrapperのkをFrame IDとして引数で渡してはいない。Frame内部の追加構造はD06へ残す。 |
| 4 | [ORB-SLAM3論文v2](https://arxiv.org/pdf/2007.11898v2) PDF5頁=誌面5頁、図1・§III | キャッシュ本文および `sources/ORB_SLAM3_2007.11898v2_page-05.png` を実読。Frame入力→Tracking/Extract ORBという接続を確認。k/f・double型・Frame ID採番は論文図の規定ではなく上記実装根拠。 |

最小整理式は入力 `U_k=(I_k,t_k), t_k=k/f`。`I_k` はk番目の読込成功画像配列（高さH×幅W、必要ならCチャネル。現物の型は未検査）、kは0始まりの入力順整数、fはwrapperが採用したframes/s、tは先頭を0とする相対秒。空間座標を表す式ではない。意味のある等間隔時刻の説明にはfが有限かつ正であることを仮定する（コードはf<1のfallbackだけでfinite検査なし）。f=30なら入力対は `(I_0,0秒),(I_1,1/30秒),(I_2,2/30秒)`。説明例であり実動画の時刻測定ではない。

画像の撮像時刻・ファイル個別時刻・CPU処理時計とは区別する。Frame IDは同一実行で入力順と一致する場面があっても、入力対の時刻やwrapperのkとは別管理の番号であり、一般に同一値と約束しない。リセット等の採番経路の網羅調査は本章で行わない。

固定公式一次ソースの必要箇所も実読：[System.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/System.cc)、[Frame.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Frame.cc)。取得障害なし。実画像の型・寸法・FPS・撮像時刻との一致は未検証。新資料取得なし、D06以降未調査。
