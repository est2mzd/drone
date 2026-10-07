# D02 調査計画：FPSと時間基準

- 対象はDFDの動画FPS、接続「動画情報→A03,D05」。動画由来のCAP_PROP_FPSとCamera.fpsの設定取込を別経路として扱う。次章先行なし。
- 実作業者はwrapper33〜54のget/比較/fallback/timestampと処理経過時計を確認し、f_raw<1なら30、その他その値という現行分岐と非有限値未検査を正確に記録する。
- Trackingのsettings/旧設定取込とmMaxFramesを必要範囲で読み、動画get値がCamera.fpsを上書きする経路と誤解しない説明を用意する。全ての使用箇所の網羅は不要。
- 公式OpenCV VideoCapture getとCAP_PROP_FPS/CAP_PROP_POS_MSECの文書を実読。既存ORB-SLAM3 PDFの画像・時刻入力に関連する必要頁本文/画像を再利用し、このwrapperのk/f式を論文由来としない。
- t_k=k/f、Δt=1/f、f採用規則の記号型/単位/有限正/等間隔という前提を整理する。撮像時刻/個別PTS/処理経過時計を区別し、30fps例とA17の参照程度に留める。
- research/D02_evidence.mdへ4〜6件程度の短い根拠表を保存・即通知。小監督は受領後80〜100行の本文/自己監査を作成する。実行/設定変更/新規の網羅調査は不要。
