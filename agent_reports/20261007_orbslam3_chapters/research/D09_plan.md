# D09 調査計画

- 対象は「KeyFrameと受け渡し」、A06/A13→P02→P03。Frameからの構築、保持/共有する情報、独立IDと元FrameID/時刻、キューの実行境界を説明する。D10以降は先行しない。
- 同じ実workerにKeyFrame.h/.ccのコンストラクタ・ID/時刻・特徴/記述子/MapPoint参照・姿勢/観測/接続の更新口を局所調査させる。保存した画像の完全不変スナップショットとはしない。
- Trackingの初期2KF/通常CreateNewKeyFrame→LocalMapping::InsertKeyFrameとRun→LoopClosing::InsertKeyFrameの必要行を再確認。キュー投入≠処理完了、参照コピー≠地図点実体の複製を明示する。
- 最小式はKFと特徴番号からMapPoint参照へ結ぶ観測関係の整理程度にし、全記号・型・単位を説明。A13選択条件やP02/P03算法は再導出しない。
- 固定公式KeyFrame/関連キューソース、旧/新PDFのKeyFrame・並列処理の必要本文とキャッシュ画像を実読し、5〜6件根拠をresearch/D09_evidence.mdへ保存。
- 根拠受領を通知後、80〜100行の本文と自己監査をまとめて保存。実行・コード/設定変更・次章先行なし。
