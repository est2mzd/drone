# D15 調査計画

- 対象「姿勢・有効フラグのファイル」、A23→O01/O03。独自SaveCameraPosesの4履歴からの再構成と9列・valid条件を説明し、O01/O03は先行しない。
- 同じ実workerがSystem.cc1394–1463、宣言、wrapper呼出し、KeyFrameのmTcp生成とGetParentの必要箇所を確認する。Map選択はD14を再利用し、この関数で独立に選び直すことを明記。
- lost/ref null/参照badなら親連鎖/親null/最終参照Map照合という条件順序を確認。4listの同じ順と長さを前提に同期走査するが検証・atomic snapshotを保証しない。
- Tcw=Tcr*親連鎖*最終参照姿勢、Cw=-Rcw^T tcw、quatのxyzw順と9列t tx ty tz qx qy qz qw validを全記号・座標・単位と小例で説明。無効行の0 0 0 0 0 0 1 0を実姿勢として扱わない。
- validはstateOK/精度/全入力の有効性印ではなく保存時条件の結果。座標・時刻・姿勢有限性/IO未検査、Shutdown/参照一覧の境界はA23/D10/D13/D14の既根拠を再利用。
- 固定上流Systemに独自関数がない点と、既読PDFの参照KF/姿勢背景の本文画像を実読し6件程度の根拠をresearch/D15_evidence.mdへ保存。受領通知後、本文100行前後と自己監査を保存。実行・コード変更なし。
