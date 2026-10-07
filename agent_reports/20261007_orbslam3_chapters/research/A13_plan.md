# A13 調査計画

- 図A「姿勢を得る・必要ならキーフレームを選ぶ」、A07/A11→D08,D09,P02、合流点A。純単眼通常SLAMの成功後NeedNewKeyFrame/CreateNewKeyFrameとLocalMappingへのキュー挿入までを扱う。
- 作業者はTrackの呼出し条件、NeedNewKeyFrameの早期抑止・参照観測数/現在対応数・Frame間隔・mapper受付/負荷条件を現在のMONOCULARに簡約して確認する。境界と判定順を記録し、IMU/ステレオ/RGBDの網羅はしない。
- CreateNewKeyFrameの生成・既存対応受渡し・LocalMappingキュー挿入を確認。生成と非同期処理完了、純単眼で深度から新点を作る他sensor用分岐へ入らない点、初期2KeyFrameはA06の別経路を区別する。LocalMapping処理内部へは進まない。
- 公式固定コミットソースをWeb一次資料で確認。既存ORB-SLAM原論文V.Eの本文/画像を再読し、旧方針/閾値と現行差を記録。新PDF取得不要。
- research/A13_evidence.mdへ6〜8件の短い根拠と純単眼簡約条件を保存。受領時に大監督へ通知。本文は90〜120行のchapters/13_A13.md、自己監査reviews/A13.mdを作成。
- 姿勢式はA09参照を使い重複を抑え、判断式の記号/型/単位/前提を明示。A14以降の調査・コード変更/実行は禁止。
