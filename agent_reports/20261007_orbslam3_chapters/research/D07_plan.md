# D07 調査計画

- 対象はDFDの検索用DBと辞書/DBのDB部分、接続KeyFrame登録→A15,P03。D04の固定語彙と実行時登録索引の違いを主線にする。D08以降は調べない。
- 実workerを再利用し、KeyFrameDatabase.h/.ccのWordId→KFリスト、add/erase/clearMapと必要な呼出し元を実読する。MapPoint集合や永続DBと同一視しない。
- DetectRelocalizationCandidatesの現在Map限定とDetectNBestCandidatesの同Map loop/別Map mergeを分け、共有語→BoW score/共視集約→幾何検証への候補渡しを確認。閾値網羅・P03既知bad候補continue懸念の追加調査は不要。
- 必要式は索引集合I(w)と問い合わせ語の集合和だけを基本に、全記号の型・単位・重複排除等の説明上の前提を定義する。小さな仮定索引例を作る。
- 固定公式DBソース、旧ORB-SLAM PDF6頁§III-Eと新ORB-SLAM3 PDF9頁§VI-Aの必要本文・キャッシュ画像を実読。5〜7件の根拠表をresearch/D07_evidence.mdに保存し、確認限界を記録する。
- 根拠受領を大監督へ通知後、小監督が本文を約100行で執筆し自己監査とまとめて保存。コード変更・アプリ実行・新規不具合検証なし。
