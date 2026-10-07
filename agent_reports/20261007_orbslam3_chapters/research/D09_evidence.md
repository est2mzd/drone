# D09 根拠メモ：KeyFrameと受け渡し

対象 `A06/A13 → P02 → P03`。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下は同リポジトリ内ローカル行番号。選択閾値・LocalMapping/LoopClosing算法は既章参照。

| # | 確認事項 | 根拠 |
|---|---|---|
| 1 | KeyFrameは元Frame ID・時刻を継承するが、自身のIDは別に採番する。 | `src/KeyFrame.cc:45–46,64`：`mnFrameId(F.mnId),mTimeStamp(F.mTimeStamp)` と `mnId=nNextId++`。`include/KeyFrame.h:312–315`：自身IDはlong unsigned int、元Frame IDはconst long unsigned int、時刻はconst double。時刻の秒/入力順との関係はD05。 |
| 2 | 特徴・記述子・検索表現・校正・姿勢と、既存地図への参照を引き継ぐ。地図点実体は複製しない。 | `KeyFrame.cc:50–60,66–77,93`：特徴vector等をコピー、`mDescriptors(F.mDescriptors.clone())`、`mvpMapPoints(F.mvpMapPoints)`、語彙/カメラ等はポインタ参照、gridもコピーし `SetPose(F.GetPose())`。Frameを単なる画像ファイルとして保存する処理ではない。 |
| 3 | KeyFrame全体は不変スナップショットではない。姿勢・観測先・接続を更新するAPIがある。 | `KeyFrame.cc:109–120` SetPose、`297–327` Add/Erase/ReplaceMapPointMatch、`189–202` AddConnection、`379` UpdateConnections。`KeyFrame.h:385` の記述子constと、姿勢・観測・接続の更新可能性を混同しない。 |
| 4 | 初期2KFと通常追加KFは異なる作成入口からLocalMappingへ渡る。 | 初期は `Tracking.cc:2529–2530` で2つ構築、`2540–2541` でMapへ追加後 `2623–2624` でLM投入。通常は `3216–3224` の早期抑止を通過すると構築し `3335` で投入。通常側のMap追加は `LocalMapping.cc:298–337` の処理内。両者を同じ登録順としない。 |
| 5 | LMへの投入は処理完了ではなく、共有KFポインタをキューへ積む操作。LMが後で取り出して処理する。 | `LocalMapping.cc:284–288` はmutex下push_backとBA中断要求。Run `74–83` → ProcessNewKeyFrame `298–308` でfront/popとBoW、`310–337` で必要な観測関係・共視接続・Atlas登録を更新。地図点への参照コピーだけで観測の両側登録が全て済むわけではない。 |
| 6 | LMの処理経路からLCへもキューで渡す。全KFがそのまま受理される保証やBA完了の保証はない。 | `LocalMapping.cc:250` はその回の条件付き処理経路の後で `mpLoopCloser->InsertKeyFrame(mpCurrentKeyFrame)`。P02の条件付きBAを毎回完了したという意味ではない。`LoopClosing.cc:311–316` はmutex下でID≠0の場合だけキューにpush。LCの幾何処理完了とも別。 |

最小関係式は、単眼KeyFrame Kの特徴番号jについて

\[
\mathcal O_K(j)=K.\mathrm{mvpMapPoints}[j]\in\{\mathrm{null}\}\cup\{\text{MapPointへの参照}\},\quad 0\le j<N_K.
\]

KはKeyFrameオブジェクト、N_Kはその特徴数（整数）、jは画像内特徴番号、O_Kはその番号から地図点への関連。番号・参照は無次元で、3D座標値そのものではない。画像特徴の画素単位や記述子行との対応はD06。観測登録はK側の関連と地図点側の観測を更新する操作を区別する（初期例 `Tracking.cc:2553–2557`、通常はLM `319–323`）。

仮定例：Frame ID120・時刻4.0秒から、新しいKF ID7を構築すると、`mnFrameId=120,mTimeStamp=4.0,mnId=7`（採番状態を仮定）。元Frameのj=2が地図点Pを参照していれば構築直後の `O_K(2)=P` も同じ実体を指す。記述子行はcloneされた別データだがP自体は複製されない。後からKの姿勢が修正されても元Frame IDと入力時刻はそのまま、という情報の役割の違いを示す例。実動画計測ではない。

固定一次 [KeyFrame.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/KeyFrame.cc)、[LocalMapping.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/LocalMapping.cc) の構築/更新/キュー必要箇所を実読。[ORB-SLAM3 v2](https://arxiv.org/pdf/2007.11898v2) PDF5頁=誌面5頁 図1/§IIIはKeyFrameのTracking→LocalMapping→Loop/Map Mergingと並列構成、[旧ORB-SLAM v2](https://arxiv.org/pdf/1502.00956v2) PDF8頁=誌面7頁 §VI-AはKF挿入に伴う共視/BoW更新を説明。両方の必要本文とキャッシュ画像を再読。現行の構築仕様・実行順はコードを根拠とする。

取得障害なし。実行時キュー滞留・処理完了時刻・各KFの実観測集合は未確認。コード変更/アプリ実行/D10先行なし。
