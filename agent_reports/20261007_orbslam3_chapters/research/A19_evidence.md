# A19 現在地図を残すかの判断：根拠メモ

2026-10-07確認。純 `MONOCULAR`・通常SLAMのみ。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下は `third_party/ORB_SLAM3/` 内のローカル行番号。System.ccには既存のinclude/保存機能追加があるが、本章の対象処理は固定版と同じ。

|確認対象|結果|根拠|
|---|---|---|
|Kの実体|`pCurrentMap->KeyFramesInMap()` は `mMutexMap` を保持し、`std::set<KeyFrame*> mspKeyFrames` のsizeを返す。現在地図に登録されたKF集合の要素数であり、現在画像の特徴点数やAtlas内の地図数ではない。この関数内で幾何品質評価やisBad再検査をして数え直すわけでもない。|src/Map.cc:165–168；include/Map.h:163|
|入口LOSTの前半|前半の `else if(mState==LOST)` では `K<10` ならSystemへResetActiveMap要求、それ以外はCreateMapInAtlasを直接呼び、return。|src/Tracking.cc:2014–2031|
|途中LOSTの後半|後半の独立LOST判定では `K<=10` なら同要求後return。純単眼は続くIMU条件を通らず、それ以外はCreateMapInAtlasを直接呼びreturn。K=10だけ前半と後半で選択先が異なる。|src/Tracking.cc:2271–2288|
|要求と直接呼出し|`System::ResetActiveMap()` はmutex下で `mbResetActiveMap=true` とするだけ。この呼出し時点でTrackingの地図リセット完了を意味しない。CreateMapInAtlasは当該Track内で直接呼ばれる。各関数内部の対象・手順はA20/A21へ残す。|src/System.cc:514–518；src/Tracking.cc:2021–2024、2275–2286|
|要求の消費|次回TrackMonocularがリセット検査まで到達すれば、全体resetの `mbReset` が先に評価され、それがなければ `mbResetActiveMap` を消費してTracking::ResetActiveMapを呼びフラグを下ろす。その後GrabImageMonocularへ進む。次回入力がなければこの経路の消費も発生しない。|src/System.cc:450–471|

## 境界表

Kは判断時の非負整数（単位：KF個数）。「要求」はSystem::ResetActiveMap、「新地図側」はCreateMapInAtlasへの直接呼出しを意味する。これは実装の分岐表であり、地図の幾何学的な健全性を保証する基準ではない。

|仮定したK|入口LOST前半：K<10|途中LOST後半：K<=10|
|---|---|---|
|9|リセット要求|リセット要求|
|10|新地図側|リセット要求|
|11|新地図側|新地図側|

図の「地図を残せる?」はこの実装上の選択を説明する名称。Kが大きければ誤地図でない、という意味ではない。同じ画像で前半のelse-ifへ入り直さない制御はA18参照。両境界の差の設計意図や不具合かどうかは確認しておらず推測しない。

## 一次資料・PDF実読

- [公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)、[公式固定Map.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Map.cc)、[公式固定System.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/System.cc)：分岐、集合サイズ、要求フラグの必要箇所をオンライン一次本文で照合。
- [ORB-SLAM3論文 v2](https://arxiv.org/pdf/2007.11898v2)：PDF5頁＝誌面5頁、図1と§III Atlas/Tracking段落を本文・画像で再読。active/non-active mapの区別と追跡喪失後の新地図管理の概説を確認。現行のK=10境界差、要求フラグ消費順はその概説から導かずコードに基づく。
- キャッシュ：`sources/ORB_SLAM3_2007.11898v2.pdf`、同 `.txt`、`sources/ORB_SLAM3_2007.11898v2_page-05.png`。新PDF取得なし。

未確認・範囲：実動画でK=9/10/11の各経路を再現したわけではない。A20/A21内部の手順・状態更新・リセット対象詳細は未調査。コード実行・変更なし、取得障害なし。
