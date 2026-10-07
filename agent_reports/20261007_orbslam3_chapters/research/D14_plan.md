# D14 調査計画

- 対象「時刻付き地図点ファイル」、A23→O01。独自SaveTimedMapPointsの入力・Map選択・点選別・時刻算出・並替え・出力列を説明する。D15/O01は先行しない。
- 復旧後の既存canonical research_workerへfollowupを試す。使用不能ならその事実を記録し別の実workerを起動する。実働の研究役を維持する。
- 実workerはローカルSystem.cc独自関数と宣言、wrapper呼出しを読み、選択尺度GetAllMapPoints().size()（有効点数/KF数ではない）、同数/全0、null/bad、有限観測時刻のmin、時刻順sort、固定小数6桁とt x y zを確認する。
- min式は対象観測集合・KF時刻・無候補時の扱いを全記号/単位付きで定義。オンライン初観測を永続記録する機構とは断定せず、現在の観測表からの算出と仮定例で示す。
- 公式固定Systemとの機能差、既読PDFのMapPoint/KF/時間入力に関わる背景本文画像を実読し5〜6件根拠をresearch/D14_evidence.mdへ保存。A23のvoid/IO未確認/Shutdown待機欠如とD10のsnapshot限界を再利用。
- 根拠受領通知→本文と自己監査保存・提出。コード独自差分を上流機能としない。文書のみ、実行・コード/設定変更・次章先行なし。

復旧記録：既存canonical `/root/chapter_supervisor/research_worker` へのfollowupが成功し、live listでrunningを確認した。新規workerの起動は不要。
