# D12 根拠メモ：補正・統合された地図の共有

純 MONOCULAR 通常 SLAM。固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。行番号はローカル `third_party/ORB_SLAM3/` 基準。P03/D10/A23 を再利用し、結果の書戻しと読取りだけを確認した。

| 論点 | 現行コードの根拠と限定 |
|---|---|
| 同じ Map 内の補正 | `src/LoopClosing.cc:1040–1064,1068–1113`：Map 更新 mutex の下で補正した KF 姿勢を保存し、旧/新 Sim3 を介して MapPoint 位置を書き換え、方向・距離範囲と接続を更新する。Map 実体を新設する処理ではない。 |
| 位置以外も更新 | `LoopClosing.cc:1118–1140,1142–1183,1192–1196`：対応点の Replace/観測追加、SearchAndFuse、接続の更新、グラフ補正、loop edge 追加。出力は位置配列だけでなく、KF と点の観測対応・共視接続も変わる。融合は D11 の置換処理につながる。 |
| 別 Map の座標と所属 | `LoopClosing.cc:1431–1496,1506–1554`：current 側の窓を merge 側座標へ補正し、KF/点へ位置・姿勢を反映。各実体の UpdateMap、統合先集合への追加、元集合からの除去、current Map 切替、元 Map の bad 化を行う。1554 行では生存する merge Map の ID を旧 current の ID へ変更するので、「Map ID が不変」の例にはできない。 |
| 統合後の接続と残り | `LoopClosing.cc:1559–1605,1647–1750,1772–1778`：木の接続変更・点融合、残りの KF/点への補正と所属移動、merge edge と変更番号更新。通常集合 `mspMaps` からの除去は先行する1551行の `SetMapBad`（`Atlas.cc:260–265`）。1778行の `RemoveBadMaps` は `mspBadMaps.clear()` であり、Map を delete するループはコメントアウトされている（`Atlas.cc:268–275`）。純単眼は1715行の後半 EssentialGraph 分岐外（P03参照）。二つの点群を単純連結しただけの結果でも、ここで全メモリを解放する処理でもない。 |
| Tracking が読む更新 | `Tracking.cc:1886–1897` は取得した current Map の更新 mutex 下で変更番号を比較する。これは共有更新の検知であり、全 sensor 共通の自動再予測を保証しない。通常 OK 経路の1943行→2702–2717は前 Frame の置換済み点参照を差し替える。運動モデル経路2860行→2782–2787は参照 KF の現在姿勢を使って前 Frame 姿勢を再構成する。どの画像でも全補正を一括再計算するという意味ではない。 |
| 読取り・保存の境界 | D10 の `Atlas.cc:191–221,Map.cc:147–156` は参照一覧を返すだけで、全実体の固定コピーではない。P03 の GBA は条件付きの非同期処理。A23 の `System.cc:520–551` は終了要求後の待機がコメントアウトされている。地図補正が行われたことから、全最適化完了・収束・二出力の同時点 snapshot は保証できない。 |

## 点補正の最小整理式と仮定例

\[
X_{w,\mathrm{new}}
 = S_{iw,\mathrm{new}}^{-1}\!\left(S_{iw,\mathrm{old}}(X_{w,\mathrm{old}})\right),
\qquad S(X)=sRX+t.
\]

`Xw,old/new∈R³` は同じ点の補正前/後の地図座標、`i` は補正を伝える KF。`Siw,old/new` はそれぞれ地図世界座標から共通の中間カメラ座標への相似変換。`R∈SO(3)` は回転、`s>0` は尺度比、`t∈R³` は出力側座標の並進。位置と並進の長さ単位は各地図の任意尺度、R/s は無次元で、メートル尺度を自動獲得する式ではない。これは `LoopClosing.cc:1093–1096,1487–1495` の伝播段階を表し、後続 BA 後まで点位置が不変という式ではない。

仮定例：`Sold(X)=X`、`Snew(X)=2X`、旧点 `(2,0,6)` なら新点は `(1,0,3)`。両者を各変換で写した中間座標は `(2,0,6)` となる。実データの補正量・誤差改善を示す値ではない。別 Map 統合の所属も、実体参照を用いて「旧 current に属した K/P → 生存する merge Map に属する K/P」と説明し、数値 ID の固定を仮定しない。

## 一次資料の実読・未確認

- 固定公式 [LoopClosing.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/LoopClosing.cc) と [Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc) の必要実装をオンライン照合。行番号は空行を保持したローカル版。
- [ORB-SLAM3 論文 v2](https://arxiv.org/pdf/2007.11898v2) の PDF 9頁 §VI、10頁 §VI-B/D と図3(a)を、キャッシュ本文と `sources/ORB_SLAM3_2007.11898v2_page-09.png` / `_page-10.png` で再読。同 Map loop と別 Map merge、座標整合・点融合・観測接続・Tracking による再利用の根拠。論文の一律な最適化手順を現行純単眼の条件分岐へ転記しない。
- 取得障害なし。実行時の補正量、真値一致、改善量、全競合の不存在や保存時の一貫性は未検証。P03 の全算法/GBA条件は再調査せず、コード実行・改修・D13先行なし。
