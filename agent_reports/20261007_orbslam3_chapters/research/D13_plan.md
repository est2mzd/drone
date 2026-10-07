# D13 調査計画

- 対象「Trackingの姿勢履歴」、P01,D08→A23。relative/reference/time/lostの4並列listを一つの論理記録として説明する。D14/D15は先行しない。
- 同じ実workerがTracking.hの型とTracking.cc末尾2300付近の追加条件・isSet/else、初期化/LOST途中return、UpdateLastFrameの相対姿勢再構成を確認。D08/A18/A20/A21を再利用し全状態を再調査しない。
- Tcr=Tcw*Trw^-1とTcw再構成の最小式を全記号・方向・型・単位・前提付きで示す。参照KF更新によって再構成結果が変わるが、過去の真値を保証しない。
- OK/RECENTLY_LOSTでの追加時mState==LOSTがfalseである点、isSet falseなら時刻も前値コピー、全ResetのclearとActiveResetのlost再構成、Map切替で全履歴が消えない点を最小限確認。
- 3入力の仮定例で入力数/OK件数/履歴数と履歴時刻を区別。elseの到達率・空リスト安全性等の新しい不具合調査を行わず、コード上の前提を限定する。
- 固定公式Tracking必要箇所と既読PDFの追跡/参照KFの必要本文画像を実読再利用し、5〜6件根拠をresearch/D13_evidence.mdへ保存。受領通知後、約100行の本文と自己監査を保存。実行・コード変更なし。
