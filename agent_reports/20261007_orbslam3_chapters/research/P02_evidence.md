# P02 根拠メモ：LocalMappingと非同期キュー

純 MONOCULAR・通常 SLAM に限定。manifest は `D09,D10 → D11,D09 → P03`。ORB-SLAM3 固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`、外側 HEAD `d1265bc35439dd6ca57687ac93c8b3a7310fc681`。行番号は `third_party/ORB_SLAM3/` 以下のローカル現行ファイル。

| 確認事項 | 根拠と現行の限定 |
|---|---|
| Run の順序・受付と中断 | `src/LocalMapping.cc:64–281`：受付 false → キューがあり badIMU でなければ受取/点選別/新点生成 → キュー空なら近傍融合 → キュー空かつ停止要求なしなら条件付き BA と KF 選別 → LoopClosing へ渡す → reset 確認 → 受付 true → finish 確認。BA はさらに `KeyFramesInMap()>2`、純単眼は154行の `LocalBundleAdjustment`。KF 選別191行はこの >2 条件の外。`InsertKeyFrame:284–288` は mutex 下の push と abort=true、`RequestStop:825–830` は停止要求と abort=true、`InterruptBA:897–900` は abort=true。103行で abort=false に戻す箇所もある。`AcceptKeyFrames:873–882` は専用フラグであり、キュー空/全処理完了の証明ではない。 |
| KeyFrame 受取と地図への追加 | `LocalMapping.cc:298–337`：キュー mutex 下で先頭を pop → ComputeBoW → 未登録の既存 MapPoint 観測を追加し代表記述子/観測方向等を更新 → UpdateConnections → Atlas::AddKeyFrame。これは Tracking のキュー挿入後にこのワーカーが行う処理。旧論文§VI-Aの列挙順を現行コードの順として転記しない。 |
| 最近追加された点の選別 | `346–384` は recent リストを検査。bad 点、追跡での発見率が低い点、作成 KF ID からの差と観測数条件で不適当な点は bad 化してリストから除く。一方、377–378行の経過条件は recent リストから除くだけで、点を bad 化しない。全 MapPoint を毎回一律に削除判定する関数ではない。 |
| 既存地図への新点追加 | `388–466` は共視近傍 KF、既存姿勢、基線、対応探索を利用し、`558–585` で視差確認と三角測量、`612–691` で両カメラ前方・再投影・尺度等を検査、`694–709` で MapPoint と2観測を登録。`436–437` は最初の近傍後、新 KF が来ていれば早期 return。A06 の H/F 選択から初期姿勢・地図を作る手順と異なり、既存地図の KF 姿勢を用いる。 |
| 隣接融合 | Run105–108の呼出し条件はキュー空。`714–822` は共視近傍と一部の二段近傍を対象に、現在点→近傍、近傍点→現在 KF の投影対応による Fuse を呼び、記述子等と共視接続を更新。`744–745` の近傍拡張打切り、`777–778` の後半前 return があり、abort 時に必ず全段階完了とはならない。P03 の地図間統合とは区別。 |
| 局所 BA の変数と固定対象 | 実呼出しは `src/Optimizer.cc:1116` の overload。`1121–1160` は現在 KF と同じ Map の有効な共視 KF、およびそこで見える有効点を集める。`1162–1179` はそれらの点を見る局所集合外 KF を固定対象にし、`1220` は Map の初期 KF を局所集合内でも固定する。固定 KF が0なら `1182–1185` で return。`1212–1238` の姿勢頂点と `1282–1290` の点頂点を使い、局所の自由な姿勢と点を同時に調整する。A09 の姿勢のみ・点固定、A06 の初期地図 BA と区別。 |
| 残差・最適化・結果反映 | `Optimizer.cc:1304–1325` は単眼2次元観測、octave 別逆分散×単位行列の重み、Huber を設定。残差は `include/OptimizableTypes.h:99–109` の観測−投影と正深度判定。`1203–1204` は停止フラグ登録、`1406–1408` は実行前 true なら return、`1410–1411` は optimize(10) 一回。g2o `core/sparse_optimizer.cpp:376` / `.h:188` は反復中も停止フラグを検査。戻った後は単眼の χ²>5.991 または非正深度を観測削除候補にし（1416–1429）、Map mutex 下で双方の観測対応を erase、姿勢と点を書戻す（1463–1497）。最適化中の中断後もここへ進み得るため、全結果破棄/常に10反復完了/収束済みとはしない。この overload に二段目や Huber 解除はない。 |
| 冗長 KF 選別と後段への受渡し | `LocalMapping.cc:902–1047` は共視 KF を検査し、初期 KF/bad KF を除外。純単眼の現行判定は他 KF の `scaleLeveli<=scaleLevel+1` を数え、`thObs=3` に対して `nObs>thObs`、すなわち他4 KF以上でその点を冗長と数える。冗長点数が `0.9*nMPs` より大きければ SetBadFlag。旧論文/コメントの他3 KF・同等か細かい尺度とは相違。Run250行は BA/KF 選別が省略された場合にも LoopClosing::InsertKeyFrame を呼ぶ。境界先の `src/LoopClosing.cc:311–315` は queue mutex 下で ID!=0 の KF を push するのみ。P03処理完了ではない。 |

## 最小 BA 式の出典と記号

[旧 ORB-SLAM 論文 v2](https://arxiv.org/pdf/1502.00956v2) の PDF16頁（誌面15頁）Appendix、式(5)–(7)を本文・画像で確認。以下は局所集合を明示した整理式であり、論文式のそのままの転載ではない。

\[
\min_{\{T_{iw}:i\in\mathcal L\setminus\mathcal F\},\{X_{w,j}:j\in\mathcal P\}}
\sum_{(i,j)\in\mathcal E}\rho_H(e_{ij}^{\mathsf T}W_{ij}e_{ij}),
\qquad e_{ij}=u_{ij}-\pi_i(R_{iw}X_{w,j}+t_{iw}).
\]

`L` は現在/共視の局所 KF 集合、`P` はその局所点集合、`F` は局所外の観測 KF と、集合内に存在する初期 KF の固定集合。`E` はこれら KF と局所点の有効な観測対応。`Tiw=(Riw,tiw)∈SE(3)` は地図世界座標 w→カメラ i、`Xw,j∈R³` は点の世界位置、並進と点位置は同じ単眼地図の任意尺度。回転 R は3×3、並進 t は3成分。`uij,eij∈R²` は画像上の観測と誤差（pixel）、π は固定カメラモデルの3D→画像投影。現行 PinHole の観測は `mvKeysUn`。`Wij=σij⁻²I₂` は2×2の逆共分散重み（pixel⁻²）、ρH は Huber 損失。論文の Ω は共分散で、重みは Ω⁻¹。カメラ校正はここでの変数ではなく、固定 KF の存在だけからメートル尺度が得られるとはしない。

## 一次資料と相違・限界

- [公式固定 LocalMapping.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/LocalMapping.cc) と [公式固定 Optimizer.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Optimizer.cc) の Run、呼出す overload、固定 KF、optimize(10) をオンライン照合。
- 旧論文 PDF8–9頁（誌面7–8頁）§VI-A〜E、PDF16頁 Appendix の本文・画像を再読。§VI-D は途中と最後の外れ値除去を記すが、現行の当該 overload は表の一段の処理。KF 選別の差も上表の通り。論文の算法説明と現行実装条件を分離する。
- キャッシュ `sources/ORB_SLAM_1502.00956v2.pdf`、同名 `.txt`、`_page-08.png`、`_page-09.png`、`_page-16.png` を利用。9頁画像は既存 PDF から今回描画した。新 PDF の取得なし。
- 実行・性能・中断タイミングの再現は未実施。全しきい値/IMU 分岐の網羅、P03算法の調査は行っていない。取得障害なし。
