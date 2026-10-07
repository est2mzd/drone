# D13 根拠メモ：Tracking の姿勢履歴

純 MONOCULAR 通常 SLAM。固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`、行番号は `third_party/ORB_SLAM3/` 基準。D08/A18/A20/A21 の必要根拠を再利用した。

| 論点 | 現行コードと限定 |
|---|---|
| 4つの並列 list | `include/Tracking.h:152–155`：`mlRelativeFramePoses` は `list<Sophus::SE3f>`、`mlpReferences` は `list<KeyFrame*>`、`mlFrameTimes` は `list<double>`、`mlbLost` は `list<bool>`。同じ追記順の相対姿勢・参照 KF・秒時刻・lost 印を論理上一組として扱うが、別々の list であり一括更新される atomic record ではない。各要素に入力 Frame ID や Map ID を直接保存する形式でもない。 |
| 姿勢を持つ場合の追記 | `Tracking.cc:2300–2309`：末尾まで到達し状態が OK または RECENTLY_LOST の場合だけ処理する。`isSet()` が true なら、現在姿勢×参照 KF 姿勢の逆を保存し、参照ポインタと現在画像時刻も追加する。`Frame.cc:427–436` の isSet は `mbIsSet` を返し、SetPose はこれと `mbHasPose` をともに true にする。姿勢設定済みと Tracking OK は別。追加時の `mState==LOST` は外側条件の下で false なので、RECENTLY_LOST を true と記録するコードではない。 |
| 姿勢未設定の else | `Tracking.cc:2311–2317`：相対姿勢、参照 KF に加えて**時刻も**各リストの back を複製する。現在画像時刻への置換ではない。lost 印は同じく false。前値が存在する前提のコード上の操作として説明し、この枝の実動画での到達率や空リストの安全性は本章では検証しない。 |
| 全入力が一履歴になるとは限らない | 初期化未成立の `Tracking.cc:1912–1915`、後半 LOST の `2271–2288` などは末尾前に return する。wrapper `slam/src/offline_mono.cpp:45–54` の読込画像数、状態2の件数、履歴追記数は別。TrackMonocular の返却 SE3 を wrapper が毎回リスト保存しているわけでもない。 |
| 参照 KF の現在姿勢から再構成 | `Tracking.cc:2781–2789` の UpdateLastFrame は履歴末尾の相対姿勢と前 Frame の参照 KF の現在姿勢を合成する。運動モデル経路2860行から呼ばれる。参照 KF の姿勢更新に応じて再構成値が変わり得るが、過去画像の真値を保証する操作ではない。 |
| リセット・新 Map との関係 | 全体 Reset は `Tracking.cc:3823–3826` で4リストを clear。ActiveReset は `3881–3912` で lost リストを再構成し、残す要素は旧値、境界以後は true とする。判定 index は mnFirstFrameId と残る Map の lowerKFID から設定し要素ごとに増やすため、各記録の実 Frame ID/所属 Map を直接選別する説明にはしない。他の3履歴はここで clear しない。CreateMapInAtlas `2661–2700` も全履歴 clear は行わない（A20/A21）。 |

## 相対姿勢と再構成（コードの整理式）

\[
T_{cr}=T_{cw}T_{rw}^{-1},\qquad
\widehat T_{cw}=T_{cr}T_{rw}^{\mathrm{now}}.
\]

`T_ab∈SE(3)` は座標 b→a の剛体変換（点に `R_ab X_b+t_ab` と作用）。`w` は所属地図の世界座標、`c` は対象 Frame のカメラ、`r` は参照 KF のカメラ。`Tcw`/`Trw` は世界→各カメラ、逆 `Trw^-1` は参照カメラ→世界、したがって `Tcr` は参照カメラ→対象カメラ。右側の変換から適用する。回転は無次元、並進は同じ地図の任意長さ単位で、純単眼ではメートルを保証しない。型 `SE3f` は単精度浮動小数点の姿勢であり時刻ではない。

第1式は2305行、第2式は2783–2786行の前 Frame を一般記号 c で表したもの。利用可能な参照 KF と保存相対姿勢を使う前提で、`now` は読取り時の姿勢、ハットは再構成値。参照が無効化された場合の親連鎖や出力ファイルへの変換は D15 に残す。

## 3入力の仮定例

有限正値 `f=30`、入力順 k の時刻 `t_k=k/f` 秒とし、下記の枝を通ったと**仮定**する。実動画での到達性を再現した例ではない。

| 入力 | 仮定した状態・分岐 | 追加履歴と累計 |
|---|---|---|
| k=0、t=0 | 初期化未成立で1915行 return | 追加なし、履歴0 |
| k=1、t=1/30 | OK、末尾到達、isSet=true | `(Tcr,参照KF,1/30,false)`、履歴1 |
| k=2、t=2/30 | 小地図（KF数10以下）で初期姿勢推定が失敗し1959–1975行で LOST、2276行 return | 追加なし、履歴1 |

この条件表では入力3件、wrapper の OK 計数1件、履歴1件で時刻列は `[1/30]` 秒。末尾 else の別条件例として、既存 back の時刻が1/30秒の状態で OK/RECENTLY_LOST かつ isSet=false の枝に到達したと仮定すると、入力時刻が2/30秒でも追加時刻は1/30秒となる。lost 印は前値のコピーではなく、その場の比較結果 false。追加後に ActiveReset が lost 印を書き換える場合は別段階。

## 一次資料・実読範囲と限界

- [固定公式 Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc) の末尾履歴追加・途中 return・UpdateLastFrame をオンライン照合。現行4リストと各分岐の仕様は論文から補わずコードを根拠とする。
- [ORB-SLAM 原論文 v2](https://arxiv.org/pdf/1502.00956v2) PDF8頁（誌面7頁）§V-D をキャッシュ本文と `sources/ORB_SLAM_1502.00956v2_page-08.png` で再読。Tracking の局所地図と参照 KF の役割を確認。この段落は現行履歴の lost 値・時刻複製・reset 仕様を定める資料ではない。
- 取得障害なし。コード/動画実行・変更なし。履歴の実件数・else到達率・全reset経路・保存列・親連鎖は追加調査していない。
