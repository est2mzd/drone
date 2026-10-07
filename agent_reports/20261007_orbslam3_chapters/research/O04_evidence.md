# O04 根拠メモ — object_mapの別系統の観測実験

確認日2026-10-07。対象は現行 `object_map/{extract_objects,verify_papers,render_review_video}.py`。外側HEADは `d1265bc35439dd6ca57687ac93c8b3a7310fc681`。ソース静的読解・一次文書・PDF実読のみで、モデル取得/実行、動画解析、再測定、ソース変更は行っていない。

| # | 確認した事実・限定 | ローカル根拠 / 一次資料 |
|---|---|---|
| 1 | `extract_objects` は保存動画をVideoCaptureで開き、標本画像をseek/readして画像ごとに検出と深度を計算する構造。既定2標本、時刻はFPSが正ならindex/fps、そうでなければNone。YAMLは画像番号・画像寸法・検出箱・クラス/score・相対深度統計・画素重心等で、Tcw/世界座標/実寸は含まない。 | `extract_objects.py:97–118,258–324,441–468`。画像YAMLと重ねJPG、summary.yamlが出力先。 |
| 2 | YOLOのローカル `weights/yolo11n.pt` を指定し `predict(imgsz=640,conf=.25)` の最初のResultsから `xyxy/cls/conf` を読む。これは検出箱で、インスタンスの正解マスクではない。公式YOLO11表で同ファイル名はDetection、COCO事前学習系。今回重みの実体/版/ハッシュは検査していない。 | `extract_objects.py:24–27,145–174`。[YOLO11公式](https://docs.ultralytics.com/models/yolo11)、[予測API](https://docs.ultralytics.com/modes/predict)。 |
| 3 | DA3-SMALLをCPUへ置くコードで、BGR→RGBの1画像リストを長辺504指定でinferenceし、`prediction.depth[0]` だけを元画像寸法へ線形resizeする。K/Tcwをモデルに渡さず、予測pose/confも利用しない。公式モデルカードはRelative Depthを明記。単画像間の尺度整合、メートル、測距精度を保証する処理はない。 | `extract_objects.py:22–23,120–142,268`。[DA3-SMALLカード](https://huggingface.co/depth-anything/DA3-SMALL)、[公式API](https://raw.githubusercontent.com/ByteDance-Seed/Depth-Anything-3/main/docs/API.md)の入力/処理解像度/戻り値。 |
| 4 | bbox shrink=.10は幅・高さの各側5%（整数丸めあり）。有限かつ>1e-6の深度だけを分母とし、log深度の許容幅内で個数最大の窓を取る。代表値は`exp(median(log z))`。内側面積400以上、代表値あり、採用tol=.15の比率≥.50でaccepted。dynamicはクラス名によるflagだけで、acceptedを阻止しない。連結成分数も記録のみ。 | `extract_objects.py:28–34,41–95,177–232`。コメント「静止物にはしない」と実際の採用分岐を区別する。 |
| 5 | 平面用Kは特定保存動画名かつ校正ファイル有りの場合にCamera1のKを画像寸法比で拡縮し、他はfx=fy=.9×幅、中心=(幅/2,高さ/2)を仮定する。歪み補正をしない。stride4の有効深度を逆投影、最大6000点から3点RANSAC、単位法線/offsetと相対深度中央値に比例する距離閾値で最大3平面を抽出する。 | `verify_papers.py:22–30,50–117,125–145`。既読ORB-SLAM3 PDF6頁§IVの投影/逆投影説明は幾何の背景で、この近似Kや実験精度の根拠ではない。 |
| 6 | supportは法線と固定`up=(0,-1,0)`の絶対内積角から判定し、IMU重力を測っていない。structureはstride4の有限正深度標本に対する平面内率≥.12。box内の一致/支持/構造マスクや点群の厚み比を比較するが、壁・床・物体クラスの正解、物理体積、通行可能空間を検証する処理ではない。 | `verify_papers.py:119–122,147–212,384–420`。モジュール冒頭2–8行は論文の最適化器を回さないと明記。論文名を付けた集計を原算法の再現評価としない。 |
| 7 | review動画は再び画像ごとの検出/深度/平面を計算し、比較パネルをffmpegへ書く。1/2Hz標本を8Hz出力に繰り返す表示で、世界地図の逐次更新ではない。読んだ3スクリプトと`patrol/`, `slam/src/`, `scripts/orb_slam3/`の対象コード検索ではobject_map観測をAtlas/巡回へ直接登録・利用する接続は確認されない。 | `render_review_video.py:16–32,189–253`、`extract_objects.py:2–5,258–275`。既報`agent_reports/20261006_object_map/005_summary.md`は姿勢や世界地図未作成を記載する過去記録。既報の速度/件数/精度比較を今回の測定値にしない。 |
| 8 | DA3公式技術報告の題名/著者をPDF1頁で確認し、PDF3頁図1と導入、4頁の画像対応depth/ray説明を本文実読、3頁を画像実読。図は任意画像数からのdepth/ray/geometryというモデル全体の能力を示し、現行のdepth単独使用より広い。ORB-SLAM3 PDF6頁§IVも本文/画像再読。モデル図を現行object_mapの統合済み出力図にしない。 | [DA3公式PDF](https://depth-anything-3.github.io/assets/da3_tech_report_2025.pdf)（Linほか、2025、32頁）、[ORB-SLAM3 PDF](https://arxiv.org/pdf/2007.11898v2)。キャッシュは下記。 |

最小整理式（論文原式の転載ではなく、現行コードの演算）：有効画素集合をV、深度をz_p>0、許容相対差をτ=.15とし、log zの最大値−最小値≤log((1+τ)/(1−τ))を満たす最大個数窓Sを選ぶ。`a=|S|/|V|`、`z*=exp(median{log z_p:p∈S})`。Vが空なら比0/代表無し。aとτは無次元、zとz*はモデル相対単位。例として内側面積条件を満たし、有効1000画素中600画素が最大窓に入ればa=.6で採用されるが、クラス正解かはこの計算から分からない。

逆投影は `Xc=z[(u−cx)/fx,(v−cy)/fy,1]^T`、平面は `n^T Xc+d=0`、距離は `|n^T Xc+d|`（||n||=1）。u,v,cx,cy,fx,fyは画素単位、Xc,z,dは同じ相対単位、nは無次元。画像右をx、下をy、前方をzとするピンホール近似で、zを光軸深度として使う。固定upはカメラ上方向の仮定であり、世界の上方向ではない。外部姿勢が無いためXcを世界点に変換していない。歪み未補正と近似Kによる幾何誤差は未測定。

PDFキャッシュ：`sources/DA3_tech_report_2025.pdf`、同`.txt`、`DA3_tech_report_2025_page-03.png`。既存`ORB_SLAM3_2007.11898v2_page-06.png`も再読。初回web公式PDFはInternal Error、arXivは20,403,091 bytesのサイズ制限、通常shellはDNS失敗だったが、許可済み論文取得を権限付きshellで行うと公式PDF取得成功。取得障害は解消。

未確認：モデル/ライブラリの実インストール版、重み内容、個別動画の推論結果、分類正答率、深度・平面の真値誤差、画像間尺度、実機/巡回の有効性。QuadricSLAM等の原論文全算法・optimizerの再現は今回の範囲外。`object_map/README.md`は存在しない。
