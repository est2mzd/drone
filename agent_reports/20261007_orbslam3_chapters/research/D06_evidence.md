# D06 根拠メモ：Frameと特徴・対応情報

純MONOCULARの必要範囲。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。行番号は `third_party/ORB_SLAM3/` 以下のローカル版。A04/D03/D04/D05の根拠を再利用し、ORB・最適化算法の再調査は行わない。

| # | 確認事項 | 根拠 |
|---|---|---|
| 1 | N個の特徴番号jが、元特徴 `mvKeys[j]`、補正後 `mvKeysUn[j]`、記述子行jに共通する。補正後も画素座標である。 | `include/Frame.h:222–242`、`src/Frame.cc:311–323,747–777`。`src/ORBextractor.cc:1080,1112` は32列CV_8U、正常に特徴があるFrameではN×32 bytes（256 bits/特徴）。特徴番号は画像内の添字でMapPoint IDではない。 |
| 2 | 同じjにMapPointポインタと外れ値フラグを持つ。初期状態は対応null、外れ値false。純単眼のright座標・depthはともに-1。 | `Frame.cc:326–335`、`Frame.h:231–246`。falseは初期値でもあり、対応成立の証明ではない。N=0なら `Frame.cc:319–321` で補正・これらの代入・grid構築より前にreturnする。コンストラクタ全体が常に全フィールドを初期化し終えると説明しない。-1は未知/非ステレオを示す番兵で実測負深度ではない。 |
| 3 | 照合結果が対応配列へ入り、姿勢最適化後に外れ値対応が解除される経路がある。 | `Tracking.cc:2730,2738–2759` は対応配列代入→姿勢設定→最適化→外れ値なら当該ポインタをnullにしフラグもfalseへ戻す。従ってnull/falseから「かつて外れ値でなかった」とも言えない。各時点の2D観測と3D点への関連を分ける。 |
| 4 | 姿勢値と姿勢設定フラグ、Trackingの成功状態は別。 | `Frame.cc:291–296` で時刻とID、`mbHasPose=false`。`Frame.h:144–158,169–174` のGetPoseは値を返しHasPoseはフラグを返す。`Frame.cc:431–436` のSetPoseは値・派生行列を更新しフラグtrue。`Tracking.cc:2739–2745` のように成否評価前の初期値も設定するのでtrueをTracking OKと同一視しない。姿勢は世界→カメラのTcw（A09参照）。 |
| 5 | Frameは参照KFポインタ、BoW/FeatureVector、特徴探索gridも持つが役割が異なる。 | `Frame.h:237–252,274–275`。参照KFは構築時null (`Frame.cc:292`)、Trackingが設定する箇所は `Tracking.cc:2109,2292`。BoW/FeatureVectorはD04の画像検索表現・特徴索引。`Frame.cc:367,385–415` のgridは純単眼では補正後画素からセルを求め、PosInGrid成功時だけ特徴番号を格納する空間探索用索引。すべての特徴が必ずgridに入るとはしない。 |
| 6 | FrameのコピーはIDを継承し、記述子のデータをcloneする一方、地図点ポインタ列はコピーする。 | `Frame.cc:55–84`：`mDescriptors.clone()`、`mvpMapPoints(frame.mvpMapPoints)`、`mnId(frame.mnId)`。地図点実体を複製する操作ではない。コピー先の姿勢フラグは一度false、コピー元が姿勢設定済みならSetPoseする。既存画像のコピーを新画像採番と混同しない。 |

添字対応の整理式：N>0で単眼コンストラクタの該当初期化を終えたFrameに対し、

\[
E_j=(u_j,\bar u_j,d_j,P_j,o_j),\quad j=0,\ldots,N-1.
\]

`u_j=mvKeys[j].pt` は元画像上の2D画素、`bar u_j=mvKeysUn[j].pt` は歪み補正後の2D画素（ともにpixel）。`d_j=mDescriptors.row(j)` は32 byteの記述子、`P_j=mvpMapPoints[j]` はMapPointへの参照またはnull、`o_j=mvbOutlier[j]` はbool。Pは3D座標値そのものではなくポインタであり、nullから3D位置を得られない。KeyPointの角度や尺度段等はA04、時刻とIDはD05へ委ねる。

仮定した3特徴の例（追跡途中のある時点、実測ではない）：

| j | 元画素u / 補正後画素bar u | 記述子行 | P | o | 読み方 |
|---|---|---|---|---|---|
| 0 | (100,200) / (103,201) | d0、32 byte | 点Aへの参照 | false | 対応候補あり、現時点では外れ値フラグなし |
| 1 | (640,360) / (640,360) | d1、32 byte | null | false | 2D特徴はあるが3D点未対応 |
| 2 | (1100,500) / (1096,499) | d2、32 byte | 点Bへの参照 | true | 現在の対応が外れ値と判定された時点の例 |

この3例だけからFrame全体の追跡成功を結論しない。後処理がj=2の参照をnull、フラグをfalseに変えることもある。Nは特徴数であり対応済3D点数ではない。

固定一次ソースを実読：[Frame.h](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/include/Frame.h)、[Frame.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Frame.cc)。PDFは [ORB-SLAM3 v2](https://arxiv.org/pdf/2007.11898v2) PDF5頁=誌面5頁 図1/§III（Frame入力・対応地図点による姿勢推定）と [ORB-SLAM v2](https://arxiv.org/pdf/1502.00956v2) PDF8頁=誌面7頁 §V-C/D（画像特徴との対応、参照KF、投影探索）の必要本文・キャッシュページ画像を実読。フィールド名・コピー仕様は論文でなくコード根拠。

取得障害なし。全フィールドの初期化保証・実動画の特徴数/対応数・コピーの全用途は未検証。コード変更/アプリ実行なし。D07以降へ進んでいない。
