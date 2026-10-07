# A15 現在地図への再局在化：根拠メモ

2026-10-07確認。純単眼・通常SLAM、現在地図の座標系に対する姿勢推定を対象とする。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。行番号は `third_party/ORB_SLAM3/src/` 内。対象Tracking/MLPnPsolver/ORBmatcher/Optimizerに固定版との差分なし。

|段階|確認結果|コード根拠|
|---|---|---|
|候補検索|現在FrameをBoW化し、DBへ現在地図を渡して候補KFを取得。地図限定の戻り候補はA14参照。BoWの類似候補取得だけでは姿勢成立を確定しない。|Tracking.cc:3613–3617；KeyFrameDatabase.cc:834–835|
|2D–3D対応|候補KFとのSearchByBoWは、KFの既存MapPoint参照と現在Frameの特徴を対応付ける。solverは非bad対応について、現在の歪み補正済み画素 `mvKeysUn` とMapPointの `GetWorldPos()` を受け取る。二画像から点自体を復元するA06とは入力が異なる。|Tracking.cc:3643–3656；ORBmatcher.cc:223以降；MLPnPsolver.cpp:65–89|
|実際のsolver|型は `MLPnPsolver`。正式名称は “MLPnP - A Real-Time Maximum Likelihood Solution to the Perspective-n-Point Problem”（Urban, Leitloff, Hinz、2016）。現行呼出しは6点標本を指定する。旧論文EPnPや残存P4Pコメントを実装名として使わない。|Tracking.cc:3630、3656–3657；MLPnPsolver.cpp:20–22、123–140；下記著者論文登録|
|標本から姿勢仮説|対応のインデックスを無作為に選び、選択済みを候補リストから除く6対応でcomputePose。全対応へ仮説を再投影し、画素残差二乗と特徴尺度に応じる許容値を比較する。現行computePose呼出しは共分散情報なしであり、MLという名から観測共分散を常用と断言しない。|MLPnPsolver.cpp:120–149、257–283|
|反復に関する限定|Trackingは `iterate(5,...)` を呼ぶが、内部whileは `mnIterations<mRansacMaxIts || nCurrentIterations<nIterations`。厳密な5回上限ではない。設定時に対応数から最小整合数・epsilon・反復上限を再計算するため、呼出し値300を固定実行回数とも書かない。内部修正・実行検証はしない。|Tracking.cc:3681–3689；MLPnPsolver.cpp:100–118、225–259|
|姿勢だけの最適化|仮説Tcwを現在Frameへ設定し、RANSACのinlier対応をFrameに反映後、PoseOptimizationへ渡す。単眼の姿勢頂点が変数、世界点座標はエッジに固定値として渡される。地図点も同時に作り直すBAではない。|Tracking.cc:3692–3721；Optimizer.cc:829–834、861–887；A09参照|
|必要時の対応追加|候補KFの未使用MapPointを仮説姿勢で現在画像へ投影し、近傍の特徴記述子と照合。条件付きで再最適化、さらに狭い探索と再最適化へ進む。投影された場所だけで対応を自動確定する処理ではない。最終受理の数値条件はA16へ。|Tracking.cc:3723–3751；ORBmatcher.cc:1889–1969|

## 式と記号（コードからの整理）

対応集合 `C={(X_i^w,u_i)}` に対して `u_i≈π(R_cw X_i^w+t_cw)`。`X_i^w∈R³` は既存地図の世界点、`u_i∈R²` は現在画像の歪み補正済み画素観測、`R_cw∈SO(3)` は世界→カメラ回転、`t_cw∈R³` は同変換の並進、`T_cw=[R_cw,t_cw]∈SE(3)`、πは校正済みカメラの射影である。Xとtは現在の単眼地図の任意尺度を共有し、回転は無次元、uと射影結果はpixel単位。

RANSACは標本 `S⊂C, |S|=6` から姿勢仮説Tを求め、全対応の `e_i(T)=u_i−π(TX_i^w)` と整合集合 `I(T)={i : e_i(T)^T e_i(T)<ε_i}` を評価する。残差eは2次元pixel、εはpixel²で、コードは特徴ピラミッド尺度の分散値×設定係数を使う。これらはPnPと現行CheckInliersを説明する整理式で、MLPnP論文の式番号付き転載でもsolver全導出でもない。仮説生成と最終復帰受理は別段階。

## 一次資料・PDF実読

- [公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)、[公式固定MLPnPsolver.cpp](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/MLPnPsolver.cpp)：型・引数・呼出し順をネット一次本文で確認。
- [MLPnP著者論文のarXiv登録・要旨](https://arxiv.org/abs/1607.08112)：題名、著者、PnPの最尤解という名称、3D方向ベクトルを扱う概要を確認。新PDFは取得しておらず、同論文内部式・図の実読を行ったとは主張しない。一般法の共分散利用能力とORB-SLAM3の現行呼出しを区別する。
- [ORB-SLAM原論文 v2](https://arxiv.org/pdf/1502.00956v2)：PDF8頁＝誌面7頁、V.C “Initial Pose Estimation via Global Relocalization” を本文とページ画像で再読。BoW候補、候補別RANSAC/PnP、姿勢最適化、投影誘導による追加対応、再最適化の順を確認。参照[41]はEPnP（参考文献本文も照合）だが、現行solverの名称は上記コードを優先する。
- 既存キャッシュ：`sources/ORB_SLAM_1502.00956v2.pdf`、同 `.txt`、`sources/ORB_SLAM_1502.00956v2_page-08.png`。

未確認・範囲：実データでのRANSAC回数、復帰精度・頻度は未測定。A16最終受理条件の詳細、MLPnP全導出は展開していない。コード実行・変更なし、取得障害なし。
