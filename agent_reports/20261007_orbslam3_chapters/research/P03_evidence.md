# P03 根拠メモ：LoopClosingの補正と地図統合

純 MONOCULAR・通常 SLAM に限定。manifest は `D09,D07,D10 → D12`。ORB-SLAM3 固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`、外側 HEAD `d1265bc35439dd6ca57687ac93c8b3a7310fc681`。以下は `third_party/ORB_SLAM3/` 以下のローカル現行行番号。本文執筆・コード実行/変更は行っていない。

| 確認事項 | 現行の根拠と限定 |
|---|---|
| キューと実行入口 | `src/LoopClosing.cc:90–112,311–338` は LocalMapping からの KF キューを確認し、NewDetectCommonRegions で pop して消去抑止を設定する。`327–328` は場所認識無効なら false、`356–361` は地図が小さい場合 DB へ登録して false。入力があるだけで補正が必ず実行されるわけではない。 |
| BoW 候補と同/別地図の分類 | `LoopClosing.cc:483–512` は DetectNBestCandidates(...,3) の loop/merge 候補を別々に幾何検証へ渡す。`src/KeyFrameDatabase.cc:717–723` は同一 Map を loop、異なる非bad Map を merge 候補へ分類。`LoopClosing.cc:691–777` は Sim3Solver の RANSAC、投影対応追加、OptimizeSim3、さらに狭い投影探索という検証。BoW の類似は候補取得であり、幾何的成立や地図統合の完了ではない。 |
| 共視での検証と merge 優先 | 新規候補は `818–841` で現在 KF の共視 KF に幾何検証を行い、`870–880` で一致数を保存して >=3 を返す。`374–463` には次の入力 KF へ前候補を伝播・再検証する経路もある。旧論文の「連続3回 BoW 候補が現れる」規則とは異なる。Run は `122` の merge を先に処理し、純単眼では183行の MergeLocal。`208–217` で同時に立った loop を解除するため、その検出で二経路を常に続けて実行しない。loop の成立経路は274行の CorrectLoop。 |
| 同一地図の姿勢/点補正と融合 | CorrectLoop `975–999` は LocalMapping に停止要求、EmptyQueue、動作中 GBA への中断要求と detach、LocalMapping の isStopped 待ち。`1013–1064` は補正 Sim3 を共視 KF へ伝播し、SE3 保存姿勢では並進を scale で割る。`1068–1099` は旧姿勢で写して補正姿勢の逆で点を戻す。`1118–1140` は一致点の Replace/観測追加と SearchAndFuse。後者 `2115–2146` は投影 Fuse と Map mutex 下の Replace。単に点群配列を連結する処理ではない。 |
| 同一地図のグラフと GBA 起動 | `1142–1183` は融合後の新接続を集め、純単眼では OptimizeEssentialGraph を呼ぶ。地図点を全て同時に変数にする BA と、相対変換制約を使う姿勢グラフは区別する。`1195–1206` で loop edge を追加し、条件 `!isImuInitialized() || (KeyFramesInMap()<200 && CountMaps()==1)` なら別 thread の GBA を起動。純単眼では前半が成立するため「200 KF 未満に限る」とはしない。`1210` の LocalMapping 再開と GBA 完了は別。 |
| 別地図の統合と純単眼の伝播 | MergeLocal `1227–1261` は実行中 GBA の中断有無を記録し LocalMapping 停止を待つ。`1431–1496` で current 側の窓の姿勢/点を merge 側座標へ補正、`1506–1551` で所属を移し merge Map を current に、元 Map を bad にする。木の接続更新、SearchAndFuse は `1559–1605`。welding BA 後1639行で一度再開し、残りがあれば純単眼枝 `1647–1704` で旧地図の残りの姿勢/点へ変換を伝播、再び停止して所属を移す。`1715–1718` の後半 EssentialGraph は sensor!=MONOCULAR のみなので純単眼は通らない。最後 `1772–1778` は merge edge・変更通知・bad Map の除去。A20 の独立した空 Map 作成とは異なる。 |
| 現行 welding BA の可動/固定 | `LoopClosing.cc:1616–1627` は current 側窓を第2引数、merge 側窓を第3引数に渡す。実体 `src/Optimizer.cc:3498` の overload は `3526–3540` で第3引数の有効 KF を固定、`3562–3576` で current 側を可動、双方から集めた点を再投影観測で調整する。`3719–3772` は事前 stop で return、Huber 付き5反復を要求し、継続時に外れ値 edge を外し Huber を解除して10反復を要求する。`3825–3835` は mutex 下で外れ観測を erase。P02 の1116版一段 BA と区別。呼出し側の stop は局所変数 `bStop=false` であり、LocalMapping の mbAbortBA と同じ変数ではない。 |
| 非同期 GBA・中断・採否 | CorrectLoop `979–991`、MergeLocal `1231–1243` は stop フラグ/世代値更新と detach で、join による終了待ちではない。Merge の再起動は `1763–1769` の bRelaunchBA が追加条件で、毎回の統合で新 GBA が始まるとはしない。RunGlobalBundleAdjustment は `2281–2286` で純視覚 GBA を要求し、`2300–2329` で idx 比較・慣性状態・stop フラグを検査してから LocalMapping 停止待ちと Map mutex を取得する。採用側は木に沿う補正伝播/姿勢・点反映（`2334–2381,2453–2494`）。ただし idx の取得自体は最適化呼出し後2300行であり、世代比較の存在だけで古い結果の完全排除を保証しない。処理完了・最適化収束・スレッド終了は同義ではない。 |

## Sim3 の最小整理式と出典

\[
X_A=S_{AB}(X_B)=s_{AB}R_{AB}X_B+t_{AB},\qquad
S_{AB}^{-1}(X_A)=s_{AB}^{-1}R_{AB}^{\mathsf T}(X_A-t_{AB}).
\]

`SAB∈Sim(3)` は座標 B→A、`XA,XB∈R³` は同じ点を各座標系で表した値、`RAB∈SO(3)` は3×3回転、`tAB∈R³` は A 側の長さ単位の並進、`sAB>0` は無次元の尺度比。回転3・並進3・尺度1の計7自由度。純単眼の地図座標は任意尺度なので s を推定しても実メートルが自動決定するわけではない。正方向の実装は `Thirdparty/g2o/g2o/types/sim3.h:144–145`、逆式はその代数的整理。

`LoopClosing.cc:746–748` の `Scw=Scm Smw` は、候補 Map の世界 w→候補カメラ m→現在カメラ c の右から左への合成。点の補正は `1093–1096,1487–1495` に対応して `Xw,new=(Siw,new)⁻¹ Siw,old Xw,old`。`1021,1452–1456` の SE3 保存形 `(R,t/s)` は、PinHole の透視投影で `π(sRX+t)=π(RX+t/s)` となる表現であり、Sim3 と SE3 が同じ3D変換という意味ではない。

旧 ORB-SLAM PDF17頁（誌面16頁）Appendix 式(8)–(9)は Sim3 姿勢グラフ、式(10)–(11)は相対 Sim3 の双方向再投影誤差・固定点・Huber/逆共分散重みを説明する。今回は式の実読出典として記録し、グラフ誤差の導出を追加しない。BA の再投影式と記号は P02 参照、可動/固定集合は上表の現行呼出しに置き換える。

## 一次資料・論文との差・未確認

- [公式固定 LoopClosing.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/LoopClosing.cc)、[公式固定 Optimizer.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Optimizer.cc) をオンライン照合。現行呼出しと純単眼の除外条件を優先した。
- [ORB-SLAM3 v2](https://arxiv.org/pdf/2007.11898v2) PDF9頁§VI-A、10頁§VI-B/Dと図3(a)を本文・画像で実読。論文は welding 窓の両側 KF を可動、外側の観測 KF を固定と説明するが、現行1627→3498版は上表のとおり merge 側窓を固定する。論文の統合後 EssentialGraph の説明も純単眼の1715行分岐へ無条件には転記できない。論文の検証説明と現行のカウンタの数え方も同一視しない。
- [旧 ORB-SLAM v2](https://arxiv.org/pdf/1502.00956v2) PDF9頁（誌面8頁）§VII-A〜D、17頁 Appendix を本文・画像で実読。旧連続3候補則を現行の共視・継続検証へ流用しない。
- キャッシュは `sources/ORB_SLAM3_2007.11898v2.pdf/.txt` と `_page-09.png/_page-10.png`、旧論文の同様のキャッシュと `_page-09.png/_page-17.png`。必要画像だけ既存 PDF から描画した。新規 PDF 取得なし。
- 静的注意のみ：`KeyFrameDatabase.cc:709–728` は bad 候補の continue が i/iterator 更新より前にある。`LoopClosing.cc:556–570` は最適化した gScm から返却 gScw への反映が見えず、gScw 由来で scale=1 の estimation を構成する。いずれも実行条件・到達性・影響を再現せず、修正調査へ広げていない。
- 実行時の成功率、収束、全競合の不存在、非同期 GBA の採否保証は未検証。D12 のデータ詳細や次章へは進んでいない。取得障害なし。
