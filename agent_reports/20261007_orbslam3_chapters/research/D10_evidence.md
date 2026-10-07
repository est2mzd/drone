# D10 根拠メモ：Atlas・地図群と共有更新

manifest接続 `A06,P02,P03 ↔ P01; A20/A21; A23` を確認。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下は同リポジトリ内ローカル行番号。A20/A21/P01/P02/P03/A23の確認済み根拠を再利用。

| # | 確認事項 | 根拠 |
|---|---|---|
| 1 | AtlasはMapポインタ集合とcurrentMap参照を持ち、MapはKF/MPポインタ集合を持つ。各オブジェクトの所属Mapも別に保持する。 | `include/Atlas.h:144–149`、`include/Map.h:162–163`。`KeyFrame.cc:835–844`、`MapPoint.cc:560–569` のGetMap/UpdateMapは各オブジェクトの所属ポインタを読み書きする。集合と所属の更新が全体で一命令という意味ではない。 |
| 2 | 新Map作成は旧Mapをstoredにして新Mapをcurrentへ。storedはディスク保存ではなく、badとも別状態。 | `Atlas.cc:58–88`、`Map.cc:204–211`：current/storedは `mIsInUse=true/false`。`Map.cc:241–248` のbadは別の `mbBad`。`Atlas.cc:260–265` のSetMapBadは通常集合から除きbad集合へ移す。A20の新Map作成は旧Mapを保持する。これだけでは地図幾何構築や座標統合をしない。 |
| 3 | GetAllMapsはmspMapsの参照一覧、AtlasのGetAllKeyFrames/GetAllMapPointsは**現在Mapだけ**。いずれも実体の深いコピーではない。 | `Atlas.cc:191–200,209–221`：Atlas mutex下でcurrentから取得、またはMap*をvectorへコピーしID順に整列。`Map.cc:147–156` はMap mutex下で集合からKF*/MP*のvectorを返す。返却後に各実体の姿勢・位置まで固定され続ける保証はない。 |
| 4 | Atlasへの追加APIは引数オブジェクトの所属Mapへ追加する。常にcurrentへ追加するとは限らない。ロックも階層・対象ごとに異なる。 | `Atlas.cc:103–112` は `GetMap()->AddKeyFrame/AddMapPoint`。`Map.cc:58–83` は `mMutexMap` 下で集合追加。`Atlas.h:163` の `mMutexAtlas`、`Map.h:141` の `mMutexMapUpdate`、`Map.h:202` の `mMutexMap` は別。SetMapBadやMapのcurrent/stored/bad setterは関数内部に一律のlockを持たないため、全APIがAtlas mutexで保護されるとはしない。 |
| 5 | Tracking/LocalMapping/LoopClosingは同じ地図実体を参照し、異なる範囲を読書きする。 | P01根拠：`Tracking.cc:1812,1886` は取得時のcurrentMapを追跡し、そのMapの `mMutexMapUpdate` をTrackのreturnまで保持。P02/D09根拠：LMはKF/観測を登録し、条件付きlocal BAで姿勢・点を更新。P03根拠：LCは補正・融合・所属移動を行う（例 `LoopClosing.cc:1431–1551`）。各役割がAtlas全体を一括停止/固定するという意味ではない。A23のShutdown/保存も全体snapshot保証としない。 |
| 6 | 同じAtlasに入っていることは、別Map同士が既に共通座標・同一尺度になったことを意味しない。 | [ORB-SLAM3 v2](https://arxiv.org/pdf/2007.11898v2) PDF5頁=誌面5頁 図1/§IIIはdisconnected mapsとactive/non-active maps、共有情報を介する並列構成を示す。本文と `sources/ORB_SLAM3_2007.11898v2_page-05.png` を再読。別地図の単眼相似変換・統合はP03の確認済み根拠を参照し、ここで再導出しない。 |

最小集合モデル（安定した登録状態を説明する概念式）：

\[
\mathcal A=\{M_0,\ldots,M_{r-1}\},\quad M_{\rm cur}\in\mathcal A,\quad
M_i\leadsto(\mathcal K_i,\mathcal P_i),\quad
\operatorname{map}(K)=M_i,\ \operatorname{map}(P)=M_i.
\]

Aは通常Map集合、rはその個数、Mcurは現在Mapへの参照、K_i/P_iはMap iが登録するKeyFrame/MapPoint参照集合、mapはオブジェクトの所属参照を表す。最後の所属式はK∈K_i、P∈P_iについて登録が整合した状態を説明しており、統合・削除の途中も全関係が同時に成立する原子的保証ではない。空のAtlas/current未設定などの全状態をこの式で表してはいない。識別子・集合・参照は無次元で、地図座標値とは別。

2Mapの仮定例：A=`{M0,M1}`、Mcur=M1、M0はstoredで2 KF/100 MP、M1はcurrentで3 KF/80 MP。`GetAllMaps()` はID順にM0/M1への参照を返すが、`Atlas::GetAllMapPoints()` はM1の80参照を返す。返却vectorをコピーしても80個の点実体は複製されない。M0座標の `(1,0,0)` とM1座標の `(1,0,0)` を同じ位置とは比較できず、純単眼の1は各地図の任意長さ単位であって自動的に1mではない。実データ件数の測定ではない。

固定公式 [Atlas.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Atlas.cc)、[Map.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Map.cc) の必要実装を実読。取得障害なし。並行実行時の整合性・競合の全検証、全reset/merge経路の再調査、各Map実座標・実尺度の検証はしていない。コード変更/アプリ実行/D11先行なし。
