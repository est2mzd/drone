# D04 調査計画：事前語彙と画像検索表現

- 対象は図DFDの特徴の辞書と辞書/DBの辞書部分、語彙ファイル→P01,A15,P03。事前語彙と地図点/実行中のKeyFrame検索DBを分け、D05以降へ先行しない。
- 実作業者の再利用をまず試し、呼出不能なら別実働workerを起動し継承を記録する。先行章の根拠キャッシュは再利用できる。
- 巨大ORBvocは先頭とメタデータだけ確認し、木分岐数/深さ/重み付け/スコア種別をDBoW2列挙定義と照合する。全内容の出力・語彙再学習・SLAM実行は不要。
- SystemのloadFromTextFile、Frame/KeyFrame ComputeBoW、DBoW2 TemplatedVocabulary/ScoringObject/FORBを必要範囲で読み、ORB記述子の木量子化→BowVector/FeatureVectorの役割と生存期間を確認。学習と読込・実行時変換を混同しない。
- 現行ヘッダに応じたTF-IDF/L1の式、全記号/値域/非空正規化等の前提、短い数値例を整理する。FeatureVectorの引数4が表す木の段と画像内インデックスを正確に確認する。
- 公式固定ソースと既存旧ORB-SLAM PDFのBoW/場所認識の必要頁本文・画像を実読する。新PDF追加は不足時だけ。research/D04_evidence.mdへ6〜8件程度の表と必要式を保存・即通知。
- 受領後小監督が120行前後の本文・自己監査を作る。コード/設定変更・ビルド・動画/アプリ実行・次章調査は禁止。

実働記録：既存`/root/chapter_supervisor/research_worker`へfollowupを送り、live一覧のrunningと本人の受領応答を確認した。同じworkerを再利用し、新規起動なし。
