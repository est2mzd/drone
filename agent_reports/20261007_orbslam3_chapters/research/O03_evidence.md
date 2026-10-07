# O03 根拠メモ：patrol の別特徴地図と巡回研究

対象は現行 `patrol/`。D01動画・D15姿勢と校正から作る別系統の位置推定を確認した。下表の短いファイル名は patrol/ 基準。実行・飛行・ビルド・インストール・改修なし。秘密設定/認証ファイルを読まず、認証値や接続先実値を収録しない。

| 論点 | 現行コードの根拠と限定 |
|---|---|
| 入口と ORB-SLAM3 境界 | `cli.py:14–29` の build-map は video/poses/calibration/output、demo は video/poses/map/world/output-dir を受ける。`localization.py:86–128` は動画と Tcw から点を三角測量する。Atlas/MapPoint/BoWの読込みではなく、D14の点ファイルも入力に要求しない。`README.md:23` も別途作る特徴点地図と説明。 |
| 姿勢・時刻・画像の契約 | `localization.py:19–50,87–107`：Camera1.*からK/歪み、quaternionを有限性/ノルム確認して正規化、Tcwを3×4行列へ。姿勢ファイルは**全9列有限・時刻のstrict増加**をvalid選別前に要求し、重複も拒否。採用はvalid==1、約1秒以上の参照間隔、指定終了時刻より前。動画のround(t*fps)画像を読む。D15の前値時刻コピーを含む全ファイルを無条件に受け付けるインターフェースではない。 |
| 対応と3D点の生成 | `localization.py:53–83,110–121`：OpenCV ORB記述子をHammingのkNN/比率・距離で選別し、一回の照合でtrainIdxの重複を除く。参照ごとに2秒以上先の最初の相手を選び、歪み補正した正規化点＋各TcwでtriangulatePoints、同次除算後に有限・正深度・再投影・視差を選別。時間差は物理的なカメラ間距離ではない。trainIdx一意は全pair間で同じ物理点を統合した保証でもない。 |
| 保存・更新される地図 | `localization.py:120–136`：pairごとの採用xyz、最初の参照画像のdescriptor、2参照時刻を配列へ追加し、NPZにxyz/descriptors/k/d/reference_times/units=slam_units/pose_convention=Tcw/versionを保存。Localizerは配列を読み、estimateは照合と姿勢計算をする。この経路にAtlasへの反映、オンライン点追加、共視木/語彙検索DB更新はない。地図の再生成と、本体の地図更新を分ける。 |
| PnP の実経路 | `localization.py:138–160`：query ORBと保存descriptorの対応から3D–2D対を作り、solvePnPRansacに **SOLVEPNP_EPNP** を指定、返ったinlier集合で solvePnPRefineLM。対応数/推定成否/inlier数、refine後の画素RMSと正深度条件を使いvalidを返す。A15本体のMLPnPとは別。結果のpositionはC=−Rcw^T tcw、rotation_cwとrms_pxも返すが、メートル位置共分散は計算しない。 |
| 巡回への座標・尺度接続 | `runtime.py:26–44,68–87`：Alignmentはmetric/extrinsics/gimbal指定と正の尺度・回転等を検査し、SLAM座標を外部指定のメートル世界へ変換、カメラ取付offsetを引いて機体位置へ。これは自動校正でも入力フラグの実測証明でもない。`navigation.py:26–47,140–174` は別のメートル/Z-upのbox・verified_free地図を使い、位置/周囲形状の期限、valid、外部sigma等で停止/経路計画を判断する。疎な特徴点の空白から通行可能空間を生成していない。 |
| 評価と合成巡回の分離 | `demo.py:119–146,194–206` は実動画の画像をLocalizerへ渡し、近い時刻のORB姿勢との差をSLAM単位で記録。35秒の参照/評価区分は記述子用で、ORB pose graphは映像全体由来、独立真値ではない。`simulation:97–109` は合成位置・周囲形状をControllerへ渡して位置を更新する別処理。画像PnP位置で実機を閉ループ巡回した実証ではない。README既存成績は今回再測定していない。 |
| 実機出力の境界 | `runtime.py:74–87` はcapture/geometryのmonotonic時刻とsigma_mを外部から受ける。SDK軸未確認なら送信用速度は0で提案世界速度を返す。`bridge_cli.py:21–23` は合成world速度を送らずゼロを送る試験経路、Android `PatrolCommandBridge.java:21` はLIVE_OUTPUT_ENABLED=false。これらの指定やゼロ目標を物理停止・実機安全性の実証と解釈しない。全制御仕様は対象外。 |

## 最小 PnP 式と接続例

\[
u_j\simeq\pi_{K,D}(R_{cw}P_j+t_{cw}),\qquad
C_s=-R_{cw}^{\mathsf T}t_{cw},\qquad
C_w=sR_{ws}C_s+t_{ws}.
\]

Pj は別NPZの点jのSLAM座標、ujは対応するqueryの画素座標。Rcw/tcwはSLAM世界→queryカメラの回転/並進、Kは画素単位の内部パラメータ、Dは無次元の5歪み係数、πは透視除算・歪み・Kを含む画素投影。P/t/Csは任意SLAM長さ単位、回転は無次元。sは外部測定として与えるメートル/SLAM単位、RwsはSLAM世界→巡回用世界の回転、tws/Cwはメートル。最後の式はruntimeのカメラ位置段階で、機体位置にはさらに取付offset補正がある。点・姿勢・校正の整合と有効な幾何対応が前提。

仮定例：参照時刻1秒と3秒の姿勢があっても、並進や視差が十分とは限らず、時間差だけで3D点採用は決まらない。またPnPのCs=(2,0,0)という結果を2mと読み替えられない。測定済みs=0.5 m/SLAM単位、Rws=I、tws=0という別の仮定を置いたときだけ、カメラ位置Cw=(1,0,0)mとなる。実機校正値を示す例ではない。

## 一次資料・PDF実読と限界

- [OpenCV calib3d 公式](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html) のundistortPoints、triangulatePoints、solvePnPRansac/EPnP、solvePnPRefineLMを実読。P省略時の正規化点、投影行列と同次点、3D–2Dからの外部姿勢、初期姿勢からのrefineというAPIの意味を確認。実環境のOpenCV版/実測結果は今回確認していない。
- [ORB-SLAM 原論文 v2](https://arxiv.org/pdf/1502.00956v2) PDF8頁（誌面7頁）§V-Cおよび§VI-Cを、既読キャッシュ本文と `sources/ORB_SLAM_1502.00956v2_page-08.png` で再読。対応からのPnP、三角測量と幾何選別の背景として用い、patrolをORB-SLAM3内部実装と同一視しない。
- `README.md:7,23–29,37–39,95` の未達・尺度・独立真値でないという限定を、現行localization/runtime/demoの接続と照合。実機飛行、精度・共分散・全遅延、実寸障害物自動生成は本調査で実証していない。取得障害なし。O04へ進んでいない。
