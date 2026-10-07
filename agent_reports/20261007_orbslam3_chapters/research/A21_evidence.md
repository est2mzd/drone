# A21 現在地図のリセット：根拠メモ

2026-10-07確認。純MONOCULAR・通常SLAM、Systemから既定引数でTracking::ResetActiveMapを呼ぶ経路。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下は `third_party/ORB_SLAM3/` 内のローカル行番号。Systemの既存保存機能追加は本章対象処理を変更していない。

|段階|具体処理と限定|根拠|
|---|---|---|
|System要求から実処理へ|System::ResetActiveMapは要求フラグを立てる。次回TrackMonocularの検査で全体resetが優先され、それがなければTracking::ResetActiveMapを呼ぶ。既定 `bLocMap=false` なのでLocalMappingへの要求も実行する。|src/System.cc:450–464、514–518；include/Tracking.h:165；src/Tracking.cc:3850–3861|
|LocalMappingの要求・待機|対象Mapとフラグを設定し、フラグがfalseになるまで待つ。ResetIfRequestedのactive枝は新KFキューと最近追加点リストをMapで選別せずclearする。単に「対象Mapだけのキュー項目を消す」とは言えない。|src/LocalMapping.cc:1077–1096、1125–1139|
|LoopClosingの要求・待機|LocalMapping要求が戻った後、LoopClosingにも要求しフラグ解除まで待つ。こちらのactive枝はキュー内でGetMapが対象Mapと一致する項目をeraseする。両要求の待機はフラグ解除待ちであり、スレッドjoinや全最適化の終了保証ではない。|src/Tracking.cc:3852–3862；src/LoopClosing.cc:2218–2265|
|DB参照の除去|前記要求の後、DB clearMap(pMap)はmutex下で語ごとの転置リストを走査し、対象Map所属KFの参照だけをeraseする。DB全消去ではなく、この関数でKFオブジェクトをdeleteもしない。|src/Tracking.cc:3864–3866；src/KeyFrameDatabase.cc:74–98|
|同一Mapの内容をclear|Atlas::clearMapはmutex下でcurrent Mapのclearを呼ぶ。Mapをnew/deleteせずAtlasのMap集合とcurrentポインタを取り替えない。Map::clearはKFのMap参照をnull化して、MapPoint/KF集合・参照点・起点集合をclear。mnMaxKFidはmnInitKFidへ戻すがMap IDのmnIdは変更しない。MapPoint/KFのdelete行はコメントのため全オブジェクト解放とは書かない。|src/Atlas.cc:230–234；src/Map.cc:214–234|
|履歴のlost印を再構成|indexをmnFirstFrameIdから開始し、残った非空MapのlowerKFIDで小さい方へ調整。mlbLostを要素ごとに走査し、index<mnInitialFrameIdなら旧値、それ以外はtrueを新リストへ追加してindex++、最後に置換。各履歴要素の実Frame IDや所属Mapを直接調べる実装ではなく、対象Map履歴の完全選別と断言しない。姿勢・参照・時刻の履歴リストをclearする処理は本関数にない。|src/Tracking.cc:3881–3912|
|追跡の再準備|mnLastInitFrameIdへFrame::nNextIdを記録、NO_IMAGES_YET、mbReadyToInitializate=false。置換前currentのIDでmnInitialFrameId/mnLastRelocFrameIdを更新し、両FrameをFrame()へ置換、参照/最後KFをnull化、初期対応をclear、mbVelocity=false。Frame/KeyFrameの全体採番を戻す行はコメント、mVelocity数値の初期化でもない。|src/Tracking.cc:3873–3879、3914–3923；Frame()の性質はA20|

順序の整理：`System要求 → 次回の要求消費 → LocalMapping応答待ち → LoopClosing応答待ち → DB参照除去 → current Map内容clear → 履歴lost印/Tracking再準備`。待機が正常に戻る前提での静的制御順で、完了時間は測定していない。現行wrapperはviewerなしで、viewerが存在する場合だけ入る停止待ち・Releaseもコードにはある（Tracking:3843–3848、3925–3926）。

Map集合をA、リセット対象をMとすれば、当該Map内容clearの効果は `A'=A, current'=M, id(M)'=id(M), K_M'=∅, P_M'=∅`。K_M/P_MはMに登録されたKF/点参照の集合で、ヒープ上の全オブジェクト集合ではない。他Mapの容器・内容をclearする呼出しではないが、LocalMappingキューは上記のとおり無選別clearであり、全関連データが他Map単位で保護されるという主張にはしない。

A20は新Mapを追加してcurrentを切り替える処理。本章は現在Mapの器を再利用する。全体Tracking::ResetはDB clear、Atlas clearAtlas＋CreateNewMap、Frame/KF採番0、全姿勢履歴clearを呼ぶ別経路であり、本章へ転記しない（Tracking:3804–3826）。本章のフラグや参照の再準備を「全状態を0へ」とまとめない。

## 一次資料・PDF実読

- [公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)、[公式固定Map.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Map.cc)：ResetActiveMapの順序、履歴・状態再準備、Map::clearの実行行とdeleteコメントをオンライン一次本文で照合。
- [ORB-SLAM3論文 v2](https://arxiv.org/pdf/2007.11898v2)：PDF5頁＝誌面5頁、図1と§III Atlas/Trackingの本文・画像を再読。複数Mapとcurrent/non-active、喪失後の地図管理の概説を確認。本章のリセット手順・フラグ待機・集合消去・履歴操作はこの概説から導かず現行コードを根拠とする。
- キャッシュ：`sources/ORB_SLAM3_2007.11898v2.pdf`、同 `.txt`、`sources/ORB_SLAM3_2007.11898v2_page-05.png`。新PDF取得なし。

未確認・範囲：実行時の待機時間、競合、メモリ回収、履歴対応の網羅的正しさは未検証。A22次入力の詳細へは進んでいない。コード実行・変更なし、取得障害なし。
