# P02 調査計画：LocalMappingと非同期キュー

- manifestのLocalMappingの位置/接続を確認し、純MONOCULARのLocalMapping::Runを対象にする。P03内部の先行は禁止。
- 実作業者はKeyFrameキュー受取→BoW/観測/共視接続→MapPoint culling→新点triangulation→隣接融合→条件付き局所BA/KeyFrame culling→LoopClosingへの受渡しを、Runのif条件と共に確認する。新入力・停止要求・abortの扱いを読み、AcceptKeyFramesとキュー空/完了を区別する。
- ProcessNewKeyFrame/CreateNewMapPoints/SearchInNeighbors/MapPointCulling/KeyFrameCullingは上記の目的と具体処理の必要範囲だけを調べる。全しきい値列挙はせず、二視点幾何・A06初期化との違いを整理する。
- 純単眼で呼ぶOptimizer実関数と局所BAの変数/固定KeyFrame/MapPoint/再投影残差/重み/外れ値・中断を照合する。A09姿勢だけ最適化との相違を確認し、一般的な式と現行の反復手順を区別する。
- 公式固定LocalMapping/Optimizerの該当箇所をオンライン一次で確認し、取得済み旧ORB-SLAM PDFの§VIとBA Appendixの該当本文/式/画像を実読する。必要ページは既存PDFから再利用/描画し、新PDF取得は原則不要。
- 主要根拠8件程度をresearch/P02_evidence.mdへ保存して即通知。必要な式の出典・ページと、現行コードとの差/未確認点を添える。小監督は受領後110〜140行程度の本文・自己監査を作成する。コード実行/改修・ビルドは禁止。
