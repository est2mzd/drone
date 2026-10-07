# A22 再初期化への復帰：根拠メモ

2026-10-07確認。manifest接続：A20/A21→合流点A→A05/A06。純MONOCULAR・通常SLAM。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下のTracking/System行番号は `third_party/ORB_SLAM3/src/` 内。

|段階|確認結果|根拠|
|---|---|---|
|A20の時点|喪失画像のTrack内でCreateMapInAtlasを直接呼び、NO_IMAGES_YETと単眼初期化候補未準備を設定して戻る。呼出し元はreturnするので、その同じTrack中に最初の初期化状態分岐へ戻らない。次の入力画像から共通経路へ。|Tracking:2662–2680、2024–2031／2286–2288；A20|
|A21の時点|喪失画像ではSystemへの要求を設定。次回TrackMonocularが要求検査へ到達し、全体reset優先がなければTracking::ResetActiveMapを処理してNO_IMAGES_YET・候補未準備へ。その後、同じTrackMonocular呼出しの入力画像をGrabImageMonocularへ渡す。さらにもう一画像を待ってから処理する構造ではない。|System:450–471、514–518；Tracking:3877–3879；A21|
|入力からFrame構築|wrapperはread成功ごとに画像とk/f時刻を渡し、frame_indexを増やす。再初期化のための巻戻しや番号リセットは行わない。GrabImageMonocularはNO_IMAGES_YET/NOT_INITIALIZEDで初期化用抽出器を使ってFrameを構築し、NO_IMAGES_YETならt0を入力時刻へ設定、その後Trackを呼ぶ。|slam/src/offline_mono.cpp:42–55；Tracking:1584–1589、1601–1612|
|共通の状態遷移|Trackは現在Mapを取得し、NO_IMAGES_YETならNOT_INITIALIZEDへ変更。NOT_INITIALIZEDの純単眼枝はMonocularInitializationを呼ぶ。Map容器が存在するだけでは状態OKや初期地図の幾何成立を意味しない。|Tracking:1812、1862–1865、1899–1907；A05/A06|
|候補から再試行|両経路でmbReadyToInitializate=false。最初の再入力は特徴>100なら候補Frameと対応探索準備を保存し、ready=trueにしてreturn。<=100なら未準備のまま。この最初の一画像で二視点初期化が完了する構造ではない。Trackは状態がOKでなければmLastFrameを更新してreturnし、入力が続く場合に後の画像で再試行する。成立条件の詳細はA06/A07へ。|Tracking:2451–2478、1899–1915；候補解除時再試行もA07|

時点を分けた整理：喪失画像をI_kとすると、A20はI_kのTrack中にNO_IMAGES_YETとなり、次のread成功画像I_(k+1)が初期化候補の対象。A21はI_kで要求し、I_(k+1)のTrackMonocular内でリセットしてから、同じI_(k+1)をFrameにする。kはwrapperの処理画像番号（整数）でありMap IDではない。どちらも画像入力が続き、対象処理まで進むことが前提。EOF/read失敗ならこの再入力経路には進まない。

状態の整理は `NO_IMAGES_YET → NOT_INITIALIZED → 初期化候補の準備・後続画像での試行`。OKへの移行は初期化成立時だけで、候補保存やMap容器の準備を成立と呼ばない。これはコードの状態制御をまとめたもので論文式ではない。A20は新Map、A21はclearした同一Mapという違いはA20/A21根拠を参照し、ここで再調査しない。

## 一次資料・PDF実読

- [公式固定Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)：Frame構築→Track、NO_IMAGES_YET→NOT_INITIALIZED、初期化呼出しと未成立returnをネット一次本文でも照合。Systemの要求消費位置はローカルとA19/A21根拠を再利用。
- [ORB-SLAM3論文 v2](https://arxiv.org/pdf/2007.11898v2)：PDF5頁＝誌面5頁、図1と§III Atlas/Tracking段落を本文・画像で再読。新しいactive mapを初めから初期化する概説、Tracking内のMap creation、Atlas容器を確認。現行の要求消費時点、enum遷移、一画像目の候補保存はコード根拠と区別する。
- キャッシュ：`sources/ORB_SLAM3_2007.11898v2.pdf`、同 `.txt`、`sources/ORB_SLAM3_2007.11898v2_page-05.png`。新PDF取得なし。

未確認・範囲：再初期化の所要画像数・時間・成否は実動画で未測定。A23へは進んでいない。コード実行・変更なし、取得障害なし。
