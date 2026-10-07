# A07 根拠メモ：初期化の成立判定

2026-10-07。純単眼MONOCULARのみ。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。コード行は`third_party/ORB_SLAM3/src/`基準。A06の方法説明とH出力懸念は[A06根拠](A06_evidence.md)を参照し、ここでは再調査しない。

| 段階・根拠 | 条件と次の動作 |
| --- | --- |
| 1 候補未準備：Tracking.cc:2451–2478 | 現在のmvKeys.size()>100ならFrameを初期候補へ保存しmbReadyToInitializate=true、return。100点以下では保存せず未準備のまま関数末尾へ。候補保存だけでmState=OKにはしない。 |
| 2 候補準備済み：同:2481–2499 | 現在特徴数<=100なら準備フラグfalseでreturn。そうでなければ対応探索し、nmatches<100もfalseでreturn。時間差>1秒の条件はIMU_MONOCULAR専用で純単眼には適用されない。falseは候補用変数のメモリ消去ではなく、次の候補取得へ戻すフラグ操作。 |
| 3 二視点復元：同:2501–2522 | ReconstructWithTwoViewsがfalseならif本体に入らず終了。ここではmInitialFrame・準備フラグ・mStateを変更しないため、候補を保持して後続画像で再試行できる。対応探索用の作業配列まで不変という意味ではない。 |
| 4 復元true後：同:2506–2519 | 対応が存在してもvbTriangulated=falseなら対応番号を−1にしnmatchesを減らす。その後姿勢を設定してCreateInitialMapMonocularへ。除外直後にもう一度nmatches<100を検査する処理はない。復元trueだけでは最終成立ではない。 |
| 5 BA後検査：同:2580–2593、KeyFrame.cc:340–364、MapPoint.cc:210–214 | `medianDepth<0 || pKFcur->TrackedMapPoints(1)<50`でResetActiveMap要求→return。TrackedMapPoints(1)は現在KeyFrameに対応する非null・非badの点のうちObservations()>=1を数える。1は最低登録観測数、50は点数であり、特徴点数100とは異なる。 |
| 6 リセット要求：System.cc:514–518,450–464 | ResetActiveMapはmutex下でmbResetActiveMap=trueにする短い要求関数。後続の単眼入力処理のresetチェックでTracking側の処理が呼ばれる。この呼出し自体はプロセス終了や全Atlas即時削除ではない。 |
| 7 最終状態：Tracking.cc:2656、1899–1915 | 地図設定の末尾まで到達するとmState=OK。Trackは初期化呼出しから戻った後、mState!=OKなら現在FrameをmLastFrameへ保存してreturn。図A07の成立判断はこの最終状態に対応する。 |
| 8 PDFとの区別：ORB-SLAM v2、PDF6–7頁＝誌面5–6頁、§IV・図3 | 本文と両ページ画像を再読。少ない対応、低視差、曖昧な復元を避け、再構成後BAする狙いを確認。式(3)のH/F得点比はモデル選択であり成立判定そのものではない。論文のH選択>0.45と現行>0.50を混同しない。本文の「手順1へ戻る」を、手元の復元false時に必ず候補解除するという意味へ転記しない。 |

境界例（説明例、未実行）：特徴点100点は候補保存不可、101点は保存条件を満たす。対応数100点は`<100`ではないので復元へ進めるが、成立は保証しない。BA後の対象地図点49点はリセット要求、50点はその点数条件を通るだけである。

一次ネット実読：[公式固定コミットTracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)。mState!=OK、nmatches<100、medianDepth条件と周辺を照合。System.ccには既存変更があるため上表はローカル行番号。

PDF：[ORB-SLAM原論文v2](https://arxiv.org/pdf/1502.00956v2)。キャッシュ`../sources/ORB_SLAM_1502.00956v2.pdf`、同txt、`ORB_SLAM_1502.00956v2_page-06.png`／`page-07.png`。版・SHAはA06記録を再利用。

未確認・限界：実動画の成立成否は未測定。深度検査は厳密には<0であり、ゼロ・NaN等の完全検査を保証しない。復元内部の全閾値一覧、リセット内部、A08以降は未調査。取得障害なし。コード変更・実行なし。
