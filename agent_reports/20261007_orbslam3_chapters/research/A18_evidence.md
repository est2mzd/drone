# A18 追跡喪失の確定：根拠メモ

2026-10-07確認。純 `MONOCULAR`・通常SLAMで、入口RECENTLY_LOSTからA17条件により同じ画像内でLOSTとなる経路を対象とする。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。行番号はローカル `third_party/ORB_SLAM3/src/Tracking.cc`。

|制御点|確認結果|根拠|
|---|---|---|
|状態確定と前半分岐|A17で `mState=LOST,bOK=false` を代入。既にRECENTLY_LOSTのif側に入っているため、その後に対応する `else if(mState==LOST)` へ入り直さない。入口からLOSTだった画像の前半経路とは別である。|1981–1982、2006–2014|
|局所地図確認は未実行|通常SLAMの `if(bOK)` がfalseなのでTrackLocalMapを呼ばない。一方、続く `if(!bOK)` により “Fail to track local map!” のログは出る。このログだけで局所地図追跡が実行されて失敗したとは判定できない。|2122–2131|
|状態再反映と表示|`if(bOK)` はfalse、`else if(mState==OK)` もfalseなので、ここでOKやRECENTLY_LOSTに上書きしない。ただし後続のFrameDrawer更新と、姿勢設定済みならMapDrawer更新は通る。LOST代入と同時に全後続処理が止まるわけではない。|2142–2164、2200–2203|
|成功・一時喪失用処理を飛ばす|`bOK || mState==RECENTLY_LOST` はfalse。ここに含まれる通常の運動モデル更新やNeedNewKeyFrame/CreateNewKeyFrame等の処理を、この画像では通らない。その後、独立した `if(mState==LOST)` へ到達する。|2205–2268、2271|
|地図管理判断後にreturn|後半LOSTの純単眼経路は地図管理の呼出し後にreturnするため、2294行の通常の `mLastFrame=Frame(mCurrentFrame)` と2300行以降の姿勢履歴保存には到達しない。呼び出す地図処理内部の更新とは区別する。地図処理後の返却時までLOST固定とは断言しない。|2271–2288、2294、2300–2317|

最小の整理：A17直後の組 `(s,b)=(LOST,false)` から、局所地図確認を飛ばし、後段状態反映も変更せず、表示用データ更新を通り、成功/RECENTLY_LOST用ブロックを飛ばして、独立LOST判断へ進む。`s` は状態enum、`b` は局所的な成否boolで、いずれも単位を持たない。これは現行コードの制御順を整理したもので論文式ではない。

別の入口はA12で扱った、入口OKの初期姿勢推定失敗からLOSTになる枝（1959–1975）。この場合も前半elseへ再入せず後半へ進む点は共通するが、A17の時間条件が全LOST遷移に必須という意味ではない。地図サイズの分岐境界と各地図処理はA19以降へ残す。

## 一次資料・PDF実読

- [公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)：後半の `bOK || RECENTLY_LOST`、独立LOST、return、通常Frameコピーと履歴保存の位置をネット本文で照合。
- [ORB-SLAM3論文 v2](https://arxiv.org/pdf/2007.11898v2)：PDF5頁＝誌面5頁、図1および§III Trackingの喪失段落を本文・画像で再読。追跡喪失から再局在試行、継続困難時の地図管理という概説を確認。同一画像でのif/else非再入、ログと実呼出しの差、return位置は論文に記された制御ではなく現行コードの根拠とする。
- 実読キャッシュ：`sources/ORB_SLAM3_2007.11898v2.pdf`、同 `.txt`、`sources/ORB_SLAM3_2007.11898v2_page-05.png`。新PDF取得なし。

未確認・範囲：実動画の到達回数や表示内容は未測定。A19の地図サイズ条件、A20/A21の処理内部へ進んでいない。コード実行・変更なし、取得障害なし。
