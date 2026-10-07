# A12 一時的な追跡喪失への遷移：根拠メモ

確認日：2026-10-07。対象は純単眼 `MONOCULAR`・通常SLAM。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下の `Tracking.cc`、`Frame.cc` は `third_party/ORB_SLAM3/src/` 内で固定版から未変更。

|項目|確認結果|ローカル根拠|
|---|---|---|
|A11後の遷移|`bOK=true` なら状態をOKへ。falseかつ**その判定時点で** `mState==OK` なら、純単眼分岐で `mState=RECENTLY_LOST`、`mTimeStampLost=mCurrentFrame.mTimeStamp`。この箇所はKeyFrame数を検査しない。|Tracking.cc:2142–2162|
|先行する姿勢推定失敗|入口OKの姿勢推定で `bOK=false` になった場合、純単眼はIMU専用条件を通らず、現在地図の `KeyFramesInMap()>10` ならRECENTLY_LOSTと画像時刻保存、それ以外はLOST。後者ではこの枝で喪失時刻を代入しない。|Tracking.cc:1933–1939、1959–1975|
|状態を毎回上書きしない|先行箇所ですでにRECENTLY_LOSTまたはLOSTになっていれば、後段の `else if(mState==OK)` は通らない。従ってfalseのたびにRECENTLY_LOSTや喪失開始時刻を再設定するわけではない。通常SLAMで既存 `bOK=false` の場合はTrackLocalMap自体も呼ばない。|Tracking.cc:2122–2131、2142–2164|
|保存時刻の出所|ラッパーは `t_k=k/f` をTrackMonocularへ渡す。`k` は読めた画像の0始まり番号、`f` はVideoCaptureのFPS（1未満時30）、`t_k` の単位は秒。System→GrabImageMonocular→Frameへ同じ引数が渡り、Frameが `mTimeStamp` に保存。処理実時間時計や機体通信断の時刻ではない。|slam/src/offline_mono.cpp:33–47、54；System.cc:471；Tracking.cc:1584–1589；Frame.cc:289–291|
|同一画像と次画像|入口OKの枝の途中で状態を変えても、その枝に対応する前半 `else` へ同一呼出し中に入り直さない。状態代入後も現在画像の後半処理は続き得る。LOSTには別の後半条件があるため「喪失になったら即座に次画像」とは書かない。RECENTLY_LOSTが保持されて次の画像を処理する場合、次回の入口状態としてその分岐が評価される。|Tracking.cc:1939–1981、2164以降、2270–2294|

## 解釈と一次資料

本章の中心は `(!bOK && s==OK) → (s'=RECENTLY_LOST, t_lost=t_k)`。`s` は後段条件を評価するときの状態、`s'` は代入後の状態、`t_lost` は記録した喪失開始画像時刻である。これはコードを整理した規則で、すべての追跡失敗に共通する無条件遷移ではない。ラッパーの `steady_clock` 計測と `t_k` は別用途であり、画像処理の長短によって `t_k` が増減する式ではない。

- [公式固定コミット Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)：先行姿勢失敗の状態・時刻代入と後段の同代入をWeb本文でも確認。行番号はローカル基準。
- [ORB-SLAM3論文 v2](https://arxiv.org/pdf/2007.11898v2)：PDF5頁＝誌面5頁、図1およびIII節 “Tracking thread” の喪失説明を本文と画像で再読。追跡喪失後に再局在を試す概説であり、本章のenum名・KeyFrame数条件・時刻代入条件は現行コードを根拠とする。
- 実読キャッシュ：`sources/ORB_SLAM3_2007.11898v2.pdf`、同 `.txt`、`sources/ORB_SLAM3_2007.11898v2_page-05.png`。

未確認・範囲：実動画の喪失原因や到達回数は未測定。復帰算法、猶予時間、地図保持・リセットの詳細は後章へ残した。コード実行・変更なし、新PDF取得なし、取得障害なし。
