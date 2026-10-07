# A10 根拠メモ：局所地図を使う姿勢確認

2026-10-07。純単眼・通常SLAMのTrackLocalMapのみ。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。パスは`third_party/ORB_SLAM3/src/`基準。Tracking/Frame/ORBmatcher/MapPointにHEADとの差分なし。

| 根拠 | 確認内容 |
| --- | --- |
| Tracking.cc:2949–2971,3417–3424 | 入口は推定姿勢と既存の対応。UpdateLocalMap（UpdateLocalKeyFrames→UpdateLocalPoints）→SearchLocalPoints→純単眼のPoseOptimization。対象候補を局所地図へ広げて現在姿勢を再評価する流れであり、この呼出しで新しい3D点を三角測量して増やす処理ではない。 |
| Tracking.cc:3457–3477,3507–3528,3602–3605 | 現在Frameの非null・非bad MapPointから観測KeyFrameへ投票。得票がある非bad KeyFrameを種にし、最大得票のものを参照KeyFrameへ。ここでmvbOutlierを直接検査する条件はなく、「現在のインライアだけから必ず作る」と言い換えない。 |
| Tracking.cc:3531–3582 | 種KeyFrameの共有観測近傍・木の子／親の一部を追加。現在Frame IDの印で重複を避ける。共有観測上位候補を全部追加するわけではなく、追加後breakがある。size>80は拡張ループを打ち切る条件で、局所集合が常に80以下という保証ではない。空間的な距離球で選ぶ処理ではない。 |
| Tracking.cc:3427–3451 | 選ばれたKeyFrameのMapPointを集め、null・badを除き、mnTrackReferenceForFrameで重複除外する。複数KeyFrameが同じ点を観測していても局所点候補は一度だけ追加される。 |
| Tracking.cc:3343–3384、Frame.cc:512–573、MapPoint.cc:462–492,502–545 | 既対応点を再検索対象から外し、局所点の候補にisInFrustum(p,0.5)。負深度・画像外・点の距離許容範囲外・観測方向不整合を除き、投影座標と予測段を保存する。距離はカメラ中心からの3D距離。平均観測方向はnormal/nで必ずしも単位ベクトルではなく、現行viewCos条件を厳密な60度だけの判定と断言しない。遮蔽完全検出・零深度安全性も保証しない。 |
| Tracking.cc:3388–3413、ORBmatcher.cc:43–129 | 候補があれば局所MapPoint版SearchByProjection。予測投影位置・尺度に応じた近傍の特徴点から記述子距離で選ぶ。既に登録観測付きMapPointと結ばれた特徴はスキップ。最良／次善が同じ段の場合の比率検査もある。可視候補になったことと、記述子対応が成立したことは別。 |
| Tracking.cc:2969–2971、Optimizer.cc:828–834,871–889,1106–1111 | A09と同じPoseOptimizationを呼び、現在Frame姿勢だけを可変にし地図点座標を定数として使う。位置と点を一緒に調整するLocal Mapping側のLocal BAと混同しない。外れ値分類・Huberの反復扱いはA09参照。 |
| ORB-SLAM v2、PDF8頁＝紙面7、V.D | 本文とページ画像を実読。共有点のあるK1＋covisibility近傍K2から局所地図を作り、投影・方向・距離・尺度・記述子照合の後に姿勢を最適化する説明を確認。現行の木による追加、重複印、拡張停止、PredictScaleの対数・丸め処理は上のコード根拠と分ける。V.Dに番号付き式や図はない。 |

集合の教材整理（論文の原式ではない）：

`I={i | 現在Frameのp_iが非null・非bad}`、`Obs(p)={pを登録観測するKeyFrame}`として、`c(K)=Σ_(i∈I) 1[K∈Obs(p_i)]`、`K_seed={K | c(K)>0かつ非bad}`。cは投票数、iは現在画像の特徴スロット、1[条件]は0/1。`K_local=K_seed∪K_add`のK_addは上表の選択的な共有観測／木の拡張であり、全近傍を無条件に足す集合ではない。

`P_local=∪_(K∈K_local) Points(K)`からnull・badを除き重複をなくす。Points(K)はKに対応付けられた地図点集合。各集合の要素はKeyFrameやMapPointの識別子で、画素座標やメートルの集合ではない。局所点の各3D位置を現在のTcwでカメラ座標へ変換して投影する。3D距離は単眼の任意長さ単位、投影位置と画像探索窓はpx、段番号は整数。現在姿勢はA09/A15から受け取る推定なので、投影候補の判定自体もその誤差に影響される。

一次ネット：[公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)。SearchLocalPoints・局所集合構築の該当本文を照合。Webの正規化行番号はローカル行と異なる。

PDF：[ORB-SLAM原論文v2](https://arxiv.org/pdf/1502.00956v2)。既存`../sources/ORB_SLAM_1502.00956v2.pdf`とtxtを再利用。新しく`ORB_SLAM_1502.00956v2_page-08.png`を保存して画像実読。版・PDF SHAはA06を参照。

未確認・範囲：実動画の局所点数・可視性・照合精度は未測定。候補追加により実対応数が必ず増える保証はしない。成立閾値はA11へ残し、後章の内部は未調査。コード変更・実行・新PDF取得なし。取得障害なし。
