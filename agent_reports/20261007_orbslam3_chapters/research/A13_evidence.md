# A13 姿勢を得てキーフレームを選ぶ：根拠メモ

2026-10-07確認。対象：現行ラッパーの純 `MONOCULAR`、通常SLAM、PinHole・第2カメラなし。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下の行番号は `third_party/ORB_SLAM3/src/` 内のローカルソース。Tracking/KeyFrame/LocalMappingは固定版から未変更。

|項目|確認結果|根拠|
|---|---|---|
|追跡後の呼出し|`bOK || mState==RECENTLY_LOST` のブロックでNeedNewKeyFrameを評価。純単眼でCreateNewKeyFrameを呼ぶのは `bNeedKF && bOK`。失敗中のKF挿入を許す追加条件はIMU用。初期2KFはCreateInitialMapMonocularの別経路。|Tracking.cc:2205、2244–2250、2526–2530、2623–2624|
|早期抑止|通常SLAMでもmapper停止中または停止要求中ならfalse。さらに `currentId<lastRelocId+mMaxFrames && nKFs>mMaxFrames` ならfalse。画像ID比較であり、再局在後は常に一定秒数禁止という条件ではない。|Tracking.cc:3076–3094|
|比較する点数|`nRefMatches=referenceKF->TrackedMapPoints(nMinObs)`。`nMinObs` は地図KF数が2以下なら2、それ以外3。参照KFの対応スロット中、非null・非bad・Observations以上の条件を満たす数。現在側はA11の `mnMatchesInliers`。参照の全ORB特徴数ではない。|Tracking.cc:3096–3100；KeyFrame.cc:340–364|
|純単眼の候補条件|深度近傍点条件はfalse、c1c/c3/c4もfalse。現行設定の比率は0.9（MONOCULARで上書き、第2カメラなし）。画像間隔のc1aまたは受付フラグを含むc1bと、`n<0.9*nRef && n>15` の両方が必要。`mMinFrames=0`、`mMaxFrames` は設定FPS由来。|Tracking.cc:49、561–564、584–585、3105–3162、3166–3187|
|受付と忙しい場合|候補条件成立後、保存済み受付フラグまたはIsInitializingがtrueならNeed=true。双方falseならInterruptBAを要求し、純単眼はfalse。非単眼用のキュー件数条件は通らない。AcceptKeyFramesはbool受付フラグの取得で、処理待機中・キュー空の厳密保証ではない。|Tracking.cc:3103、3187–3213；LocalMapping.cc:873–882、897–900|
|生成側でも中止可能|Need=trueでも、`IsInitializing && !Atlas.isImuInitialized`、または `SetNotStop(true)` 失敗ならCreateは早期return。後者はmapperが停止済みの場合にfalse。従ってNeedは生成完了の保証ではない。|Tracking.cc:3216–3224；LocalMapping.cc:885–894|
|FrameからKFへ|生成コンストラクタはFrame ID・画像時刻・特徴・記述子・既存MapPoint参照を受け、姿勢をSetPoseする。参照KFを更新し前後KFを接続。純単眼は深度から新MapPointを作る枝を通らない。Frameの外れ値対応除去よりKF生成が先なので「inlierだけを渡す」とは書かない。|KeyFrame.cc:45–62、93；Tracking.cc:3224–3236、3247、2248–2266|
|キュー受渡し|InsertKeyFrameでmutex下のリストへpush_backしBA中断要求フラグを立てる。呼出し後SetNotStop解除、最後のKF ID・ポインタ更新。ここは非同期処理への受渡しで、LocalMappingの地図更新・最適化完了ではない。|Tracking.cc:3335–3340；LocalMapping.cc:284–288|

## 純単眼の簡約条件（コードの整理）

`i=currentFrameId`、`l=lastKeyFrameId`、`r=lastRelocFrameId`（画像ID）、`M=mMaxFrames`、`m=mMinFrames=0`（画像数）、`K=nKFs`（KF数）、`n=mnMatchesInliers`、`q=nRefMatches`（対応スロット数）とする。`a` は取得した受付bool、`j` はIsInitializingのbool。現行設定ではM=30（mini3.yaml:22）、Capture側FPSとは別の設定値。比率0.9は無次元。

1. 停止中/停止要求中、または `(i<r+M && K>M)` ならfalse。
2. 候補 `C=((i>=l+M) || (i>=l+m && a)) && (n<0.9*q) && (n>15)`。
3. `C` がfalseならfalse。trueなら `a || j` によりtrueを返し、双方falseならBA中断要求を出してfalse。

これは逐次読出しを整理したもので、非同期フラグの一括スナップショットを保証する式ではない。境界は画像間隔が `>=`、点数が厳密に `<0.9q` と `>15`。nとqは異なる条件で数えるため、比を二画像共通点の厳密な重複率とは解釈しない。最大間隔条件がtrueでも点数条件が必要で、一定周期の採用は保証されない。Createの追加抑止は上表のとおり。

図A07→A13は初期2KFと姿勢が得られた結果の接続として扱う。Trackは `NOT_INITIALIZED` のif側で初期化し、同一呼出しで1923行のelse側へ入り直さない。通常の追加KF判定は初期化済み側の経路であり、初期化成功直後に同じ画像へNeedNewKeyFrameを重ねて適用する説明にはしない（Tracking.cc:1899–1923、初期2KFは上表/A06）。

## 一次資料・旧論文との区別

- [公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc) と [公式固定LocalMapping.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/LocalMapping.cc)：Need/Create、Insert/Accept/SetNotStopの必要箇所をネット本文で照合。
- [ORB-SLAM原論文 v2](https://arxiv.org/pdf/1502.00956v2)、PDF8頁＝誌面7頁、V.E “New Keyframe Decision”を本文と画像で実読。左段下から右段上へ続く。旧論文は再局在後20画像超、mapper idleまたは前KFから20画像超、現在50点以上、参照の90%未満という方針を説明する。現行は設定由来M、KF数付き早期抑止、`>15`、忙しい純単眼では中断要求後false等の差があるため、旧閾値を現行判定として転記しない。
- キャッシュ：`sources/ORB_SLAM_1502.00956v2.pdf`、同 `.txt`、`sources/ORB_SLAM_1502.00956v2_page-08.png`。新PDF不要、取得障害なし。

未確認：実動画での選択頻度・スレッド競合タイミングは未測定。LocalMappingのキュー消費後の内部処理、A14以降へは進めていない。コード実行・変更なし。
