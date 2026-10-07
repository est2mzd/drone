# D10 調査計画

- 対象は「Atlas・地図群と共有更新」。manifestの接続を確認し、AtlasのMap集合/currentMapと各MapのKF/MP集合、共有参照と所属を説明する。D11以降は先行しない。
- 同じ実workerがAtlas/Mapの必要フィールド・GetAllMaps/GetAllMapPoints/current/stored/bad・追加/所属更新の局所実装を実読。容器のコピーを点/KF/Map実体の複製や原子的全体snapshotと同一視しない。
- A20/A21/P01/P02/P03/A23を再利用し、Tracking/LocalMapping/LoopClosingの代表的な読書きとmutex範囲を必要最小限で確認。全リセット・地図統合算法や競合検証は再調査しない。
- 各Mapの座標系と単眼任意尺度、current/stored/badの状態管理を説明。storedをディスク保存、同Atlas所属を座標整列済みとしない。最小集合/所属式と二Map仮定例で十分。
- 固定公式Atlas/Mapと既読ORB-SLAM3 PDFのAtlas・並列構成の必要本文/画像を再読し、5〜6件根拠をresearch/D10_evidence.mdへ保存。
- 受領通知後、本文80〜100行と自己監査をまとめて保存して提出。文書のみ、実行/コード変更/次章先行なし。
