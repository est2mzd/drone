# A17 復帰試行を続けるかの判断：根拠メモ

2026-10-07確認。純 `MONOCULAR`・通常SLAMの入口RECENTLY_LOSTに限定。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。Tracking行番号は `third_party/ORB_SLAM3/src/Tracking.cc`。

|項目|確認結果|根拠|
|---|---|---|
|評価順序|まず `bOK=Relocalization()`。その後 `mCurrentFrame.mTimeStamp-mTimeStampLost>3.0f && !bOK` ならLOSTへ変更しbOK=false。この判定は再局在試行を開始する前の時間切れ検査ではない。|Tracking:2000–2011|
|境界と成否|時間差が計算上ちょうど3.0なら、再局在falseでもこの条件は発火しない。3.0を超えても今回のRelocalization戻り値がtrueなら発火しない。このboolは後続TrackLocalMap前の結果であり、画像処理全体の最終追跡成功と同義ではない。|Tracking:2003–2006；後続2125–2127、2142–2143はA16根拠|
|時刻の基準|喪失開始値は現在Frameの画像時刻から保存（A12）。wrapperは `t_k=k/f` を渡す。kは0始まりの読めた画像番号、fはCaptureのFPS（1未満時30）、時刻と差の単位は秒。CPU処理時間・実時計経過ではなく、3秒sleepする処理もこの枝にはない。|Tracking:1970、2162；slam/src/offline_mono.cpp:33–47、54；A03/A12|
|継続の前提とIMUの区別|次画像での再試行には画像入力が続き、対象状態で再びこの枝へ入ることが必要。wrapperはread成功ごとに逐次TrackMonocularを呼ぶため、EOF/read失敗後や入力が来ない間に独立時計でこの判定を続ける構造ではない。`time_recently_lost(5.0)` は直前のIMU sensor枝の比較に使われ、純単眼の3.0fとは別。|wrapper:45–55；Tracking:48、1981–1997、2000–2011|

整理式：`Δt=t_k−t_lost`、`b=Relocalization()` と置けば、この箇所のLOST遷移条件は `(Δt>3秒) && (b=false)`。Δtは画像時刻差、bは今回の再局在関数のbool戻り値。式はコードの整理であり、論文式ではない。今回b=trueでも後続の局所地図確認は別にあるため、「3秒以内に最終OKへ戻れなければ必ずLOST」とは一般化しない。

境界例（比較時の数値を仮定）：Δt=3.0・b=falseでは条件不成立、Δt=3.1・b=falseでは成立、Δt=3.1・b=trueでは不成立。実際のk/f計算の浮動小数点誤差を測定した例ではなく、撮影時刻の真値を保証する例でもない。

## 一次資料・PDF実読

- [公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)：再局在先行、厳密な `>3.0f && !bOK`、IMU側の別条件をネット本文でも照合。
- [ORB-SLAM3論文 v2](https://arxiv.org/pdf/2007.11898v2)：PDF5頁＝誌面5頁、III節Trackingの喪失段落を本文・画像で再読。喪失後の再局在試行と、一定期間後に別の地図管理へ進む概説を確認。この段落には現行純単眼の3.0f・等号境界・成功条件付きの評価順序は書かれておらず、数値と制御順はコード根拠とする。
- キャッシュ：`sources/ORB_SLAM3_2007.11898v2.pdf`、同 `.txt`、`sources/ORB_SLAM3_2007.11898v2_page-05.png`。新PDF取得なし。

未確認・範囲：実時間での待ち時間・復帰率・動画上の遷移回数は未測定。A18の後半処理詳細へは進めていない。コード実行・変更なし、取得障害なし。
