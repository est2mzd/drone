# D08 根拠メモ：各画像の姿勢と状態

図DFDの接続は `P01/A13 → D13; 次画像予測`（manifest D08確認済み）。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下は `third_party/ORB_SLAM3/` 以下のローカル行番号。D06/A09/A18/A23を再利用。

| # | 確認事項 | 根拠 |
|---|---|---|
| 1 | 通常の呼出し完了経路ではGrabがFrame姿勢を返し、SystemはそれをTcwとして返す。同時にTracking状態を別のメンバーへ転記する。返却SE3値にはHasPoseやOK状態は含まれない。 | `Tracking.cc:1612–1614`、`System.cc:471–478`。`System.cc:473` のmutex下で `mTrackingState=mpTracker->mState`。`GetTrackingState:1326–1329` はmutex下でこの状態値を返す。 |
| 2 | Frameの姿勢設定済みと、追跡の受理状態は別情報。 | `Frame.h:144–158,169–174` は姿勢値とbool `mbHasPose`。`Frame.cc:431–436` のSetPoseは値を設定し `mbIsSet/mbHasPose=true` にする。`Tracking.cc:2739–2745` のように評価前の初期姿勢も設定される。状態列挙は `Tracking.h:120–131`、OK=2、RECENTLY_LOST=3、LOST=4。 |
| 3 | Tcwは世界→カメラ変換で、並進tcw自体は世界座標のカメラ位置ではない。 | `Frame.cc:472–478` がTcwの逆変換Twcから `mRwc` とカメラ中心 `mOw` を取得。A09の座標整理を再利用。下記のCw式はこのSE3逆変換の整理式。姿勢を設定してあることと幾何推定の正しさを区別する。 |
| 4 | wrapperは返却Tcwを保持せず、状態が2の呼出しだけtrackedを増やす。 | `slam/src/offline_mono.cpp:12,45–54`。`TrackMonocular(frame,timestamp);` の戻り値は未使用。入力画像数frame_index、OK件数tracked、姿勢/履歴数は別の計数である。 |
| 5 | 入力画像ごとに必ず履歴が1件増える構造ではない。履歴も返却Tcwの無条件コピーではない。 | `Tracking.cc:2271–2288` には履歴部に届かないreturn。到達しても `2300` はOK/RECENTLY_LOSTのみ。`2303–2317` はisSetなら参照KFに対する相対姿勢・参照・時刻を追加し、elseは前の履歴値をコピーする。終了時の姿勢exportは内部履歴側を用い、wrapperが返却Tcwをそのまま保存する処理ではない（A23参照）。全履歴/保存列はD13以降へ残す。 |

最小整理式：

\[
X_c=R_{cw}X_w+t_{cw},\qquad
T_{cw}=\begin{bmatrix}R_{cw}&t_{cw}\\0&1\end{bmatrix},\qquad
C_w=-R_{cw}^{T}t_{cw}.
\]

`X_w,X_c∈R^3` は同じ3D点の世界座標・カメラ座標、`R_cw∈SO(3)` は世界からカメラへの3×3回転、`t_cw∈R^3` はその並進、`T_cw∈SE(3)` は同次4×4表現、`C_w∈R^3` はカメラ原点を世界座標で表した位置。回転は `R^TR=I, detR=1` の正規直交を仮定する。回転は無次元、X/t/Cは同じ長さ単位だが純単眼では地図の任意尺度であり自動的にmではない。Cはカメラ原点なので `0=R_cw C_w+t_cw` から上式を得る。

仮定例：`R_cw=I, t_cw=(-2,0,0)^T` なら `C_w=(2,0,0)^T`。数値2は任意地図単位で、2mの計測を表さない。仮にこのTcwをSetPoseした時点でHasPose=trueでも、後続対応の受理やTracking OKまで保証しない。

固定公式必要箇所を実読：[System.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/System.cc)、[Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)、[Frame.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Frame.cc)。[ORB-SLAM3 v2](https://arxiv.org/pdf/2007.11898v2) PDF5頁=誌面5頁 図1/§IIIと [旧ORB-SLAM v2](https://arxiv.org/pdf/1502.00956v2) PDF7頁=誌面6頁 §V/§V-Bの必要本文・キャッシュ画像を実読。論文は画像ごとの姿勢推定と前画像からの予測の位置付けを確認する資料で、返却型/状態値/履歴条件はコード根拠。

限定：SystemのShutdown後は `409–410` で状態転記前に既定SE3を返すが、正常wrapperはShutdown後にTrackを呼ばない（A23）。姿勢精度、入力数と実保存行数、状態遷移の実動画観測は未検証。取得障害なし。コード変更・アプリ実行・D09先行なし。
