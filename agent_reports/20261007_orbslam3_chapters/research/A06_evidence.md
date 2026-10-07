# A06 根拠メモ：二視点からの初期地図作成

2026-10-07。対象は純単眼・PinholeのA06のみ。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下のパスは`third_party/ORB_SLAM3/src/`基準。表の対象ソースにHEADとの差分なし。

| 根拠箇所 | 確認した方法・注意点 |
| --- | --- |
| Tracking.cc:2448–2504、ORBmatcher.cc:648–718 | 最初の候補Frameを保持し、後のFrameとSearchForInitializationでORB記述子対応を求める。対応探索は補正後mvKeysUnの最細段を対象とし、再構成にも両FrameのmvKeysUnを渡す。候補は必ずしも動画の第0画像とは限らない。成立個数閾値の詳説はA07。 |
| CameraModels/Pinhole.cpp:83–90、TwoViewReconstruction.cc:78–127 | Kを使うTwoViewReconstructionへ委譲。同じ8対応の標本集合からH/Fを並列推定し得点比較。SH+SF==0ならfalse。RH=SH/(SH+SF)>0.50でH、その他F。コメントの0.40は現行分岐ではない。 |
| TwoViewReconstruction.cc:475–503,571–608,700–707 | FからE21=K^T F21 Kを作り4組のR,t候補。Hからは8候補を構成。各候補をCheckRTで三角測量・検証する。選択したモデルの復元結果を直接returnし、失敗時に他モデルへ自動切替する構造ではない。 |
| 同:802–855、GeometricTools.cc:47–65 | P1=K[I\|0]、P2=K[R\|t]、第2カメラ中心O2=-R^Tt。対応画素から4行の線形同次系を作りSVD、最後の同次成分で除算。得られるp3dC1は第1カメラ座標。 |
| TwoViewReconstruction.cc:835–887、Tracking.cc:2506–2512 | nGoodは有限性・条件付き深度・再投影検査を通った計数。vbGoodはさらに視差条件を満たす点だけtrue。低視差点もnGoodに含まれ得るため両者は同じでない。TrackingはvbTriangulated=falseの対応を外してから地図化する。 |
| Tracking.cc:2515–2567、Frame.cc:431–436,472–478 | 初期Frame姿勢をSE3単位元、現在FrameをTcwに設定。初期2 KeyFrameを作り、mvIniP3Dの座標をworldPosとしてMapPoint化、両KeyFrameの観測を登録する。Tcwは世界→カメラ、Twcはその逆。 |
| Tracking.cc:2578–2582、Optimizer.cc:52–56,116–125,160–184 | 初期点群と2姿勢を用意してからGlobalBundleAdjustemnt(map,20)。初期KeyFrame姿勢を固定し、観測の再投影誤差を最適化。観測はmvKeysUn、段ごとの逆分散で重み付け、既定値ではHuber損失を使用（include/Optimizer.h:53–54）。 |
| Tracking.cc:2582–2609,2627,2656、KeyFrame.cc:774–806 | BA後に初期KeyFrame座標で深度を計算・整列し、添字(n−1)/2の値を取得。純単眼ではその逆数を第2姿勢のtranslationと地図点へ掛ける。検査通過後の地図参照等の設定を経てmState=OK。偶数点では中央2値の平均ではなく下側の値。メートル尺度を測った処理ではない。 |
| TwoViewReconstruction.cc:695–730（固定公式rawも同じ） | **H経路の静的な不整合**：bestP3Dへ候補点を保存するが、成功ブロックはT21/vbTriangulatedだけを出力し、vP3Dへの代入がない。F経路:530–563には点群代入がある。Tracking:2550はmvIniP3D[i]を読むため、H経路が正常な点群を返すと断定しない。実際の失敗形態は未実行。 |
| ORB-SLAM原論文PDF6–7頁（紙面5–6）§IV、式(1)–(4)、図3 | 本文とページ画像を実読。H/Fの同時推定→候補運動と構造→初期BAという方法を確認。式(3)直後のH選択は>0.45で現行>0.50と異なる。原論文はH用4標本と書くが、現行FindHomographyは8標本を使う（:156–177）。図3は低視差時に初期化を待つ意義を示す例。 |

教材式・座標の最小要点（特記以外はコード由来の整理）：

- `Xc=Rcw Xw+tcw`、`Cw=-Rcw^T tcw`。Rは3×3回転、X/t/Cは3成分、同じ任意の長さ単位。初期世界は最初のKeyFrameのカメラ座標。カメラはx右、y下、z前方（Pinhole.cpp:30–32,61–68の正焦点距離での投影からの読み取り）。画像u,vは画素で右・下が正。
- `π(Xc)=(fx Xc/Zc+cx, fy Yc/Zc+cy)`、Zc≠0。fx,fy,cx,cyはpx。補正後画素の同次表現x=(u,v,1)^Tに対し`x2~H21 x1`、`x2^T F21 x1=0`。H/Fは3×3、~は非零倍率までの一致。論文式(1)のH側の等号は同次尺度を含むものとして説明する。
- 三角測量は`xj×(Pj Xh)=0`から独立2行ずつを使う4×4系。Xhは4成分同次座標。画像対応と姿勢候補から深度を得るが、基線がない純回転では深度を一意に定められない（幾何からの推論）。小視差も不安定であり、特徴点数だけでは解決しない。
- 初期BAの整理は`min Σ_(j,i) ρ((u_ji−π(R_j X_i+t_j))^T Ω_ji (u_ji−π(R_j X_i+t_j)))`。jは2つのKeyFrame、iは採用点、観測集合上の和。uは補正済2画素座標、Ωは2×2逆共分散、ρはHuber。初期姿勢を固定しても単眼尺度は任意。論文の式番号は付けない。
- `d=sorted(depth)[(n−1)/2]`、`s=1/d`、`t2←s t2`、`Xi←s Xi`。d>0での正規化として説明し、地図と並進を共に拡縮するので投影は変わらない。コードはゼロ中央値を明示的には除外していないため、数値安全性を保証する説明は避ける。

オンライン一次ソース：[公式固定コミットTwoViewReconstruction.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/TwoViewReconstruction.cc)。モデル選択とH出力箇所を本文実読。Web正規化行はローカル行と異なる。

新規PDF：[ORB-SLAM: a Versatile and Accurate Monocular SLAM System](https://arxiv.org/pdf/1502.00956v2)、Raúl Mur-Artal／J. M. M. Montiel／Juan D. Tardós、arXiv v2（2015-09-18）、TRO採録著者版、18頁。ローカル`../sources/ORB_SLAM_1502.00956v2.pdf`（4,202,706 bytes）、同名txt、`ORB_SLAM_1502.00956v2_page-06.png`／`page-07.png`。PDF SHA-256：`442bcef21b04c007628c452e21b3122296e76fee727b1fc766e7d2b666ec3634`。

未確認：実動画でのH/F選択・初期化成否・H出力不整合の発現は未検証。A07の成立閾値の体系化、一般BA理論、後続追跡は対象外。取得障害なし。コード変更・実行・ビルドは行っていない。
