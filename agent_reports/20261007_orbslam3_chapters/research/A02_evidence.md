# A02 根拠メモ：次画像の有無と動画ループ

確認日：2026-10-07。担当：`/root/chapter_supervisor/research_worker`。A02計画・manifest確認済み。図Aの接続はA01/合流点A→A02→取得成功ならA03、falseならA23。

版：A01と同じ主HEAD `d1265bc35439dd6ca57687ac93c8b3a7310fc681`、ORB_SLAM3 HEAD `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。今回の対象 `slam/src/offline_mono.cpp` は差分なし、SHA-256もA01記録と一致（先頭 `1331b120b9a35983`）。以下のLは同ファイルの行番号。

| # | 区分・確認した根拠 | A02で使える結論 |
| --- | --- | --- |
| 1 | コード：L27-30、L41-45 | 動画openの確認は先に行う。反復の判定は `while (capture.read(frame))`。独立した「次があるか」の先読みAPIは使わない。 |
| 2 | 公式文書：OpenCV 4.13.0 `VideoCapture::read` のParameters/Returns | 次フレームを取得・デコードして出力引数へ格納する操作。戻り値はboolで、取得できなければfalse、出力画像は空になると説明する。 |
| 3 | コード：L45-55。公式文書は終端や取得不能をfalseの例として挙げる | trueならループ本体へ入り、L47で本体へ画像を渡す。図のA02判断とA03画像読込は、実装上同じread呼出しに含まれる。 |
| 4 | コード：L42、L45-55 | `frame_index` は0開始、処理がL54まで達するたびに1増える。falseの試行では本体に入らず増えない。ループ内部にbreak/continueはない。 |
| 5 | コード：L45-57、main全体 | EOF（End of File：ファイル終端）とその他のread失敗を分類する分岐・再試行・理由別ログはない。falseから言えるのは「次画像を取得できなかった」であり、正常終端の確定ではない。 |
| 6 | コード：L57-67 | 通常のfalse退出後はShutdownと保存呼出しへ進む。末尾まで到達した場合、処理枚数が正なら終了値0、0枚なら1。終了値0は全動画を正常に読めた証明ではない。 |
| 7 | PDF5頁/紙面5、図1・III節、キャッシュ画像を再実読 | 論文図はFrame→Extract ORBをTracking内部への入力として描く。本文はTrackingがセンサ情報を処理すると説明する。独自ラッパーの動画whileループやEOF判定は描かない。 |
| 8 | コードL42-55からの説明用推論 | readがtrue,true,true,falseを返し各本体が完了する例では、readは4回、本体は3回、frame_indexは0→1→2→3で止まる。実行記録ではない。 |

整理式候補：`b_j = capture.read(frame)`、`b_j ∈ {false,true}`。jは0始まりの読込試行番号（整数、単位なし）、b_jはブール値、frameは出力画像用のcv::Mat。式は教材用表記で論文式ではない。readは状態と出力画像を変える操作で、純粋な存在判定関数ではない。偽の試行も数えるjと、完了した本体回数を表すframe_indexは区別する。幾何座標系を扱う式ではない。

一次資料：

- [OpenCV公式VideoCapture文書](https://docs.opencv.org/4.13.0/d8/dfe/classcv_1_1VideoCapture.html) のread節をネットで実読（表示行601-617）。文書版4.13.0と手元バイナリのリンク版の一致は未確認。
- [Camposほか ORB-SLAM3論文v2](https://arxiv.org/pdf/2007.11898v2)。`sources/ORB_SLAM3_2007.11898v2.pdf` と同名txt、`..._page-05.png`を再利用。取得し直していない。図1とIII節の本文・紙面を確認。A02に採用する論文式はない。

未確認・限界：動画は実行・再生していない。具体的ファイルの終了理由、破損時のバックエンド挙動、例外発生時の挙動を実測していない。上のfalse退出説明はreadが戻った場合で、例外やプロセス異常終了まで保証しない。時刻計算、追跡成否、実測FPSは対象外。コード・進捗表・他章に変更なし。
