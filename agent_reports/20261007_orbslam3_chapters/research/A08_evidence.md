# A08 根拠メモ：追跡状態による分岐

2026-10-07。対象は初期化分岐を通らなかった純単眼・通常SLAMの入口状態。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。表の略記Tracking/Systemは`third_party/ORB_SLAM3/src/`以下。

| 根拠 | 分岐・意味 |
| --- | --- |
| `slam/src/offline_mono.cpp:16–68`、Tracking:44–47,1923–1939、System:426–446 | wrapperはMONOCULARでSystemを作り、TrackMonocular後に状態を読む。全文にモード変更呼出しなし。mbOnlyTracking初期値はfalseなので本章は`!mbOnlyTracking`経路。これは地図更新を伴う通常SLAMか、位置推定専用かを区別するbool。mStateは画像をまたぐ状態enum、bOKは各追跡処理の戻り値を受けて更新する局所boolで、互いに別物。 |
| Tracking:1939–1977 | 入口OKではCheckReplacedInLastFrameの後、TrackReferenceKeyFrameまたはTrackWithMotionModelを呼ぶ。後者失敗時はTrackReferenceKeyFrameへフォールバックする。純単眼でこの初期追跡が失敗すると、地図の状況に応じRECENTLY_LOSTまたはLOSTへ変更する。各呼出しの算法は次章以降。 |
| Tracking:1978–2013 | 入口RECENTLY_LOSTの純単眼経路は`bOK=Relocalization()`。失敗が続き所定時間を超える場合はLOSTへ変更する。IMU予測分岐は対象外。ここでbOK=trueでも後のTrackLocalMapの結果が最終状態に関わるため、再局在関数の成功と当該画像処理の最終OKを同一視しない。 |
| Tracking:2014–2031 | 入口LOSTでは、地図の状況に応じResetActiveMap要求またはCreateMapInAtlasを実行してreturn。通常SLAMではこの入口から直接Relocalizationは呼ばない。別モード`mbOnlyTracking=true`のLOST→Relocalization（2036–2044）を本構成へ混ぜない。 |
| Tracking:1959–1979,2006–2014,2122–2162,2270–2288 | 同じif/else構造の実行中にmStateを書き換えても、選ばなかった前半elseへ入り直さない。一方、後続の独立した判定は変更後の状態を読む。bOKがtrueならTrackLocalMapへ進み、その結果でmStateを更新。後半には独立したLOST処理もあり、同一画像中のリセット要求／新地図作成に到達し得る。 |

整理する写像：分岐到達時の状態s∈{OK,RECENTLY_LOST,LOST}に対し、通常SLAM・純単眼では `f(s)={通常追跡の呼出し群, Relocalization, リセット要求または新地図作成}`。sは単位のない列挙ラベルであり、fは処理経路への写像。この表は入口の説明で、次状態を一意に返す遷移表ではない。例：入口OKで失敗してRECENTLY_LOSTになっても、その画像で前半のRelocalization分岐を再実行する構造ではない。

一次ネット実読：[公式固定コミットTracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)。OK/RECENTLY_LOST/LOST分岐と後続状態更新を照合。Web正規化行と上表のローカル行は異なる。Systemには既存変更があるためローカル行で記録。

PDF再読：[ORB-SLAM3 v2](https://arxiv.org/pdf/2007.11898v2)、PDF5頁＝紙面5、図1・III節Tracking段落。本文と既存`../sources/ORB_SLAM3_2007.11898v2_page-05.png`を実読。図の初期姿勢推定は直前フレーム／再局在／地図作成を含み、本文は喪失後の再局在と新しいactive mapを概説する。これはenumの厳密な分岐表ではなく、現行のLOST入口へ再局在を機械的に割り当てる根拠にはしない。

未確認・範囲：実動画の状態履歴は未測定。個別追跡・再局在算法、喪失時間や地図点数等の詳細条件、地図リセット内部は後章へ残す。取得障害なし。コード変更・実行・A09以降の先行なし。
