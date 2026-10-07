# A14 喪失後の復帰経路の判断：根拠メモ

2026-10-07確認。純単眼 `MONOCULAR`・通常SLAMを対象とする。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。行番号はローカル `third_party/ORB_SLAM3/src/Tracking.cc`。

|項目|確認結果|根拠|
|---|---|---|
|RECENTLY_LOSTの入口|通常SLAMの入口でOKでない場合の枝へ進み、状態RECENTLY_LOSTなら純単眼は `bOK=Relocalization()` を呼ぶ。図のA15に相当。呼出しを決めるのは状態とsensor条件であり、この分岐自体が画像から新方針を推定する算法ではない。|1933–1939、1978–1986、2000–2003|
|LOSTの入口|前項の `else if(mState==LOST)` で、現在地図に応じたResetActiveMap要求またはCreateMapInAtlasの経路へ進み、この枝からreturnする。図のA19に相当。通常SLAMのこのLOST枝はRelocalizationを直接呼ばない。地図処理の境界・内部はA19へ残す。|2014–2031|
|再局在候補の範囲|Relocalization入口は `DetectRelocalizationCandidates(&mCurrentFrame, mpAtlas->GetCurrentMap())` と現在地図を渡す。DB側も `GetMap()!=pMap` の候補をcontinueする。戻り候補は現在地図に限定される。他地図の再利用・統合は別の概説として区別する。|3609–3617；KeyFrameDatabase.cc:834–835|
|同じ画像内の扱い|前半OK枝の途中で喪失状態になっても、その前半ifに対応するelseへ入り直さない。一方、後半にはLOST状態を調べる箇所がある。従って図のA14は入口状態による復帰経路の整理であり、全失敗時に直ちに同じ順序で通る関数ではない。|1939–1981、2270–2288；A08/A12根拠を再利用|

二択の整理：入口状態 `s=RECENTLY_LOST` なら再局在試行（A15）、`s=LOST` なら地図管理判断（A19）。`s` は状態enumで単位を持たない。この対応は純単眼・通常SLAMの前半分岐についての整理であり、`mbOnlyTracking=true` の別経路へ一般化しない。入口状態と処理途中で更新された状態も混同しない。

## 一次資料・PDF実読

- [公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)：RECENTLY_LOST/LOSTの前半分岐と通常SLAM条件をネット本文でも確認。
- [ORB-SLAM3論文 v2](https://arxiv.org/pdf/2007.11898v2)：PDF5頁＝誌面5頁、図1とIII節Atlas/Trackingの段落を本文・画像で再読。図1はTracking内に再局在・地図生成を置き、Atlasのactive/non-active map、別のLoop & Map Mergingも示す。本文にはAtlasの全地図への再局在という概説があるが、現行RelocalizationのcurrentMap引数とは範囲が異なるため、その文章を現行関数の検索範囲の直接根拠にしない。
- キャッシュ：`sources/ORB_SLAM3_2007.11898v2.pdf`、同 `.txt`、`sources/ORB_SLAM3_2007.11898v2_page-05.png`。新PDF取得なし。

未確認・範囲：本章は経路選択のみ。候補選別/PnP等の再局在算法、猶予時間、地図の保持・リセット境界、他地図統合内部は展開していない。実動画の到達回数未測定、コード実行・変更なし、取得障害なし。
