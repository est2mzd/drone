# D01 調査計画：保存動画と映像入力の意味

- 図DFD/境界図の保存動画、O02→A03を対象とする。現行オフラインwrapperへ渡すファイル・圧縮映像・復号画像の区別を扱い、通信/収録実装はO02、FPSはD02へ残す。
- 実作業者はslam/src/offline_mono.cppと関係READMEの必要箇所を読み、引数/VideoCapture/isOpened/read/cv::Mat/TrackMonocularの入力境界を確認する。拡張子/コーデック/色/サイズ/完全性をコードだけから過剰に保証しない。
- オンライン一次OpenCV VideoCapture/open/isOpened/readと必要ならMat文書を実読。取得済みORB-SLAM3 PDF5頁の入力Frame/Trackingの本文・図画像を本章の観点で再確認し、論文の入力系と自前ファイル読込の違いを示す。
- 最小画像列表現を採用する場合、I_kと添字/画素数/チャネル/値域・型・8bit前提を明記。cv::Mat一般が必ずuint8三色画像という説明は避ける。開けることと全フレーム復号/画質/撮像時刻の保証を分ける。
- research/D01_evidence.mdへ4〜6件程度の根拠表と未確認点を保存し即通知。動画/アプリの実行、コード変更、次章先行は禁止。受領後小監督が80〜110行の本文・自己監査を作成する。
