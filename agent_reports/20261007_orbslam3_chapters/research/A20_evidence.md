# A20 既存地図を残す新地図開始：根拠メモ

2026-10-07確認。manifest接続はA19→A20→D10,A22。純MONOCULAR・通常SLAMを対象とする。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。対象Tracking/Atlas/Map/Frameに固定版との差分なし。行番号は `third_party/ORB_SLAM3/` 内。

|項目|具体処理・限定|根拠|
|---|---|---|
|旧Map保持とcurrent切替|Atlas mutex下で旧currentにSetStoredMapを呼び、新しいMapをnewしてcurrentに設定、AtlasのMap集合へinsertする。この関数は旧Mapを集合からerase/deleteしない。SetStoredMap/SetCurrentMapは `mIsInUse=false/true` の代入で、ファイルへの保存ではない。|src/Atlas.cc:58–77；src/Map.cc:204–211|
|新Mapの器とID|new Mapは既存のKF/点を複写せず、新たな集合を持つ。Map IDは `nNextId++`。Atlasの初期KF ID用値は旧Map最大KF IDとの条件付き比較で更新し、その値をコンストラクタへ渡す。必ず毎回「旧最大+1」と断定せず63行の条件を伴う。地図の器作成だけでは二視点初期化や新規点群生成は完了しない。|src/Atlas.cc:63–76；src/Map.cc:36–42；include/Map.h:162–163|
|状態・画像IDの再準備|現Frame IDをmnLastInitFrameIdに保存してCreateNewMapを呼び、`mnInitialFrameId=currentFrameId+1`、`mState=NO_IMAGES_YET`。Frame/KeyFrameの全体採番カウンタを0へ戻す処理はこの関数内にない。`mnLastRelocFrameId` の代入はコメントアウトされ、実行されない。|src/Tracking.cc:2662–2676|
|有効性と初期化準備|`mbSetInit=false`、`mbVelocity=false`、`mbVO=false`、純単眼では `mbReadyToInitializate=false`。mVelocityのSE3値をゼロ/単位変換に代入する処理ではなく、利用可能性を示すフラグの解除。IMU専用の再準備枝は純単眼で通らない。|src/Tracking.cc:2666–2687|
|Frame・参照・対応の再準備|`mpLastKeyFrame` と `mpReferenceKF` をnull化、mLastFrame/mCurrentFrameを `Frame()` に置換、`mvIniMatches.clear()`、`mbCreatedMap=true`。Frame既定コンストラクタは姿勢/速度等の有効フラグをfalseにする。「全フィールドを数値0に初期化」とは解釈しない。姿勢履歴リストをclearする処理もこの関数内にはない。|src/Tracking.cc:2689–2699；src/Frame.cc:45–48|
|この呼出しの保証範囲|Tracking→Atlasの直接呼出しで新Mapを作る。一連の関数にはLocalMapping/LoopClosingの停止・終了待ち、地図間対応探索、座標変換推定や地図融合の呼出しがない。旧Mapを保持することを、非同期処理から今後変更されない保証や座標統合済みという意味にはしない。|src/Tracking.cc:2662–2700；src/Atlas.cc:58–77；論文図1/§III|

## 集合・座標の最小整理

作成直前のAtlas内Map集合を `A`、旧currentを `M_old∈A`、新規Mapを `M_new` とする。この作成処理による変化は `A'=A∪{M_new}`、`current'=M_new`、旧MapはA'に残る。新MapのKF集合K_newと地図点集合P_newは作成時には空。これは当該呼出しの効果を整理した式で、並行処理を含むAtlasの将来状態を固定する式ではない。

```text
Atlas: { ... M_old [current] } -> { ... M_old [stored], M_new [current] }
Tracking: NO_IMAGES_YET / mbVelocity=false / 初期化候補の準備解除
```

地図が後に構築された場合も、`X_old` と `X_new` は別の地図座標系の3次元座標。単眼地図どうしを共通座標に表すには一般に `X_old=s R X_new+t` のような尺度を含む関係が必要となるが、CreateNewMapはs,R,tを推定・適用しない。Rは3×3回転で無次元、sは尺度比で無次元、tは旧Mapと同じ任意長さ単位、Xは各Mapの任意長さ単位。これは未整合を説明する一般形であり、この章で統合算法や論文式を実装したとの意味ではない。

## 一次資料・PDF実読

- [公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)、[公式固定Atlas.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Atlas.cc)：両作成関数の必要部分をネット一次本文で照合。
- [ORB-SLAM3論文 v2](https://arxiv.org/pdf/2007.11898v2)：PDF5頁＝誌面5頁、図1、§III Atlas/Trackingを本文・画像で再読。Atlasは非接続地図の集合、active/non-activeを区別する概説と、追跡喪失後の新しいactive map開始を確認。図1のMap Mergingは独立した構成要素であり、Map作成と同一操作ではない。旧地図保持の具体的実装は上表が根拠。
- 実読キャッシュ：`sources/ORB_SLAM3_2007.11898v2.pdf`、同 `.txt`、`sources/ORB_SLAM3_2007.11898v2_page-05.png`。新PDF取得なし。

未確認・範囲：非同期処理の実行タイミング、旧地図の以後の変更、再初期化の成否は未測定。A21リセット内部、A22次画像の初期化経路には進んでいない。コード実行・変更なし、取得障害なし。
