# D08 調査計画

- 対象はD08「各画像の姿勢と状態」。manifestで図接続を確認し、TrackMonocularのTcw返却・FrameのHasPose・Tracking状態を別情報として説明する。D09以降は先行しない。
- 同じ実workerにwrapperの返却姿勢非保持/state==2計数、System→Grab→Frame姿勢返却と状態転記、Frame SetPose/HasPose、Trackの履歴追加と途中returnを必要範囲で確認させる。
- D06/A09/A18/A23を再利用し、Tcw世界→カメラとカメラ中心Cw=-Rcw^T tcwを最小式として全記号・座標・単位・回転前提と短例で説明する。姿勢設定済みを追跡受理と同一視しない。
- D13への接続は、全入力画像で必ず履歴行が一つ増えるわけではない点と、姿勢履歴の保存表現が返却Tcwそのものの無条件追記ではない点に限定。保存列や全履歴処理は先取りしない。
- 公式固定System/Tracking/Frame、取得済みORB-SLAM3 PDF5頁図1/§IIIと旧PDF追跡の必要本文・画像を実読し、5件程度の根拠をresearch/D08_evidence.mdへ保存。
- 根拠受領を大監督へ通知後、約90行の本文と自己監査を保存して提出。文書のみ、実行・コード/設定変更・追加不具合調査なし。
