# P01 調査計画：Trackingの統括と実行境界

- manifestの並行Tracking/DFD/wrapper境界と接続を確認する。純MONOCULAR・通常SLAMの現行wrapperを対象にし、A04〜A22の算法は参照で済ませる。
- 実作業者はwrapper→System::TrackMonocular→Tracking::GrabImageMonocular→Trackの直接呼出しと、System構築時のLocalMapping/LoopClosingのstd::thread生成を確認する。Trackingという部品名/コメントを別thread生成と混同しない。
- 入力D05画像/時刻・D03カメラ設定・D04辞書と、Frame/姿勢/状態/必要時のKeyFrameキューへの出力をまとめる。出力の有効性や地図処理完了を一律に保証しない。
- Trackの現在Map取得、mMutexMapUpdateの取得行とスコープ、共有オブジェクト/キュー渡しの最小根拠を確認する。全共有情報を一つのmutexで保護するとの断定やP02/P03算法の先行はしない。
- 固定公式System/Tracking等をオンライン一次で照合し、既存ORB-SLAM3 PDF5頁図1/§IIIの本文・画像を実読する。論文上の並行機能と現行呼出しスレッドの具体実装を区別する。
- 5〜7件程度の根拠をresearch/P01_evidence.mdへ保存して即通知。受領後、小監督がASCII実行境界図を含む75〜95行程度の本文/自己監査を作る。コード実行/変更、P02/P03の先行調査なし。
