# D02 根拠メモ：FPSと時間基準

図位置は動画の FPS、接続は `動画情報 → A03,D05`。外側 HEAD `d1265bc35439dd6ca57687ac93c8b3a7310fc681`、ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。現行 wrapper と設定読込の静的確認のみ。

| 確認事項 | 根拠と限定 |
|---|---|
| 動画側 FPS の採用 | `slam/src/offline_mono.cpp:33–37` は CAP_PROP_FPS を double fps に取得し、比較 `fps<1.0` が true の場合だけ30へ置換する。それ以外は取得値をそのまま使う。0・負値・1未満の有限値は置換されるが、有限性を検査して不適切な値全般を除くコードではない。NaN や正の無限大を明示的に排除しない。実際にそれらが返ったという実測ではない。 |
| 画像時刻の生成 | wrapper `42,45–47,54` は成功した read の画像に、0から始まる frame_index を fps で割った timestamp を付け、TrackMonocular に渡してから番号を増やす。固定した f を用いる等間隔の人工的な相対時刻列であり、各画像の撮像時刻を取得しているわけではない。有限な正の f を前提とする数学的整理式は下記。 |
| 動画位置/PTS との区別 | [OpenCV 4.6 のプロパティ定義](https://docs.opencv.org/4.6.0/d4/d15/group__videoio__flags__base.html) は CAP_PROP_FPS をフレームレート、CAP_PROP_POS_MSEC を動画内の現在位置（ms）とする。現行 wrapper は POS_MSEC も個別 PTS（表示時刻）も取得しておらず、k/f が実際の不等間隔・欠損・時刻情報を再現する保証はない。POS_MSEC 自体を機体の撮像時計と同一視しない。 |
| 処理経過時計との区別 | wrapper `44,65–66` は steady_clock の差を秒へ変換して処理経過を表示する。これは44行から65行までの経過時間で、画像読込/処理に加えて Shutdown と二保存も間に含む。CPU 使用時間でも撮像時刻でもなく、この値を timestamp に渡していない。画像ループには fps に合わせる sleep や待機制御がない（ライブラリ内部で待つ可能性とは別）。 |
| 設定側 Camera.fps は別経路 | 現行 `mini3_calib/out/mini3.yaml:3,22` は File.version="1.0"、Camera.fps=30。`src/System.cc:82–84` は Settings 経路を選び、`src/Settings.cc:410` が readParameter<int> で読み、`include/Settings.h:82,170` の float 値/アクセサを経て `src/Tracking.cc:584–586` が mMaxFrames に代入する。mMaxFrames は `include/Tracking.h:302` の int。動画 get 値をこの設定へ上書きする経路ではない。旧設定経路 `Tracking.cc:1152–1158` は Camera.fps を float として読み、==0 のとき30へ置換する別コード。現行 wrapper の <1 規則と混同しない。 |

## 式・最小例

取得値を `f_raw`、採用値を `f` とすると、現行分岐は `f=30`（`f_raw<1` の比較が true）、それ以外は `f=f_raw`。正常な時間列として扱うには採用値が有限かつ正であることを前提にする。

\[
t_k=\frac{k}{f},\qquad \Delta t=t_{k+1}-t_k=\frac{1}{f},\qquad
t_{N-1}=\frac{N-1}{f}\quad(N\ge1).
\]

`k=0,…,N−1` は読込成功順の整数番号、N は読込成功画像数、f は画像数/秒、t と Δt は秒。式は等間隔モデルの数学的表現であり、実装の double 演算には丸めがある。f=30 の説明例では t0=0、t1≈0.0333秒、t90=3秒。N=91なら最後の画像時刻は3秒で、N/f を最後の画像時刻とはしない。撮像時刻との一致や実ファイルが30fpsであることを示す例ではない。A17 の時間差判定へ渡る基準もこの画像時刻（詳細は既存章参照）。

## 一次資料・PDF・限界

- [OpenCV 4.6 VideoCapture::get](https://docs.opencv.org/4.6.0/d8/dfe/classcv_1_1VideoCapture.html)：未対応プロパティは0を返し、プロパティの実際の挙動はバックエンド等に依存するという本文を確認。CAP_PROP_FPS/POS_MSEC は上表の公式定義を実読。
- [ORB-SLAM3 v2](https://arxiv.org/pdf/2007.11898v2) PDF5頁（誌面5頁）図1の Frame 入力と §III Tracking 本文を画像でも再読。論文は入力と追跡の役割を示す資料で、自前 wrapper の k/f 式の出典ではない。既存 `sources/ORB_SLAM3_2007.11898v2.pdf/.txt` と `_page-05.png` を使用。
- 実動画の fps/PTS/可変フレームレート、実撮像間隔、非有限値の発生、設定との一致は未検査。動画/アプリ実行、設定/コード変更なし。Camera.fps の全使用箇所や次章は未調査。取得障害なし。
