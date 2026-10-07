# A01 根拠メモ：入力一式の準備

- 調査作業者：`/root/chapter_supervisor/research_worker`
- 調査日：2026-10-07 UTC。最終資料確認時刻：14:38 UTC。
- 調査計画：`research/A01_plan.md`。対象はA01のみ。章本文ではない。
- 元図：図A `[動画・校正・特徴の辞書を用意する]`。`manifest.json` のA01（order=1）と照合。接続は開始 → A01 → A02。DFDで別々に描かれる保存動画・校正・特徴の辞書を、開始前にそろえる活動に当たる。
- 実施：読み取り専用のコード確認、ネット一次資料参照、PDF保存・文字抽出・該当頁画像確認、本文用根拠整理。実行スクリプト、SLAM、動画再生、ビルド、インストール、実機操作、commitは行っていない。進捗表・他章・既存コードも変更していない。

## 1. 版と観測の区別

| 対象 | 確認結果 |
| --- | --- |
| 主プロジェクトHEAD | `d1265bc35439dd6ca57687ac93c8b3a7310fc681` |
| ORB_SLAM3ローカルHEAD | `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4` |
| 主プロジェクトの対象追跡ファイル | `run.sh`、`offline_mono.cpp`、参照README・設定説明の既存差分なし |
| ORB_SLAM3の既存差分 | `include/System.h` と `src/System.cc` に既存変更あり。今回の調査で追加・変更していない |
| A01に関係する差分の確認 | `System.cc` は先頭のinclude追加と末尾の保存関数追加。コンストラクタ・`TrackMonocular`の処理自体には差分なし。行番号は変更込みの手元ファイルを示す |
| 設定・語彙の追跡状況 | `mini3_calib/out/mini3.yaml` と `third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt` はGit ignore対象。存在と読み取りを確認し、下記SHA-256で識別する |
| ネット版 | 公式GitHubのREADMEを2026-10-07に実際に開いた。Web側HEADは採取していないため、ローカル版と同一だとは主張しない |

以下の記号で根拠を区別する。

- **コード観測**：手元の該当行を実読した事実。
- **資料記述**：公式資料またはローカル説明書が述べる内容。実測の再検証とは区別する。
- **推論**：コードや資料からの帰結。実行結果ではない。
- **未確認**：今回実測や実行検証をしていない点。

## 2. 三入力と呼出し契約

| 入力 | 現行の受け取り方 | 準備時点での意味 | 主な根拠 |
| --- | --- | --- | --- |
| 保存動画 | 利用者が `run.sh VIDEO [POINTS_TXT]` の第1引数として指定 | 時間順の観測画像を供給する。校正値や既存の3次元地図を供給するファイルではない | `scripts/orb_slam3/run.sh:3,16-24,31-35`、`slam/src/offline_mono.cpp:22-30,45-47` |
| カメラ設定YAML | `mini3_calib/out/mini3.yaml` をスクリプトが固定で指定 | 撮影画像のカメラモデル・校正値、画像情報、ORB抽出設定等を与える | `run.sh:13,33`、`System.cc:74-89`、`Settings.cc:143-173` |
| ORB語彙 | `third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt` を固定で指定 | ORB記述子に対応する視覚語彙。画像検索用データベースを準備する材料 | `run.sh:12,32`、`System.cc:119-137`、論文図1 |

コード観測：シェルの引数順と実行ファイルの引数順は違う。

```text
利用者 → run.sh VIDEO [POINTS_TXT]
run.sh → offline_mono VOCABULARY SETTINGS VIDEO POINTS_TXT
                    argv[1]    argv[2]  argv[3] argv[4]
```

- `run.sh:15` はスクリプト位置からリポジトリルート `ROOT` を決める。語彙、設定、実行ファイルは `ROOT` に対する絶対パスになる（12-15、24、31-35行）。
- 動画は21行で受け取った文字列を34行でそのまま渡す。スクリプトは呼出し元の作業ディレクトリを変更しない。したがって相対動画パスは呼出し元の作業ディレクトリ基準になる（コードからの推論）。
- 出力ファイル指定は三つの入力とは別の第4引数。省略時の点ファイルは23行で `ROOT/slam/out/<動画幹>_points.txt` となる。
- `run.sh:26-28` は実行ファイルが実行可能でないとビルドスクリプトを呼ぶ。この調査では `run.sh` を実行していない。
- `offline_mono.cpp:17-25` は引数が4個であることを要求し、順に文字列を格納する。27行で動画を開き、その後39行で `System(vocabulary, settings, MONOCULAR, false)` を構築する。`false` は内部Viewerを使わない指定である（`System.cc:233-242`）。慣性付き単眼を選んでいるわけではない。

## 3. 現行YAMLの読み込み経路と値

コード観測：`mini3.yaml:3` は `File.version: "1.0"`。`System.cc:82-89` で新しい `Settings` が生成される。`Tracking.cc:51-54` はその設定を `newParameterLoader` に渡す。旧経路の `Tracking::ParseCamParamFile` の `Camera.fx` 等を、この設定に適用して説明してはいけない。

| 項目 | 手元ファイルの値 | 型・単位とA01での意味 | 読み込み箇所 |
| --- | --- | --- | --- |
| 設定形式 | `File.version: "1.0"` | 文字列。新Settings経路の選択 | `mini3.yaml:3`、`System.cc:82-89` |
| カメラモデル | `Camera.type: "PinHole"` | 文字列。ピンホール系モデルを選択 | `mini3.yaml:5`、`Settings.cc:184-203` |
| 水平・垂直焦点距離 | `Camera1.fx=895.475604`、`fy=894.667309` | 実数、画素単位。画像上の水平/垂直方向の写り方を表す | `mini3.yaml:9-10`、`Settings.cc:195-203` |
| 主点 | `Camera1.cx=641.024514`、`cy=359.282471` | 実数、画素単位。画像座標での主点位置 | `mini3.yaml:11-12`、`Settings.cc:197-203` |
| 歪み | `k1=0.11208777`、`k2=-0.28496497`、`k3=0.28816471`、`p1=0.00023454`、`p2=0.00024400` | このモデルの係数。無次元。式の詳細はD03で扱う | `mini3.yaml:14-18`、`Settings.cc:205-225` |
| 画像の幅・高さ | `Camera.width=1280`、`height=720` | 整数、画素。校正が対応する元画像サイズの宣言 | `mini3.yaml:20-21`、`Settings.cc:356-364` |
| 設定上のFPS | `Camera.fps=30` | 整数、frames/s。追跡側へ渡る設定値 | `mini3.yaml:22`、`Settings.cc:410`、`Tracking.cc:584-585` |
| 色順 | `Camera.RGB=0` | 整数からboolへ。3チャネル画像はBGRとしてグレー化 | `mini3.yaml:23`、`Settings.cc:411`、`Tracking.cc:586,1568-1581` |
| ORB抽出設定 | `nFeatures=1000`、`scaleFactor=1.2`、`nLevels=8`、`iniThFAST=20`、`minThFAST=7` | 抽出器の個数設定、倍率、段数、閾値。ここでは値と受け渡しだけを扱う | `mini3.yaml:25-29`、`Settings.cc:443-450`、`Tracking.cc:588-601` |

画像座標の説明を本文で使う場合は、原点を画像左上、横を右向き、縦を下向きとする通常の画像座標であることを明記する。焦点距離をメートルと混同しない。A01では投影・歪みの数式を導出しない。

- コード観測：`Settings::readParameter<float>` はOpenCVノードが実数かを確認し、`int` は整数かを確認する（36-79行）。値を整数表記へ不用意に変更すると、実数を要求するキーは型検査で終了し得る。単なる「読めるYAML」では契約を満たさない。
- コード観測：通常の抽出器は `nFeatures`、単眼初期用は `5*nFeatures` で生成される（`Tracking.cc:595-601`）。`nFeatures=1000` を「全段階で必ず1000個」「全段階の上限1000個」と説明しない。検出理論の詳説はA04へ譲る。
- コード観測：`Settings.cc:167-170` はORB設定とViewer設定を読み込む。Viewerを表示しない設定でも、新Settings読込中の必須Viewer値が不要になるわけではない（必須値の読込は453-465行）。
- 資料記述：YAMLコメント7-8行はMini 3下り映像・円グリッドによる計測、再投影RMS 0.5524 px、1280×720を記載する。**このコメントは今回の独立した校正精度検証ではない**。撮影条件、校正元画像、誤差分布、今回使う動画との一致は未確認。

## 4. 解像度・色順・FPSの整合条件

### 4.1 画像と校正のサイズ

コード観測：`mini3.yaml` には `Camera.newWidth` / `Camera.newHeight` がない。`Settings.cc:127-128` のリサイズフラグ初期値はfalseで、356-408行はこれらのキーが見つかったときだけフラグを立て、内部パラメータを設定上の倍率で変える。`System::TrackMonocular` は419-424行でフラグが立っているときだけ画像をリサイズする。現行設定ではその処理に入らない。

コード観測：`offline_mono.cpp` 全体、`Settings::readImageInfo`、`System::TrackMonocular` の入力経路に、デコードした画像の幅・高さと `Camera.width/height` を比較して不一致を拒否する処理はない。設定値の読込は実動画の解像度確認ではない。

推論：この現行設定をそのまま使う場合、渡される画像が校正時と同じ1280×720であることを利用者側で確認する必要がある。さらに、同じサイズでも、別カメラ、デジタルズーム、クロップ、レンズ条件、別の歪み補正などによって画像の写り方が変われば、校正との対応を再確認する必要がある。寸法一致だけは十分条件にならない。

### 4.2 色順

コード観測：`Tracking.cc:1568-1581` は画像チャネル数を見て、`mbRGB` がfalseなら3チャネルでは `COLOR_BGR2GRAY`、4チャネルでは `COLOR_BGRA2GRAY` を使う。入力画像の実際の色順を推測・検出して設定を書き換える処理ではない。今回の動画のデコーダ出力を実測したわけではないので、「実データのBGR確認済み」とはしない。

### 4.3 二つのFPS

コード観測：動画からのFPS取得・30へのフォールバックは `offline_mono.cpp:33-36`、その値による時刻付与は46行。一方、設定の `Camera.fps` は `Settings.cc:410` → `Tracking.cc:585` の `mMaxFrames` に入る。現行ラッパーはYAMLの `Camera.fps` を時刻計算の入力として読んでいない。二つが自動同期されるという説明は誤り。詳細な時刻理論・フォールバックの限界はA03/D02の範囲であり、ここでは区別だけを記録する。

## 5. 語彙と初期化準備

- コード観測：`System.cc:119-130` は `ORBVocabulary` を作り `loadFromTextFile(strVocFile)` を呼ぶ。入力はテキスト形式のORB語彙。任意のバイナリ辞書や校正YAMLを渡す契約ではない。
- 型定義：`include/ORBVocabulary.h:29-30` はDBoW2のORB記述子型を用いた語彙を定義する。
- テキスト読込の実装：`Thirdparty/DBoW2/DBoW2/TemplatedVocabulary.h:1338-1363` はファイルを開き、先頭行を文字列として読み、設定値を解析する。一部の範囲検査失敗でfalseを返す。A01では内部の語彙木理論には入らない。
- コード観測：通常の新規起動経路では語彙読込後に `KeyFrameDatabase(*mpVocabulary)` と `Atlas(0)` を生成する（`System.cc:132-137`）。現行YAMLはAtlas読込指定を持たない（`Settings.cc:472-476`、`System.cc:86,117`）。`Tracking` の初期状態は `NO_IMAGES_YET`、`mbReadyToInitializate=false`（`Tracking.cc:44-49`）。
- 推論：語彙の読み込みやAtlasの器の生成は、撮影場所の初期3次元地図の成立を意味しない。A01の出口は次の画像を処理できる準備であり、初期地図の幾何的成立は後続のA06/A07に属する。

## 6. エラー処理と保証の範囲

| 条件 | 確認できた手元コードの処理 | 断定しないこと |
| --- | --- | --- |
| `run.sh` の引数個数不正 | 16-19行でusageを表示し `exit 1` | 動画や校正の品質検証ではない |
| `offline_mono` の引数個数不正 | 17-19行でusageを表示し `return 1` | 内容が正しい保証ではない |
| 動画のopenに失敗 | 27-30行で `cannot open` と `return 1` | 拡張子だけから再生・デコード可能とは決めない |
| 設定ファイルopenに失敗 | `System.cc:75-79` でエラー表示と `exit(-1)` | YAMLの数値が物理的に正しい保証ではない |
| 新Settingsの必須キー欠落・型不正 | `Settings.cc:36-105` の型別読込で `exit(-1)` | 正しい型の誤校正値まで発見するものではない |
| 未対応カメラモデル | `Settings.cc:270-272` でエラー表示と `exit(-1)` | モデル名だけが合えば実レンズが適合するとは限らない |
| 語彙ローダがfalseを返す | `System.cc:123-128` で語彙パスのエラー表示と `exit(-1)` | あらゆる壊れたファイルを安全・完全に検出できるとは未確認。ローダの全異常系は実行検証していない |
| 設定と動画の寸法・撮影条件の不一致 | 上述の経路に一致判定なし | 起動成功から校正適合やSLAM成功を結論しない |

## 7. ローカル説明書との相違

- `scripts/orb_slam3/README.md:9,40-43` は使用設定を `slam/config/mini3_1280x720.yaml` と記載しているが、現行 `run.sh:13` は `mini3_calib/out/mini3.yaml`。**実際の選択パスはrun.shを根拠に説明する**。
- `slam/docs/orbslam3_settings.md:123-147` も旧設定の節で、焦点距離733.3333などを載せる。今回読み込まれるYAMLの焦点距離895台とは別物。教材へ数値を混ぜない。
- `mini3_calib/README.md:7,51,81-85` は同じ1280×720の画像で校正すること、結果YAMLの保存先が `mini3_calib/out/mini3.yaml` であることを説明する。ここは現行スクリプトの参照先と対応する。README内の撮影条件説明を今回の観測結果だとは扱わない。
- 調査のため、これら既存説明書は修正していない。

## 8. ネット一次情報・論文PDF実読記録

### 8.1 公式README

- 資料：UZ-SLAMLab / ORB_SLAM3公式リポジトリREADME。
- URL：<https://github.com/UZ-SLAMLab/ORB_SLAM3>
- 実読箇所：§2 DBoW2、§4 Running ORB-SLAM3 with your camera、§7 Running Monocular Node、§9 Calibration。
- 要旨：自分のカメラを校正してYAMLを作る手順と、語彙・設定ファイルを指定する起動例を示す。DBoW2は場所認識に使用すると説明する。
- ローカル対応：`run.sh:12-13,31-35` と `System.cc:74-137`。公式の特定カメラ用デモの引数構成を、独自 `offline_mono` の引数と同一とは扱わない。
- 正式論文の書誌：READMEは IEEE Transactions on Robotics 37(6):1874-1890, Dec. 2021 を掲げ、arXivの著者公開版PDFへリンクする。

### 8.2 正式論文に対応する著者公開PDF

- 資料名：Carlos Campos et al., *ORB-SLAM3: An Accurate Open-Source Library for Visual, Visual-Inertial and Multi-Map SLAM*。
- 正規一次配布元：<https://arxiv.org/abs/2007.11898>、固定版PDF <https://arxiv.org/pdf/2007.11898v2>。
- 版：arXiv v2、2021-04-23改訂。PDF表紙に採録済み表示と DOI `10.1109/TRO.2021.3075644`。出版社組版そのものとは区別する。
- キャッシュ：`sources/ORB_SLAM3_2007.11898v2.pdf`（18ページ、5,049,669 bytes）。全文抽出テキストは同名 `.txt`。
- PDFスキルを読んで、Popplerで5-6ページをPNG化し、`view_image` で紙面全体を実際に確認した。ページ番号はPDFの1始まり。紙面右上の番号も確認した。

| PDFページ / 紙面ページ | 節・図・式 | 実読した内容とA01で使える要旨 | コード対応・範囲 |
| --- | --- | --- | --- |
| 5 / 5 | III. System Overview、Figure 1 | 図上部にFrameからExtract ORBへ入る経路、中央にDBoW2 KeyFrame Database内のVisual VocabularyとRecognition Databaseが別項目として描かれる。本文はDBoW2データベースを再局在化・ループ・統合に使うと説明する | 語彙は画像や校正と役割が異なることの根拠。`System.cc:119-137`、`Tracking.cc:1584-1589`。論文図にローカルのrun.shや三ファイル準備箱そのものはない |
| 6 / 6 | IV. Camera Model 冒頭 | カメラモデルを投影・逆投影等のモジュールへ分離し、ピンホールとKannala-Brandt魚眼を提供すると説明する | 校正とカメラモデルの整合が必要という背景。現行 `Camera.type=PinHole` → `Settings.cc:191-203`。魚眼の理論は扱わない |
| 6 / 6 | V.A、式(1)は同頁に存在 | 紙面右下の式(1)は慣性付き状態表現で、A01の入力準備に必要な式ではない | 採用しない。今回のラッパーはMONOCULARであり、この式を本章の説明へ流用しない |

紙面画像：`sources/ORB_SLAM3_2007.11898v2_page-05.png`、`sources/ORB_SLAM3_2007.11898v2_page-06.png`。図や数式の長い転載は本メモにしていない。

### 8.3 補助確認

OpenCV公式 `VideoCapture` リファレンス <https://docs.opencv.org/4.13.0/d8/dfe/classcv_1_1VideoCapture.html> を実読。動画ファイルを開くAPI、`isOpened`、`read` の役割を確認した。今回参照したページではBGRの記述は確認できず、実動画の色順は確認済みとしていない。ネットOpenCV版が実行バイナリのリンク版と同じだとは主張しない。

## 9. A01で使える概念式と具体例

### 9.1 式候補（教材用に導入する整理式。論文の式ではない）

\[
\mathcal U = (V,C,W),\qquad
\operatorname{size}(I_k)=(H_C,W_C)=(720,1280).
\]

- `V`：保存動画を指すファイルパスおよびその動画データ。数値の次元・単位を持つベクトルではない。
- `C`：設定ファイルを読み込んだ名前付き項目の集合。校正に加え画像・抽出・表示等の項目も持つ。
- `W`：ORB視覚語彙（Vocabulary）。幅の記号ではない。
- `I_k`：動画からデコードされ本体へ渡される第 `k` 画像。`k` は整数インデックス、単位なし。画像は行・列・チャネルからなる配列で、この式の `size` はチャネル数を除いた高さ・幅の順と定義する。
- `H_C,W_C`：設定が宣言する元画像の高さと幅。いずれも正整数、単位は画素。`W_C` は幅、`W` は語彙で意味が違うため、初心者向け本文では語彙を `\mathcal V_{ORB}` などに変更してもよい。
- 前提：現行YAMLはリサイズ指定なし。同一カメラと同一画像処理条件に対する校正を用いる。
- 等式は現行組合せで満たすべき**必要な整合条件の一つ**。自動検査式ではない。サイズ一致は校正の正確性、特徴対応の成立、初期地図の成立を保証しない。
- 投影式・歪み式・語彙木の評価式は本章に不要。

### 9.2 実行しない説明例

前提例：リポジトリルートから、既存保存動画を `mini3_bridge/pc/recordings/example.mp4` という名前で指定したと仮定する。このファイルの存在・中身は今回確認しておらず、命令を実行するための手順ではない。

```text
run.shに渡す説明上の値:
    VIDEO = mini3_bridge/pc/recordings/example.mp4

offline_monoへ渡る文字列:
    argv[1] = /home/takuya/work/drone/third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt
    argv[2] = /home/takuya/work/drone/mini3_calib/out/mini3.yaml
    argv[3] = mini3_bridge/pc/recordings/example.mp4
    argv[4] = /home/takuya/work/drone/slam/out/example_points.txt
```

コードによる結果：動画は `VideoCapture`、設定・語彙は `System` に渡る。現在YAMLは1280×720とBGRを宣言し、通常抽出器の設定は1000で初期用抽出器は5000設定になる。これらはファイルと呼出しの静的な追跡結果で、実動画で5000点を検出したという意味ではない。

推論による注意例：外部で動画を640×360へ縮小したのに同じYAMLを渡すと、現行経路はその寸法差を拒否しない。解像度・内部パラメータ・実際の前処理の対応を再確認する必要がある。クロップやデジタルズームの場合も「幅高さだけ変えればよい」とは限らない。語彙を差し替えることは、その校正不一致を補正する操作ではない。

## 10. 未確認事項・障害・小監督への要点

未確認：具体的動画のデコード可否、実寸、色順、FPS、撮影条件、実バイナリとソースの一致、全語彙のローダ通過、YAML校正値の品質。これらは静的調査や起動引数から証明できない。特定不調の原因は断定しない。

取得障害：最初のサンドボックス内 `curl` は `Could not resolve host: arxiv.org` で即時失敗した。Webの正規arXiv経路は成功しており、その後ネット接続が許可された同URLの取得でPDF保存も成功した。別配布元を必要とする資料未取得は残っていない。`rg` は未導入のため `grep` / `find` で代替し、インストールはしていない。

小監督へ渡す主要結論：

1. 三入力は「観測画像」「写り方等の設定」「ORB視覚語彙」で責務が異なる。
2. 実行ファイルの引数は語彙・設定・動画・出力の順。スクリプトの利用者引数は動画・任意出力。
3. 現行設定は `mini3_calib/out/mini3.yaml`、`File.version="1.0"` → `Settings` → `Camera1.*`。古いREADMEの別設定と混ぜない。
4. 寸法・色順・撮影条件等の対応は準備側の責務。正常な読込から幾何整合やSLAM成功は導けない。
5. 語彙はテキスト読込。DB/Atlas生成は初期地図成立ではない。A01の出口は画像処理開始の準備。
6. PDF図1・III節・IV節の該当紙面を確認済み。A01に論文式を追加する必要はなく、整理用の入力組・寸法条件で十分。

## 11. 再現用SHA-256

```text
8efc8a7fd09c0de21309b18dcf208b208be12b61c930aa03811b16f778c1e393  scripts/orb_slam3/run.sh
1331b120b9a359839073ba69599c01499aaaabc3f9f68d4fe8b774ec0f934c5b  slam/src/offline_mono.cpp
c4437955b5b95690ef1fb8aba9b269addfdd0e6944ab8c27fc65fee2a7506e32  mini3_calib/out/mini3.yaml
556526aca464f817611594f0192352328c84deb6ebd1fb646ec99723d90eaf23  third_party/ORB_SLAM3/src/System.cc
bfa34355c01cf497ba5edbc3631fe403fb084e961386b832a62ed12a1fea261e  third_party/ORB_SLAM3/src/Settings.cc
3a3654bcc675f859cce1f2fb28ab32a129e8d734d0ac3d55417ff8b47a013264  third_party/ORB_SLAM3/src/Tracking.cc
f8dd027f7a6cb88129821341194d7f2c75b77b3394257ddd0d2229863d1a3570  third_party/ORB_SLAM3/Vocabulary/ORBvoc.txt
4d119517be7565c9651fbf1e36a330d605b7a534d738558858c96feca7b99156  sources/ORB_SLAM3_2007.11898v2.pdf
```
