# D15 根拠メモ：姿勢と有効フラグのファイル

対象はローカル独自 `SaveCameraPoses`。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`、以下は同リポジトリ内の現行行番号。A23/D10/D13/D14 の根拠を再利用した。

| 論点 | 現行コードと限定 |
|---|---|
| 呼出し・地図選択 | `include/System.h:185–188`、wrapper `slam/src/offline_mono.cpp:57–63`：点保存に続いて `stem + "_poses.txt"` へ呼ぶ。`src/System.cc:1396–1414` は最大 GetAllMapPoints().size を独立に選び直す。D14同様、有効点数ではなく集合件数、strict >、同数先行保持、全0なら候補なし。二保存の同一 Map 選択を固定する共通 snapshot はない。候補なしでは履歴があっても行を出さず return。 |
| 4 list の同期走査 | `System.cc:1417–1426`：relative/reference/stamp/lost を同時に進めるが、end を検査するのは relative だけ。他も同じ長さ・対応順であることを前提にする。並替えはなく履歴順。D13 の途中 return・前値時刻複製があるため、入力動画の全画像に必ず1行、時刻が必ず増加、とはしない。 |
| valid の条件順 | `1427–1446`：まず `ok=!lost`、次に参照 null なら false。ok の場合だけ bad KF の親をたどり、親が null なら false。最後に到達した非bad KF の Map が選択 Map と異なれば false。元の参照が bad でも親連鎖を経て通過し得る。履歴への追加時に false だった lost 印は ActiveReset 等で後から変わり得る（D13）。 |
| 親連鎖と再構成 | `1429,1434–1437,1454` の parent_chain は既定構築の単位 SE3。根拠は `Thirdparty/Sophus/sophus/se3.hpp:446–448,970` の並進0と `so3.hpp:449–452` の単位回転。`KeyFrame.cc:669–673` は bad 化時、親があれば `mTcp=Tchild,w*Tparent,w^-1` を保存。GetParent は `507–510`。chain を右へ積み、履歴相対姿勢×chain×最終祖先の現在姿勢で世界→対象カメラ姿勢を構成する。 |
| 9列と精度指定 | `1448–1459`：`t tx ty tz qx qy qz qw valid`。fixed 表示で時刻は小数点以下6桁、valid=1行の並進3成分と quaternion 4成分は9桁。qx/qy/qz/qw の順で世界→カメラ回転を表す。valid=0行は時刻の後に固定文字列 `0 0 0 0 0 0 1 0`。これは無効行の埋め値で実姿勢を測定した結果ではない。ヘッダなし、sortなし。 |
| 保証しないこと | `1394,1409,1448–1462`：void、時刻/並進/quaternion の finite 検査と I/O 成否検査なし。valid は Tracking OK、実精度、数値有限性、全入力画像の有効性を証明しない。kept/total ログは条件通過数/処理履歴数で書込成功の証明でもない。A23 の Shutdown 待機コメントと D10 の共有参照取得から、全最適化完了・一括固定した出力は保証できない。 |

## 親連鎖の最小式と座標

元の参照 KF を r0、bad KF を親へたどり最初に到達する非bad祖先を rm とする（元から非badなら m=0）。各 mTcp が利用可能で、この連鎖が正常に終わる前提で、

\[
A=T_{r_0r_1}T_{r_1r_2}\cdots T_{r_{m-1}r_m},\quad A=I\ (m=0),
\qquad T_{cw}=T_{cr_0}A\,T_{r_mw},\qquad
C_w=-R_{cw}^{\mathsf T}t_{cw}.
\]

`T_ab` は座標 b→a の SE3 変換で、点へ `X_a=R_ab X_b+t_ab` と作用する。`w` は選択地図の世界、`c` は対象履歴 Frame のカメラ。`Tcr0` は保存済み相対姿勢（D13）、A は最終祖先→元参照、右端は世界→最終祖先。従って右から世界→祖先→元参照→対象カメラと適用する。各 mTcp は当該 KF の bad 化時に保存した子←親の変換であり、全祖先の現在姿勢を再差分するコードではない。

`Tcw=(Rcw,tcw)` の tcw がファイルの tx/ty/tz で、世界内のカメラ中心 Cw とは異なる。最後の式は逆変換からの整理で、実装は中心へ変換して保存していない。並進と Cw は地図の任意長さ単位、純単眼ではメートル保証なし。回転と quaternion は無次元。時刻 t は履歴の秒値で、並進記号 tcw と区別する。

仮定例：全回転が単位、Tcr0 の並進が `(1,0,0)`、bad な r0 から非bad親への mTcp が `(2,0,0)`、親の世界→カメラ姿勢が `(3,0,0)` なら、保存並進は `(6,0,0)`、カメラ中心は `(-6,0,0)`。lost=false、親の所属が選択 Map、時刻1.2秒なら行は `1.200000 6.000000000 0.000000000 0.000000000 0.000000000 0.000000000 0.000000000 1.000000000 1`。同じ時刻で判定不合格なら `1.200000 0 0 0 0 0 0 1 0`。実測・実保存ではない。

## 一次資料・PDF実読と未確認

- [固定公式 System.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/System.cc) に SaveCameraPoses がないことをオンライン再確認。D14で確認した固定 HEAD の不在と既存ローカル追加差分を再利用し、独自仕様として扱った。
- [固定公式 KeyFrame.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/KeyFrame.cc) の mTcp 保存を照合。Sophus の既定構築は同梱一次ソースを実読。
- [ORB-SLAM 原論文 v2](https://arxiv.org/pdf/1502.00956v2) PDF8頁（誌面7頁）§V-D の本文と `sources/ORB_SLAM_1502.00956v2_page-08.png` を再読。参照 KF と姿勢追跡の背景であり、独自の親連鎖保存・列・valid条件を規定する資料ではない。
- 取得障害なし。実出力、全連鎖の正常性、並行更新、有限性や I/O 失敗の挙動は未検証。O01/O03、実行、コード変更へ進んでいない。
