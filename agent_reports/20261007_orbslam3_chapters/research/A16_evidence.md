# A16 再局在化の成立判定：根拠メモ

2026-10-07確認。対象は純単眼・通常SLAM。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下は `third_party/ORB_SLAM3/src/` 内のローカル行番号。

|段階|確認結果|根拠|
|---|---|---|
|solverの2つのbool|`bNoMore` は当該候補に今後の試行を残すかの情報、`bTcw` は今回姿勢を返したか。bNoMoreなら候補に破棄印を付けて残数を減らすが、ここにcontinueはなく、その後bTcwを別に検査する。solverにもbNoMore=trueの後で最良姿勢を返しtrueとなる経路がある。|Tracking.cc:3683–3696；MLPnPsolver.cpp:205–218|
|nGoodの意味と最初の関門|姿勢と対応をFrameへ設定後、`nGood=PoseOptimization(...)`。通常終了の戻り値は `nInitialCorrespondences-nBad`（初期対応3未満なら早期0）。単眼では姿勢最適化へ渡した対応から最終外れ値数を引く計数で、A11のObservations条件付きループと同じ処理ではない。最初のnGood<10なら当該姿勢の追加探索・受理判定を飛ばして次候補へcontinue（それ自体は候補破棄印を設定しない）。|Tracking.cc:3695–3717；Optimizer.cc:868、996–997、1008以降、1113；Tracking.cc:3004–3020|
|追加探索と再最適化の順序|最初のnGood>=10で外れ値対応を除去。nGood<50なら広い投影探索。`nadditional+nGood>=50` の場合だけ再最適化しnGoodを上書き。その新nGoodが `>30 && <50` なら狭い探索を行い、再び合計>=50なら最終再最適化。追加対応数を足しただけでは最終受理しない。|Tracking.cc:3719–3751|
|関数内の受理|各候補処理末尾の、最後に得た最適化戻り値が `nGood>=50` なら `bMatch=true` として候補ループを抜ける。最終的にbMatch=falseならfalse、trueなら `mnLastRelocFrameId=mCurrentFrame.mnId` を記録してtrue。姿勢はこの判定より前に設定済みなので、false返却が必ずFrameの姿勢未設定を意味するとは言えない。|Tracking.cc:3695–3696、3756–3774|
|呼出し側の最終OK|再局在戻り値は `bOK` に入り、trueなら同じ画像についてTrackLocalMapを呼び、その結果でbOKを上書きする。最後のbOKがtrueならmState=OK。従ってRelocalization=trueや再局在ID更新だけで、Track全体の最終OKまで確定したとはしない。|Tracking.cc:2003、2123–2127、2142–2143|

記号：`nGood`、`nadditional` は整数の対応数（個）。前者は各PoseOptimization後の戻り値、後者は投影探索で追加した対応数。`bMatch` は候補の最終受理を記憶するbool、`bOK` は呼出し側で各段階の結果に上書きされるbool。`mnLastRelocFrameId` は画像IDで、秒単位の時刻ではない。

境界の整理：最初の9点はcontinue、10点は追加処理へ進める。広い探索後の再最適化が30点なら狭い探索に入らず、31～49点なら入る。最後の最適化結果49点では受理せず、50点なら受理する。例えば「40点＋新規10対応」は再最適化の実行条件であり、その結果が49点なら未受理。この途中の49点は狭い探索へ進んで改善し得るため、その時点でRelocalization全体のfalse返却が確定するわけではない。これらはコード入力を仮定した説明例で、実動画測定ではない。

## 一次資料・PDF実読

- [公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)：bNoMore/bTcwの独立分岐、最適化と追加探索、bMatch/最終returnをネット本文でも確認。
- [ORB-SLAM原論文 v2](https://arxiv.org/pdf/1502.00956v2)：PDF8頁＝誌面7頁、V.Cの本文とページ画像を再読。姿勢仮説→最適化→誘導探索→再最適化→十分なinlierで継続、という説明を確認。現行の10/30/50やboolの制御順は論文の概説から導かず、上記ソースに基づく。
- キャッシュ：`sources/ORB_SLAM_1502.00956v2.pdf`、同 `.txt`、`sources/ORB_SLAM_1502.00956v2_page-08.png`。新PDF取得なし。

未確認・範囲：実データでの候補成否・最適化後の数値は未測定。A17の時間条件は扱っていない。コード実行・変更なし、取得障害なし。
