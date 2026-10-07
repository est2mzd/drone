# A16 調査計画

- 図B「復帰できた?」、A15→真ならA10、偽ならA17。再局在化関数の受理と呼出し側の最終OKを区別する。
- 作業者はRelocalization3714-3774の最適化戻り値nGood、<10の継続、条件付き追加探索/再最適化、>=50のbMatch、最終trueとmnLastRelocFrameId更新を順序付きで確認。
- iterateのbNoMore（候補の今後の試行）とbTcw（今回の姿勢返却）を区別する。bNoMore時に破棄印を付けても同じ返却姿勢を評価するコード順と、即continueがないことを必要範囲確認。
- nGoodはPoseOptimizationの戻り値でありA11のmnMatchesInliersと同じ計数処理とはしない。呼出し側2003→2125/TrackLocalMap→2142で最終OKになる流れを確認。A17の時間条件を先行しない。
- 公式固定ソースをWeb一次資料で確認し、既存原論文V.Cの本文/画像を再読。現行数値条件を旧概説から導かない。5件程度の根拠をresearch/A16_evidence.mdに保存。
- 受領時大監督通知→chapters/16_A16.md（65〜85行）/reviews/A16.md作成→提出。49/50の境界と各bool/個数の意味を中心にし、A17以降の内部未着手を維持する。
