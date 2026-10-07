# D04 根拠メモ：事前語彙と画像検索表現

ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下はローカル行番号。`DBoW2/` は `third_party/ORB_SLAM3/Thirdparty/DBoW2/DBoW2/` の略。語彙は先頭1行とファイルメタデータだけ確認（145,250,924 bytes）。語彙全読込・再学習・SLAM実行はしていない。

| # | 確認事項 | 根拠 |
|---|---|---|
| 1 | `ORBvoc.txt` の先頭 `10 6 0 0` は分岐数k=10、深さL=6、スコアL1_NORM、重みTF_IDF。Systemはテキストの木・記述子・保存重みを読み込む。 | `System.cc:119–133`、`DBoW2/TemplatedVocabulary.h:1338–1415`、`BowVector.h:38–55`。この経路は学習の `create` ではない。ヘッダだけから実葉数を10^6と断定しない。 |
| 2 | ORB記述子を、各段で子ノードの代表記述子と比較し、距離最小の子を選んで葉のWordIdへ量子化する。距離は256 bitの不一致数。 | `include/ORBVocabulary.h:29–30` のFORB型、`DBoW2/FORB.cpp:26,81–100`、`TemplatedVocabulary.h:1218–1258`。木に沿う貪欲探索であり全葉の厳密最近傍探索ではない。同じ語は同じ3D点という意味ではない。 |
| 3 | Frame/KeyFrameにBoWとFeatureVectorが保持され、必要時に記述子から計算される。 | `Frame.cc:738–744` はBow空なら、`KeyFrame.cc:98–106` はBowまたはFeature空なら `transform(...,4)`。`Converter.cc:24–31` は行順で記述子を渡す。`KeyFrame.cc:52–58` はFrameの記述子・両vectorをコピーし語彙ポインタを継承。語彙そのものを画像ごとに作り直さない。 |
| 4 | BowVectorはWordId→重みの疎な表。TF-IDF経路では保存重みwが正の記述子だけ加算し、最後にL1正規化する。 | `BowVector.h:58–60`、`TemplatedVocabulary.h:1127–1161,1193`、`BowVector.cpp:34–45,62–83`、`ScoringObject.h:73–74`。学習関数のIDFは `log(NDocs/Ni)` (`TemplatedVocabulary.h:955–990`) だが、今回の実行入口ではファイル重みを読む。実訓練画像集合やその総数は未確認。 |
| 5 | FeatureVectorはNodeId→画像内特徴インデックス列。引数4は `levelsup` で、目標段は `m_L-levelsup=2`（根を0）。WordIdの葉と同じものではない。 | `FeatureVector.h:23–25,46–52`、`TemplatedVocabulary.h:1155–1160,1225–1252`。同ノードの特徴に照合候補を絞る利用は `ORBmatcher.cc:223–267`。全葉の深さ分布は未検査で、ここではコードの目標段を示す。 |
| 6 | L1Scoringは共通語の重みから画像間スコアを計算する。非負・非空・L1正規化済みの2画像なら下記の距離式と一致する。 | `ScoringObject.cpp:23–67`。空の場合もnorm=1とは置けない。どちらかが空なら実装の共通語ループは寄与せずscore=0。BoWスコアだけで幾何的一致や姿勢成立を証明しない。 |
| 7 | 事前語彙は記述子空間の離散化、検索DBは実行中のKeyFrameとの対応を保持する別のもの。 | `System.cc:122–133` は語彙読込後に別途DB生成、`KeyFrameDatabase.cc:32–35` は語彙サイズに対応する索引容器を準備。[ORB-SLAM原論文](https://arxiv.org/pdf/1502.00956v2) PDF6頁=誌面5頁 §III-E は事前学習語彙・増分検索DB・根側第2段での候補制限を説明。本文と `sources/ORB_SLAM_1502.00956v2_page-06.png` を実読。DB内部の追加調査はD07へ残す。 |

式の根拠（コードの整理式、論文式番号ではない）：

記述子 `d_j∈{0,1}^{256}`、jは画像内インデックス、`q(d_j)=i` は上記木探索で得た語iとする。葉に保存された重みを `w_i`、画像Aで語iへ割り当てられた記述子数を `n_i^A` とすると、

\[
a_i^A=\begin{cases}n_i^Aw_i&w_i>0\\0&w_i\leq0\end{cases},\quad
Z_A=\sum_i a_i^A,\quad v_i^A=a_i^A/Z_A\quad(Z_A>0).
\]

`v^A` がBowVector、`Z_A` は正規化係数。語彙全体に対する概念上のベクトルで、非出現語は0、実装は疎に保持する。TFはterm frequency（出現回数）、IDFはinverse document frequency。学習側の `w_i=ln(N/N_i)` はN枚の訓練画像中その語が現れる画像数N_iに基づく（`1≤N_i≤N`）。これは保存重みの意味の説明で、今回の語彙の訓練統計を再現した結果ではない。各重み・スコアは無次元で、3D座標やメートル尺度を含まない。

2つの非空正規化ベクトル `v^A,v^B` について、

\[
s(A,B)=1-\tfrac12\sum_i|v_i^A-v_i^B|=\sum_i\min(v_i^A,v_i^B)\in[0,1].
\]

説明用の仮定例：2語の正重み `(w_1,w_2)=(1,2)`、出現数A=`(2,1)`、B=`(1,2)` なら、加算値はA=`(2,2)`、B=`(1,4)`、正規化後A=`(.5,.5)`、B=`(.2,.8)`、スコアは `.7`。実語彙から測った数値ではない。FeatureVectorの数値は重みではなく、その画像の記述子行インデックスである。

公式固定オンラインソースも該当実装を実読：[TemplatedVocabulary.h](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/Thirdparty/DBoW2/DBoW2/TemplatedVocabulary.h)、[ScoringObject.cpp](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/Thirdparty/DBoW2/DBoW2/ScoringObject.cpp)。取得障害なし。実語数・重み分布・訓練集合・全語彙の構造健全性は未検証。DBoW2はライブラリ名として表記し、未確認の正式名称展開は追加しない。
