# O01 根拠メモ：結果の表示と画像再投影

対象は現行 `slam/viewer/view.py` と `slam/rviz/play_map.py`。以下の行番号は workspace 内の現行ファイル。D03/D08/D14/D15 の座標・保存仕様を再利用。起動・動画読込・出力作成・改修はしていない。

| 論点 | 現行コードと限定 |
|---|---|
| 実入口と表示モード | 概要文書213行の viewer/RViz 接続、root `README.md:473–497`、`scripts/orb_slam3/view.sh` と `show_rviz.sh` を照合。前者は view.py へ video/points と追加引数を渡す。`view.py:545–585` は通常 Player、--save 並列表示動画、--overlay 重ね動画、--check/--dump の分岐。overlay は入力動画の隣に `stem_div_XXX.mp4` を自動命名し、--overlay の文字列を出力先には使わない。後者は rviz2 設定を開き play_map.py へ points/poses/divisor を渡す。 |
| 読込データと校正 | viewer `48–55,272–277` は点4列、姿勢9列を検査。`10–12,237–258` は現行 mini3.yaml の Camera1.* から K と `[k1,k2,p1,p2,k3]` を読み、グローバル初期化なので通常 viewer 起動にも校正ファイルが必要。overlay は D15 の Tcw と valid を使用。RViz `205–219` は点/姿勢を np.loadtxt し、動画や校正 YAML を使わない。二保存の同一 Map と校正/画像寸法の整合を表示側が保証するわけではない。 |
| 箱の生成差 | viewer `58–74` と RViz `71–85` は全点 bbox 対角長/divisor を箱幅とし、各セルの最早時刻を採る。viewer の位置は `(floor(X/h)+0.5)h` のセル中心。RViz の位置はそのセルで最早時刻を持つ**実点**。同じ箱位置と断定しない。bbox対角長が微小なら h=1。箱は点をまとめる描画表現で、壁面・占有確率・障害物体積を推定した結果ではない。 |
| 仮想3D表示と実画像投影 | viewer `77–108,133–155` の左表示は orbit 視点と仮想焦点距離520の投影。`306–350` の overlay は別経路で、poseからRcw/tcwを作り箱頂点をカメラ座標へ変換し、rvec/tvec=0 と実校正 K/DIST で cv2.projectPoints を呼ぶ。既にTcwを適用済みなので二重に外部姿勢を掛けない。奥行き・面・投影画素等の表示用選別もあり、時間条件を満たした全箱が必ず描かれるわけではない。 |
| overlay の時刻照合 | viewer `194–195,353–360,363–389`：姿勢時刻 round(t,5) の辞書へ登録。重複キーは原則先行保持だが先行valid<0.5からvalid>=0.5への置換あり。画像 index/fps を同じ丸めで検索し、姿勢の補間なし。箱時刻<=index/fpsの箱だけを候補とする。poseなし/valid<0.5では箱を重ねない。fps読込は `get(...) or 30.0` で wrapper の `<1` 規則と同一コードではない。 |
| RViz の開始座標系 | play_map `64–101` は valid>=0.5 行を抽出し、最初の行の R0/C0 を用いる。点位置 R0(X−C0)、軌跡 R0(C−C0)、カメラ回転 R0 Rcw^T。表示 frame 名は map だが初回カメラ座標へ揃える処理で、ENU/重力方向への整列やメートル換算ではない。valid行なしなら停止。 |
| ROS形式と再生 | play_map `122–141,156–202,219`：Marker CUBE_LIST の points/scale、Path の PoseStamped 配列、map→camera のTFを発行。30Hz timerごとにvalid履歴行を1件進め、末尾では同じ行を再発行。点時刻<=現在行時刻で箱を出す。ROS stamp は `get_clock().now()` で、Path内各poseもその発行時刻。元時刻の gap に従って実時間再生する方式ではない。 |
| 可視化・check の限界 | viewer `198–234` のcheckは右パネルと動画の一致、箱数、yaw変更による表示差などで、地図の真値精度検証ではない。通常Playerは `448–475,494–528` の経過時計とfpsから表示画像を選ぶ。各表示は保存座標・時刻の利用であり、SLAM再推定・再校正ではない。D14/D15 の任意尺度、validや時刻の限定、snapshot未保証はそのまま残る。 |

## 最小座標式と時刻例

有限点と正の divisor d、非微小bbox対角長の通常例では、`h=||Xmax−Xmin||/d`。X は保存地図座標、max/min は成分別、h は同じ任意長さ単位、d は無次元。viewer のセル番号 n=floor(X/h) は整数3成分、箱中心は h(n+1/2)。RViz は同じセルの最早時刻の実点を中心として使う。

overlay の箱頂点 Xw に対し、

\[
X_c=R_{cw}X_w+t_{cw}=(x_c,y_c,z_c)^T,\quad
(a,b)=(x_c/z_c,y_c/z_c),\quad
(u,v)=(f_x D_x(a,b)+c_x,\ f_y D_y(a,b)+c_y).
\]

Rcw は世界→カメラ回転、tcw は同じ向きの並進。X/t/h は任意長さ単位、a/b と歪み関数 D は無次元、u/v・焦点距離 fx/fy・主点 cx/cy は画素単位。Dは現在の5係数による歪み（D03参照）。前方の頂点と適切な同一校正/画像寸法・点と姿勢の共通座標が前提。実装は原画像へ重ねるので、補正済み画素だけの理想 pinhole 式で DIST を落とさない。

RViz はカメラ中心 C=−Rcw^T tcw を使い、`Xdisplay=R0(Xw−C0)`、`Cdisplay=R0(C−C0)`、`Rdisplay=R0 Rcw^T`。0は最初のvalid行で、その位置が原点になる。回転は無次元で、長さの実尺度を追加決定しない。

時刻の仮定例：fps=30、画像index=3なら0.1秒、辞書キーは0.10000。箱時刻0.08秒は候補、0.15秒はまだ候補外。対応poseキーがなければ前後poseを補間しない。RVizの隣り合うvalid行が0.1秒と0.3秒でも、通常は次の1/30秒timerで次行へ進むため、0.2秒の欠落区間をそのまま待つわけではない。実再生結果を測った例ではない。

## 公式一次資料・PDF実読

- [OpenCV projectPoints](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html)：3D点・外部姿勢・K・歪みから画素へ投影するAPI、およびrvec/tvec=0の部分適用を確認。4.x URLは4.13.0へ転送された。実環境のOpenCV版は実行確認していない。
- ROS 2 Jazzy公式 [Marker.msg](https://raw.githubusercontent.com/ros2/common_interfaces/jazzy/visualization_msgs/msg/Marker.msg)、[Path.msg](https://raw.githubusercontent.com/ros2/common_interfaces/jazzy/nav_msgs/msg/Path.msg) を実読。Markerのheader/frame、型、姿勢、scale、points/colorsと、Pathのheader/PoseStamped配列を確認。形式名から座標のENU整列や軌跡時刻の再現を補って解釈しない。
- [ORB-SLAM3 v2](https://arxiv.org/pdf/2007.11898v2) PDF6頁 §IV の本文と `sources/ORB_SLAM3_2007.11898v2_page-06.png` を再読。投影/逆投影を担うカメラモデルの背景で、ローカルviewerの箱化・時刻照合・ROS再生仕様はコード根拠。
- 取得障害なし。表示/動画処理/ROS起動・実出力・精度評価は未実施。全描画閾値の網羅、O02/O03/O04は対象外。
