# A09 根拠メモ：姿勢の予測と照合

2026-10-07。純単眼・通常SLAM、初期化後のOK入口が対象。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。下表のパスは`third_party/ORB_SLAM3/src/`基準。Tracking/ORBmatcher/OptimizerにHEADとの差分なし。

| 根拠 | 確認内容 |
| --- | --- |
| Tracking.cc:1939–1955 | CheckReplacedInLastFrame後、運動モデルが使えない場合等はTrackReferenceKeyFrame、それ以外はTrackWithMotionModel。運動モデル経路がfalseなら参照KeyFrame経路へフォールバック。参照経路の失敗から運動モデルへ逆に切替する構造ではない。 |
| Tracking.cc:2702–2716,2781–2789,2300–2306 | CheckReplacedInLastFrameは前FrameのMapPoint参照を置換先へ更新。運動モデル経路内のUpdateLastFrameは保存した参照KeyFrameとの相対姿勢Tlrと現在の参照姿勢から前Frame姿勢を更新する。純単眼はその後returnし、一時VO点を生成しない。 |
| Tracking.cc:2205–2215,2858–2871 | 更新は`bOK || mState==RECENTLY_LOST`かつ両Frame姿勢設定済みの場合。`mVelocity=Tcw*LastTwc`、適用は`mVelocity*mLastFrame.GetPose()`。更新を成功時だけとは書かない。両箇所にtimestamp差の除算・間隔比補正はない。 |
| Tracking.cc:2720–2778 | 参照KeyFrame経路はComputeBoW→SearchByBoWで対応取得、前Frame姿勢を初期値にPoseOptimization、外れ対応除去。コメントの「PnP solver」ではなく実呼出しを根拠とする。ここは既存3D点と現在2D特徴の対応であり、新しい地図点を作る二視点初期化ではない。 |
| Tracking.cc:2876–2909、ORBmatcher.cc:1676–1789 | 前Frameで観測した非外れMapPointを予測姿勢で現在画像へ投影。画像内・段別探索窓でORB記述子距離を比較し、方向整合性も扱う。候補不足では窓を2倍にして再探索し、足りなければfalse。対応を得てからPoseOptimization。全画像特徴の無制限総当たりではない。 |
| Optimizer.cc:828–834,863–889,1106–1111 | 最適化頂点は現在FrameのSE3姿勢1個。単眼辺は補正後mvKeysUnを観測、MapPoint座標を辺のXwへ定数コピー。地図点を変数として一緒に動かすA06初期BAと区別。最適化姿勢をFrameへ戻す。 |
| Optimizer.cc:879–884,999–1041,1102–1103 | 段ごとの逆分散重みと初期Huber。各最適化後に外れ値を再分類し、除外点が再び採用され得る。it==2の判定後にrobust kernelを解除。したがって全反復で固定したHuber目的を最小化するとは断言しない。 |
| 論文V.B／Appendix | PDF7頁＝紙面6のV.Bは運動モデル→前画像で観測した点の誘導探索→不足時探索拡大→姿勢最適化を説明。PDF16頁＝紙面15のAppendix式(5)–(7)と末尾は再投影誤差・段依存共分散・motion-onlyでは全点固定／姿勢だけ可変を記載。両頁を本文と画像で実読。 |

式・記号の根拠（予測式はコード整理、残差は論文式(5)–(7)に対応）：

- `T_ab∈SE(3)`は座標bからaへの剛体変換（4×4同次行列表現）。wは地図世界、cは現在カメラ、lは前カメラ、rは参照KeyFrame。`T_lw=T_lr T_rw`がUpdateLastFrameの順序。3Dカメラ軸は右・下・前、世界軸は初期KeyFrame由来。並進は単眼地図の任意長さ単位、回転は無次元。
- 更新する数値行列`V←T_cw(T_lw)^−1`はl→cの相対変換。次の予測では同じ数値を次区間の相対変換と近似して`T̂_cw=V T_lw`と左から掛ける。Vはm/sやrad/sの速度ではない。「ほぼ等時間間隔で同程度の運動増分が続く」はモデルを読む際の仮定で、実装が時間間隔を検査・補正している意味ではない。
- 固定3D点`X_i∈R³`、補正後観測`u_i∈R²`に対し`e_i(T)=u_i−π(RX_i+t)`。`π(X,Y,Z)=(fx X/Z+cx,fy Y/Z+cy)`、Z≠0。u/e/fx/fy/cx/cyは画素単位、画像は右・下が正。初期ロバスト段の概念式は`min_(T∈SE3) Σ_i ρ_H(e_i^T Σ_i^−1 e_i)`。Σ_iは2×2共分散（px²）、ρ_HはHuber、iは現在の対応。未知数はTのみ。式は外れ値再分類と後段Huber解除の手続き全体を一本で表したものではない。論文では共分散記号がΩなので、本文でΣを使うなら記号変更を明記する。

一次ネット：[公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)。相対変換の更新と予測積、探索拡大をWeb本文で照合。

PDF：[ORB-SLAM原論文v2](https://arxiv.org/pdf/1502.00956v2)。キャッシュ`../sources/ORB_SLAM_1502.00956v2.pdf`とtxtを再利用し、画像`ORB_SLAM_1502.00956v2_page-07.png`と新規`ORB_SLAM_1502.00956v2_page-16.png`で実読。PDF版・SHAはA06根拠に記録済み。Appendix該当部分に図はなく、式(5)–(7)のレイアウトを確認。

未確認・範囲：実動画での予測誤差・照合成功率は未測定。V.Bは旧論文の概説で、現行の参照KeyFrame fallbackや各反復制御をそのまま載せてはいない。A10の局所地図拡大・探索内部は未調査。新PDF取得・コード変更・実行なし。取得障害なし。
