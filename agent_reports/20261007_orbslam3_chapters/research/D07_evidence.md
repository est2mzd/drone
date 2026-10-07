# D07 根拠メモ：検索用KeyFrameデータベース

ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下は `third_party/ORB_SLAM3/` 以下のローカル行番号。D04の語彙、A15/P03の幾何検証は再導出しない。

| # | 確認事項 | 根拠 |
|---|---|---|
| 1 | DBは語ごとのKeyFrameポインタリストを持つ。語彙木やMapPoint集合とは別で、ここで操作するのはメモリ上の索引。 | `include/KeyFrameDatabase.h:87–97`：`const ORBVocabulary*` と `vector<list<KeyFrame*>>`。`src/KeyFrameDatabase.cc:32–35` は語彙サイズ分の索引を用意。保存用のID表も別フィールドにあるが永続化内部は本章の対象外。 |
| 2 | addはKFのBoWにある語へポインタをpush_back。eraseは各語リスト中の最初の一致を削除。clearMapは所属Mapが一致する項目を削除し、KF実体をdeleteしない。 | `KeyFrameDatabase.cc:39–98`。add/erase/clearMapはmutex取得。addに重複登録検査はなく、集合の一意性を実装保証としない。`clear:68–72` は索引全体を空にして語彙サイズへ戻すが内部lockはない。全操作が同一方法で保護されると説明しない。 |
| 3 | 登録・削除はSLAM処理に伴う明示呼出しで行われる。全入力Frameや全生成KFの登録を自動保証する容器ではない。 | `LoopClosing.cc:356–361,491–522` は小地図の早期終了経路または候補検証後にadd。`LoopClosing::InsertKeyFrame` はid=0をキューへ入れない。`KeyFrame.cc:677–678` はMapからの除去と別にDB erase、`Tracking.cc:3866` はactive resetでclearMap（A21）。全登録経路網羅はしていない。 |
| 4 | Relocalization用検索は共有語→BoW類似度→共視近傍のスコア集約→候補選別。現在Map条件は**最後の返却候補を入れる前**に適用。 | `KeyFrameDatabase.cc:733–844`：共有語 `741–755`、score `780–785`、共視集約 `795–821`、Mapフィルタ `834–835`、重複返却抑止 `836–839`。呼出し元 `Tracking.cc:3613–3617` がcurrentMapを渡す。他Mapを検索・集約の最初から除外する構造ではない。 |
| 5 | Loop/Merge検索では接続KFを除いた共有語候補を評価・共視集約し、同Map候補と別Map候補へ分ける。 | `DetectNBestCandidates:604–730`：接続除外 `613,626`、score `659–664`、集約/降順 `674–702`、同Maploop `717–720`、別Mapmerge `721–724`。`LoopClosing.cc:491` はnNumCandidates=3で呼ぶ。旧論文の候補数説明を現行APIの両出力へそのまま転記しない。 |
| 6 | DB返却は幾何一致の成立ではない。 | `Tracking.cc:3641–3657` は候補KFからBoW対応を得てMLPnPsolverへ。`LoopClosing.cc:505–512` はLoop/Merge候補を別々に `DetectCommonRegionsFromBoW` へ渡す。詳細はA15/P03参照。索引の共有語は外観の候補を作るための情報。 |
| 7 | 論文も事前語彙と増分索引、外観検索と幾何検証を分ける。 | [旧ORB-SLAM](https://arxiv.org/pdf/1502.00956v2) PDF6頁=誌面5頁 §III-E：語→観測KFの倒立索引、KF削除に伴う更新、共視による集約。[ORB-SLAM3](https://arxiv.org/pdf/2007.11898v2) PDF9頁=誌面9頁 §VI/VI-A：AtlasのBoW候補検索後に幾何検証し、同Mapと別Mapで用途が分かれる。両ページのキャッシュ本文と画像を実読。現行の最終Mapフィルタ位置やAPI条件はコードを優先。 |

最小式（集合として表す説明上のモデル）：

\[
I(w)=\{K\mid K\text{の参照が語}w\text{の索引に登録されている}\},\quad
W_Q=\operatorname{supp}(v_Q),\quad
C_0(Q)=\bigcup_{w\in W_Q}I(w).
\]

wはWordId（語の整数識別子）、KはKeyFrameを指す参照、Qは問い合わせFrameまたはKeyFrame、v_QはD04のBoW、W_Qはその非零語集合。I(w)は実リストから重複を除いた概念集合、C0は共有語から拾う入口候補集合であって最終返却結果ではない。全て無次元の識別子・集合で、画素/3D座標/距離の式ではない。実装では問い合わせIDによる候補重複の抑制や、最終出力用setを使い、共有語数も数える。add自体の重複非許容を仮定しない。

仮定例：`I(w1)={K1,K2}`, `I(w2)={K2,K3}`, 問い合わせ語が `{w1,w2}` なら `C0={K1,K2,K3}`（K2を2件と表さない）。K1/K2がMap A、K3がMap Bの所属でも、この集合和自体では除外しない。その後の点数・共視・返却条件により候補は減り得る。再局在化の対象MapがAなら返却候補にK3は入らない。Loop/Mergeでは残った候補を所属Mapで分ける。これらは索引の読み方の例で、実動画の検索結果ではない。

固定公式一次 [KeyFrameDatabase.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/KeyFrameDatabase.cc) の更新・NBest・Relocalization必要箇所を実読。PDF画像は `sources/ORB_SLAM_1502.00956v2_page-06.png` と `sources/ORB_SLAM3_2007.11898v2_page-09.png` を再利用。

未確認・限界：実行時の登録集合/重複/候補順位は未測定。P03で確認済みの `isBad()` 時continueによる反復進行の静的懸念（DB `709–728`）はP03参照に留め、新規再現・修正調査は行わない。検索が常に完了する保証や論文の精度数値を現行動画への保証としない。取得障害なし。コード変更/アプリ実行/D08先行なし。
