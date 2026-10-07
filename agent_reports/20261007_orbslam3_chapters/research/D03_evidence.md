# D03 根拠メモ：カメラ校正と座標の前提

対象は現在の純単眼、`File.version: "1.0"` / `PinHole`。外側 HEAD `d1265bc35439dd6ca57687ac93c8b3a7310fc681`、ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下はローカル行番号。コード・校正・動画は実行していない。

| # | 確認事項 | 根拠・適用範囲 |
|---|---|---|
| 1 | 現行入力は `mini3_calib/out/mini3.yaml`。`fx=895.475604, fy=894.667309, cx=641.024514, cy=359.282471`、1280×720、`Camera.RGB=0`。旧 README の733系数値を採用しない。 | `scripts/orb_slam3/run.sh:12–13,31–35`、YAML `3–23`。歪み係数は `k1=.11208777, k2=-.28496497, k3=.28816471, p1=.00023454, p2=.00024400`。画像の実寸との適合を今回実測していない。 |
| 2 | 校正は平面上の非対称円中心を mm で作り、検出した2D中心との対応から `cv2.calibrateCamera` を呼ぶ。校正入力内の寸法不一致は拒否する。 | `mini3_calib/pattern.py:23–29`、`calibrate.py:165–168,178–189,202–210`。物体座標は `((2col+row%2)spacing_mm,row spacing_mm,0)`。`_rvecs/_tvecs` はYAMLへ保存しない。mmのパターン使用が単眼地図をmm尺度にする経路ではない。 |
| 3 | 1.0形式では `Settings` が `Camera1.*` を読む。Pinhole本体のパラメータは4内参、歪みは別ベクトル `[k1,k2,p1,p2,k3]`。 | `System.cc:82–84`、`Settings.cc:184–224`、`Tracking.cc:535–559`。`Settings.cc:356–394` は元寸法と任意の新寸法に応じ内参を調整するが、現行YAMLは新寸法指定なし。`System.cc:419–424` は必要時のみresize。 |
| 4 | `Camera.RGB=0` は3/4チャネル入力をBGR/BGRAとしてグレー化する指定。 | `Settings.cc:411` → `Tracking.cc:586,1568–1581`。`calibrate.py:23` の「0はグレー」コメントだけでは意味が不十分。1チャネルならこの変換枝を通らない。入力の現物色順は未検査。 |
| 5 | グレー画像で特徴抽出した後、特徴点座標だけを歪み補正する。`mvKeysUn` は補正後の画素座標。 | `Frame.cc:311,323,747–779`。`undistortPoints(...,R=空,P=mK)` は全画像の補正ではない。`Frame.cc:749` は **k1だけ** が0ならskipする条件で、現行k1は非零。[OpenCV undistortPoints](https://docs.opencv.org/4.6.0/d9/d0c/group__calib3d.html) のAPI説明・P指定式を実読。 |
| 6 | Pinhole投影は `fx X/Z+cx, fy Y/Z+cy`、unprojectは `((u-cx)/fx,(v-cy)/fy,1)`。後者は通常ノルム1ではなく、奥行きを決定しない。 | `src/CameraModels/Pinhole.cpp:30–47,61–68`。[ORB-SLAM3論文](https://arxiv.org/pdf/2007.11898v2) PDF6頁=誌面6頁 §IV・IV-A は投影/逆投影の抽象化と画素から視線への変換を説明。キャッシュ本文と `sources/ORB_SLAM3_2007.11898v2_page-06.png` を実読。 |
| 7 | YAMLの `RMS 0.5524 px` は既存保存コメント。校正で検出した中心とモデルによる投影の残差を集約した指標。地図誤差、別の撮影条件での精度、単眼実尺度の保証ではない。 | YAML `7–8`、`calibrate.py:94–121,202–211`。[OpenCV calibrateCamera](https://docs.opencv.org/4.6.0/d9/d0c/group__calib3d.html) の戻り値・再投影誤差最小化説明を実読。再校正・残差分布・実撮影条件の照合は未実施。 |

採用式の最小根拠（原論文の式番号ではなく、現行5係数設定とOpenCVモデルの整理）：

\[
K=\begin{bmatrix}f_x&0&c_x\\0&f_y&c_y\\0&0&1\end{bmatrix},\quad
x=X/Z,\quad y=Y/Z,\quad
(u_u,v_u)=(f_xx+c_x,f_yy+c_y).
\]

\[
r^2=x^2+y^2,\quad a=1+k_1r^2+k_2r^4+k_3r^6,
\]
\[
x_d=xa+2p_1xy+p_2(r^2+2x^2),\quad
y_d=ya+p_1(r^2+2y^2)+2p_2xy,
\quad (u_d,v_d)=(f_xx_d+c_x,f_yy_d+c_y).
\]

\[
q=K^{-1}[u_u,v_u,1]^T=(x,y,1)^T,\qquad P_c=Zq.
\]

`P_c=(X,Y,Z)^T` はカメラ座標の点、可視な前方点の説明では `Z>0` を仮定（`Pinhole::project` 単体が正深度を検査するという意味ではない）。X,Y,Zは同じ長さ単位だが単眼地図では実単位未確定。`u_d,v_d` は歪みあり、`u_u,v_u` は補正後の画素座標、f/cもpixel。x,y,xd,yd,r,aと5係数は無次元。qはz成分を1とした視線で単位ベクトルではなく、未知のZが残る。OpenCVの逆歪み処理は反復近似で、FrameがP=Kを渡すため結果を画素へ戻す。その後に上の逆Kで正規化する。式出典は上記OpenCVページのpinhole/歪み/undistortPoints節とPinhole実装。

障害なし。D04以降は未調査。設定値の妥当性・動画の寸法/色順・現在の光学条件への適合・RMS再現性は今回の静的調査から保証しない。
