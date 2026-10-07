# D06 調査計画：Frameと特徴・対応情報

- 対象は図DFDのFrame（時刻・特徴・対応情報）、A04→P01,A06,A09,A15。A04/D03/D04/D05を再利用し、ORB/BA理論やD07内部を先行しない。
- 実workerはFrame.h、単眼コンストラクタ、SetPose/必要なコピーとマッチ代入を必要範囲で確認。N個のmvKeys/mvKeysUn、N×32bytesの記述子、同じ特徴番号jのmvpMapPoints/mvbOutlierの対応を整理する。
- 初期null対応、単眼mvDepth/mvuRight=-1、N=0早期returnの範囲、姿勢値とmbHasPose、参照KF、BoW/FeatureVector、探索gridの役割を区別。全フィールド完全初期化/2D特徴=3D点/姿勢設定=追跡成功としない。
- Frameの構成または添字対応の最小式と全記号、3特徴の仮定例を用意する。コピー時のIDと共有MapPointポインタは必要な範囲だけ。
- 公式固定Frame関連ソース、既存新旧PDFのFrame特徴入力/追跡の必要本文・画像を実読。5〜7件表をresearch/D06_evidence.mdへ保存・即通知。既に確認できた内容の追加網羅調査は不要。
- 受領後小監督が90〜110行の本文と自己監査をまとめて保存。実行/ソース変更/次章先行は禁止。
