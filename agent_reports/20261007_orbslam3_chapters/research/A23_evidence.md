# A23 根拠メモ：終了要求と結果保存

対象は純単眼の現行 `slam/src/offline_mono.cpp`。リポジトリ HEAD は `d1265bc35439dd6ca57687ac93c8b3a7310fc681`、ORB-SLAM3 HEAD は `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。行番号はローカル現行ファイル。本文執筆、プログラム実行、実データ保存は行っていない。

| 確認事項 | 現行の根拠と読み取れる範囲 |
|---|---|
| 引数・入力終了 | `offline_mono.cpp:17–30` は実行名を含め `argc==5` を要求し、辞書・設定・動画・点出力先の順。引数不備は usage と `return 1`、動画を開けなければ `cannot open` と `return 1`。`45–55` の `capture.read(frame)` が false になるとループを抜ける。EOF とその他の read 失敗を wrapper は分類しない（A02参照）。 |
| 終了後の呼出し順 | `offline_mono.cpp:57–63` は `Shutdown()` → 出力親ディレクトリ作成 → `SaveTimedMapPoints(points_path)` → 同じ親ディレクトリの `stem + "_poses.txt"` へ `SaveCameraPoses()`。両独自保存は無条件の順次呼出しであり、optional ではない。`create_directories` を含め、この main に例外捕捉はない。 |
| Shutdown が行うこと | `System.cc:520–530` は shutdown フラグ設定と LocalMapping/LoopClosing の `RequestFinish()`。`539–551` の終了待ち while はコメントアウトされ、join 呼出しもない。この待機コメントは固定上流版にも存在する。終了要求を出した事実から、全処理完了・BA 収束・二つの出力の完全な同時点スナップショットは保証できない。設定が空でない場合だけ `SaveAtlas(BINARY_FILE)` を呼ぶ `553–557` は独自二出力と別の条件分岐。 |
| 独自出力と上流の区別 | `include/System.h:183,188`、`System.cc:1344–1463` の二保存関数は既存ローカル差分。`git show HEAD:src/System.cc` と公式固定版の双方に `SaveTimedMapPoints` / `SaveCameraPoses` はない。固定版の標準終了・保存機能の説明を、そのままこの独自出力の仕様にしない。 |
| 保存する地図の選択 | 各関数がそれぞれ `GetAllMaps()` を取得し、`GetAllMapPoints().size()` を比較する（`1346–1357`、`1396–1407`）。最大 KeyFrame 数ではなく、取得した MapPoint 集合の個数が最大の地図を選ぶ。現在地図の固定指定でも Atlas 全体の結合出力でもない。二回の選択は独立で、同一の選択結果・同一時点を固定する共通スナップショットはここにはない。`best=0` と `n>best` により全地図が0点なら選択先は nullptr のまま。 |
| 保存ログと成否 | `ofstream` 構築は `1359,1409`。両関数は `void` で、open/write 成否の検査や失敗用ログを実装していない。選択先がない場合も stream 構築後に0件ログを出して return（`1361–1364`,`1411–1414`）。末尾の件数・パスログ（`1391`,`1462`）もファイルへの正常書込みを証明する結果値ではない。入力動画の open 失敗ログと混同しない。 |
| wrapper の終了コード | `offline_mono.cpp:48–49` の `tracked` は状態値2の画像数、`54` の `frame_index` はループで処理した画像数。`66` は両者を別々に表示し、`67` へ正常に到達した場合だけ `frame_index>0` なら0、そうでなければ1を返す。したがって終了コード0は追跡成立件数が正であることや、両保存の成功を検査した結果ではない。例外等があっても常にこの規則で終了する、とは言わない。 |

## 一次資料・PDF実読

- [公式固定コミット System.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/System.cc) をオンラインで確認。Shutdown の finish 要求、コメント化された待機、条件付き Atlas 保存をローカルと照合した。独自二保存の不在は固定 HEAD のファイル内容とも照合した。
- [ORB-SLAM3 論文 v2](https://arxiv.org/pdf/2007.11898v2) の PDF 5 頁（誌面5頁）図1と §III を本文・画像で再読。Tracking、Local Mapping、Loop & Map Merging、Full BA の構成と、local mapping thread による地図の継続的な更新を確認。これは並列構成の根拠であり、現行 Shutdown や独自保存の同期保証を規定する資料ではない。キャッシュは `sources/ORB_SLAM3_2007.11898v2.pdf`、同名 `.txt`、`sources/ORB_SLAM3_2007.11898v2_page-05.png`。

## 未確認・本章の限界

静的読解のみ。実際の終了時スレッド状態、I/O 失敗の再現、ファイル内容の一貫性は検証していない。出力列・座標・valid・行の選別詳細は D14/D15 へ残す。初回計画の「optional な独自保存」「最大 KF 数」「保存 open 失敗ログ」という前提は現行コードに合わせて訂正した。
