# D01 根拠メモ：保存動画と映像入力の意味

図位置は保存動画、接続は `O02 → A03`。外側 HEAD `d1265bc35439dd6ca57687ac93c8b3a7310fc681`、ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。保存動画を入力する現行運用に限定し、通信・FPS詳細は扱わない。

| 確認事項 | 根拠と限定 |
|---|---|
| 保存ファイルという入力 | root `README.md:364–374` は保存済み .mp4 を PC で追跡する手順。`scripts/orb_slam3/README.md:1,13,25` も保存ファイルの利用を説明する。後者には古い設定パスがあるため、現行引数は `scripts/orb_slam3/run.sh:12–13,21,31–35` を優先する。VIDEO を第1引数として受け、実行ファイルへ辞書・設定・VIDEO・出力先の順に渡す。収録側の詳細は O02。 |
| wrapper の受入れ境界 | `slam/src/offline_mono.cpp:17–27` は argc==5 を要求し、argv[3] を文字列 video_path として VideoCapture に渡す。拡張子やコーデック、ファイル種別の独自検査はない。run.sh の STEM 生成は出力名を作る操作であり、入力種別の検査ではない。OpenCV の文字列コンストラクタは動画ファイル以外も扱い得るため、「コードが mp4 以外を拒否する」とは説明しない。 |
| 開けたことと画像取得の区別 | wrapper `28–30` は isOpened が false なら入力名をログに出して return 1。OpenCV 4.6公式文書の isOpened はコンストラクタ/open による初期化成功、open は入力を開く処理。各画像の取得・復号は後の read で行う。したがって open 成功から動画全体の復号可能性、画質、追跡に適した画像、撮像時刻の正しさを保証できない。 |
| 符号化された動画と復号画像 | wrapper `41–47` は `cv::Mat frame` を用意し、`capture.read(frame)` が成功した画像を TrackMonocular に渡す。OpenCV read は次の画像の取得と復号を行い、取得不能なら false/空画像となる契約。保存ファイル/その中の符号化映像と、メモリ上の画素配列は異なる段階であり、ORB-SLAM3 へ mp4 のバイト列を直接渡していない。read false の区別と終了は A02/A23 参照。 |
| 画像配列の型と論文上の入力 | OpenCV Mat は一般の多次元配列で、画素深度とチャネル数は型の一部。常に uint8・3チャネルという型ではない。現行 wrapper に frame の型・実寸・色順序を検査するコードはない。ORB-SLAM3 論文 PDF5頁図1は Frame→Tracking/ORB抽出、§III は画像等のセンサ情報から現在姿勢を計算する役割を示す。保存ファイルを VideoCapture で読む具体的な入口は自前 wrapper 側の実装根拠と分ける。 |

説明用に、8bit unsigned の画像例を `I_k∈{0,…,255}^{H×W×C}` と整理できる。`k=0,1,…` は読込順の画像番号、H/W は高さ/幅（画素数）、C はチャネル数、各成分は0〜255の整数。これは画素配列の抽象表現であり、cv::Mat の実メモリ配置や実ファイルの型を測定した結果ではない。I_k 自体は撮像時刻を表さず、画像と時刻を分ける。時刻生成の詳細は A03/D02。

## 一次資料・実読

- [OpenCV 4.6 VideoCapture](https://docs.opencv.org/4.6.0/d8/dfe/classcv_1_1VideoCapture.html)：文字列コンストラクタ、open、isOpened、read の本文を確認。README が記す4.6系列に合わせた文書を使用したが、今回インストール版/バックエンドを実行検査したわけではない。
- [OpenCV 4.6 Mat](https://docs.opencv.org/4.6.0/d3/d63/classcv_1_1Mat.html)：一般配列、型/チャネルの例、CV_8U の値域を確認。
- [ORB-SLAM3 v2](https://arxiv.org/pdf/2007.11898v2)：PDF5頁（誌面5頁）の図1・§III Tracking 本文を画像でも再読。既存 `sources/ORB_SLAM3_2007.11898v2.pdf`、同名 `.txt`、`_page-05.png` を使用。

## 未確認

動画は開いておらず、現物のコンテナ・コーデック・解像度・型・チャネル・欠損・画質・撮像時刻は未検査。README の例を実測値として扱わない。スクリプト/動画/アプリ実行、ビルド、コード変更なし。取得障害なし。後章の通信・FPS詳細へは進んでいない。
