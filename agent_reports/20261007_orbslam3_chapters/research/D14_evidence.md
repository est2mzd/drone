# D14 根拠メモ：時刻付き地図点ファイル

対象は独自 `SaveTimedMapPoints`。ORB-SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4` の既存ローカル差分を読む。以下の System/Atlas/Map 行番号は `third_party/ORB_SLAM3/` 基準。A23/D09/D10/D11 の既読根拠を再利用。

| 論点 | 現行実装と限定 |
|---|---|
| 呼出しと独自機能 | `include/System.h:180–183` に宣言、`src/System.cc:1344–1392` に実体。wrapper `slam/src/offline_mono.cpp:57–60` は Shutdown 後、親ディレクトリを作成して無条件に呼ぶ。固定 HEAD の System.cc と公式固定オンライン System.cc には同名関数なし。上流標準の出力形式ではない。 |
| 保存対象 Map | `System.cc:1346–1357` は各 `GetAllMapPoints().size()` を比較。これは取得集合の件数で、null/bad を選別した有効点数でも KF 数でもない。`best=0`、strict `n>best` により同数なら先に選んだ候補を保持し、全 Map が0点なら選択先なし。D10 の Atlas GetAllMaps は ID 順の参照列だが、保存関数が全実体を固定するわけではない。 |
| 点の選別と座標 | 選択後に点一覧を再取得し、`1371–1372` で null/bad 点を除外。時刻条件通過後、`1383–1384` は `GetWorldPos()` の3成分をそのまま採る。選択 Map の世界座標で、別原点・カメラ座標への変換はない。座標の finite 検査はない。純単眼の長さは任意尺度で、出力桁数はメートル精度を保証しない。 |
| 時刻は残る観測から算出 | `1373–1382` は earliest を +∞ で開始し、現在の観測表から null/bad KF を除外した後 `min(earliest,KF.mTimeStamp)` を反復。各 KF 時刻を事前に finite filter せず、最後の earliest にだけ isfinite を適用し、不合格なら点を出さない。D09 の KF 時刻は元 Frame 時刻のコピー、D02 の wrapper 時刻は k/f 秒。点のオンライン初検出時刻・生成時刻を永続保存している機構ではない。 |
| 並替えと列 | `1367,1386–1389`：行は `tuple<double,float,float,float>`、標準 sort は `(t,x,y,z)` の辞書順。同時刻でも x/y/z で順序が決まり、点一覧の入力順を保存する仕様ではない。有限の通常数値を扱う前提で説明し、非有限座標時の並替え結果は保証しない。`fixed<<setprecision(6)` により空白区切りの `t x y z` を小数点以下6桁、改行区切りで出す。ヘッダ・点 ID は出さない。 |
| 成否・終了の限界 | `1359–1364` は候補なしでも ofstream 構築後に0件ログで return。戻り値は void、open/write 成否検査なし。`1391` の行数ログは書込成功の証明ではない。A23 の Shutdown 待機コメントと D10 の参照取得を合わせ、全最適化完了・同時点 snapshot・二出力の同一 Map 選択は保証しない。実ファイル作成は今回行っていない。 |

## 時刻の最小式と仮定例

保存時に読み出した点 P の観測表について、null でなく bad でもない KF の集合を O(P)、各 KF の保存時刻を t_K [秒] とする。**O(P) が非空で、その時刻がすべて有限という前提**なら、コードの結果を

\[
t_P=\min_{K\in O(P)}t_K,\qquad
\mathrm{row}(P)=(t_P,x_P,y_P,z_P)
\]

と整理できる。`(xP,yP,zP)` は読取り時の点位置、同じ選択 Map の任意長さ単位。空なら +∞ のまま最終検査で除外される。非有限時刻を含む場合は上式の前提外であり、「有限時刻だけを集めて min」と説明せず、上表の min 反復→最終 isfinite の順序を採用する。

仮定例：M0 が集合4点、M1 が3点なら M0 を選ぶ。M0 の1点が bad、別の1点に残る適格な観測 KF がなければ、この2点は出力されず、出力行数は選択に使った4と一致しない。残る点 P の観測時刻が bad KF の1秒と有効 KF の4秒・7秒なら tP=4秒。位置が `(1,0,5)` なら行は `4.000000 1.000000 0.000000 5.000000`。1秒の観測が除外されるので、オンラインの最初の観測時刻と同じとは限らない。すべて説明上の数値で実測ではない。

## 一次資料・PDF実読

- [公式固定 System.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/System.cc) を取得し `SaveTimedMapPoints` 不在を確認。ローカル `git show HEAD:src/System.cc` でも不在、既存 diff は System.cc/宣言側への追加を示す。独自処理はローカル実体を根拠とする。
- [ORB-SLAM3 論文 v2](https://arxiv.org/pdf/2007.11898v2) PDF5頁 §III/図1をキャッシュ本文と `sources/ORB_SLAM3_2007.11898v2_page-05.png` で再読。Atlas の Map/KF/MapPoint、Frame の追跡と KF 選択、継続的な地図更新の背景を確認。この論文は独自時刻付き点ファイルの列・時刻選別・I/O 仕様を規定しない。
- 取得障害なし。実ファイル・実座標・実時刻、非有限値/同時更新/I/O 失敗の動作は未検証。D15/O01、実行、コード変更へ進んでいない。
