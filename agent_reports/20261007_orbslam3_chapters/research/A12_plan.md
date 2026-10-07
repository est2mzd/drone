# A12 調査計画

- 図A「喪失状態へ」、A11失敗→次画像のA08/A14。純単眼・通常SLAMで、Track2142-2162のbOK=falseかつmState==OKによるRECENTLY_LOSTと画像時刻保存を中心にする。
- 作業者は1959-1975の先行姿勢失敗時に地図KeyFrame数でRECENTLY_LOST/LOSTへ分岐する点を最小限確認し、失敗なら常にRECENTLY_LOSTへ上書きすると誤解させない。
- 記録するmTimeStampLostが現在Frameの画像時刻であること、現行wrapperの時刻基準はA03からの入力で処理実時間や機体通信状態ではないことを確認。同一画像内の後続処理と次画像入口を区別する。
- 公式固定コミットTracking.ccの必要箇所をWeb一次資料として確認。既存ORB-SLAM3 PDFのTracking/喪失説明を本文/画像で再読。現行enum/条件と概説を区別し、新PDFを増やさない。
- 4〜5件の短い根拠をresearch/A12_evidence.mdへ保存。受領時に大監督へ即通知し、小監督が55〜70行のchapters/12_A12.mdとreviews/A12.mdを作る。
- 復帰算法・時間制限・地図保持の詳細はA14以降へ残す。A13以降先行禁止、コード実行/変更なし。
