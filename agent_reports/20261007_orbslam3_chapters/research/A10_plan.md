# A10 調査計画

- 図A/図B「局所地図で確認」、A09/A15→A10→A11。純単眼通常SLAMのTrackLocalMapが既存地図を使って現在姿勢を確認する流れだけを扱う。
- 作業者はUpdateLocalMap→SearchLocalPoints→PoseOptimization、UpdateLocalKeyFrames/UpdateLocalPointsの集合構築と参照KeyFrame選択を実読する。共有観測による近傍であり世界座標の距離球と同義ではない点を確認。
- 可視性・画像範囲・距離/尺度・観測方向の条件と、投影近傍の特徴照合の境界をFrame::isInFrustum/ORBmatcher必要箇所で確認。A09と同じpose-only最適化で点位置を動かさないことを確認し、成立閾値はA11へ残す。
- 公式固定コミットTracking等の必要箇所をWeb一次資料として確認。既存ORB-SLAM原論文の局所地図追跡節、必要なら既存ORB-SLAM3図1を本文/画像で再読し、現行拡張との差を記録。新PDF取得不要。
- 6〜8件程度の短い根拠表をresearch/A10_evidence.mdへ保存。集合の意味と入力元、実装の重複除外や近傍拡張、頁/節、未確認点を含める。全内部閾値の網羅やA11以降の調査は禁止。
- 受領後、小監督がchapters/10_A10.mdを80〜100行目安で執筆。観測集合と集合和を説明用の式にして全記号を定義し、姿勢残差はA09へ参照。reviews/A10.mdで自己監査して大監督へ提出。
