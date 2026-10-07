# P01 根拠メモ：Trackingの統括と実行境界

対象は現行 wrapper の純 MONOCULAR・通常 SLAM。manifest の位置は「並行図/DFD: Tracking、境界図: 自前ラッパー・ORB-SLAM3本体」、接続は `A03 → A04〜A22; D09 → P02`。ORB-SLAM3 固定版は `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`、外側リポジトリ HEAD は `d1265bc35439dd6ca57687ac93c8b3a7310fc681`。以下はローカル行番号。System.cc には既存独自保存差分があるが、本章の呼出し境界は公式固定版とも照合した。

| 確認事項 | 根拠と確認できる範囲 |
|---|---|
| main から Tracking への直接呼出し | `slam/src/offline_mono.cpp:39,45–54` の main は画像を読み、同じループで `TrackMonocular(frame,timestamp)` を呼ぶ。`System.cc:471` → `Tracking.cc:1566–1614` の `GrabImageMonocular` → `1612` の `Track()` は直接の同期呼出し。Tracking 専用 thread を起動して画像キューへ投げる経路ではない。次の wrapper の read はその呼出しが戻った後。 |
| 別スレッドの境界 | `System.cc:193–197` は Tracking オブジェクトの生成で、コメントも構築元の main thread に置く旨。`200–202` は LocalMapping::Run、`218–219` は LoopClosing::Run を `new thread` で起動する。`222–229` は部品相互のポインタ設定。Viewer は `234–238` の条件付き生成で、この wrapper は39行で false を渡す。論文の「Tracking thread」という部品名だけから別の std::thread 生成を読み込まない。 |
| 三種類の入力 | D05 の画像と時刻は wrapper `45–47`。時刻は `frame_index/fps` で秒、fps と fallback は `33–35`（A03参照）。D03 設定と D04 辞書は wrapper `22–23,39` から System 構築時に渡り、`System.cc:75–84,122–123,196–197` で読込・Tracking への引渡し。各画像の Frame は `Tracking.cc:1584–1589` で画像・時刻・抽出器・辞書・カメラ・歪み情報等を受け取る。設定と辞書を毎画像 wrapper が読み直す構造ではない。 |
| Frame・姿勢・状態の戻り | `GrabImageMonocular` は Frame 構築後に Track を呼び、`1614` で `mCurrentFrame.GetPose()` を返す。`System.cc:471–478` はその姿勢を受け取り、別の `mMutexState` の下で追跡状態・MapPoint ポインタ列・特徴点列を System 側へコピーし、Tcw を返す。返却された姿勢値が常に追跡成功を意味するとはしない（A05〜A22参照）。wrapper47行は返却 Tcw を保存せず、48–49行で `GetTrackingState()==2` の件数を数える。getter は `System.cc:1326–1329`。 |
| 現在地図のロック範囲 | `Tracking.cc:1812` で得た `pCurrentMap` の `mMutexMapUpdate` を `1886` の関数スコープの `unique_lock` が取得する。明示 unlock はなく、取得後は Track の return または関数末尾 `2332` で自動解除される（途中 return 例 `1915,2276,2288`）。Frame 構築・特徴抽出は呼出し順上この取得より前。取得時の Map に対応する mutex であり、Atlas 全体・全共有データ・すべてのワーカースレッドを一括停止する保証ではない。 |
| 必要時の KeyFrame 受渡し | 通常の追加判定から `Tracking.cc:2248–2250` で `CreateNewKeyFrame()` を呼び得る。`3218–3222` に早期 return があり、実際に進む場合は `3224` で現在 Frame と現在 Map 等から KeyFrame を生成、`3335` で LocalMapping に渡す。`LocalMapping.cc:284–288` は別の `mMutexNewKFs` の下でポインタをキューへ push し BA 中断要求を設定する。これは受渡しであり、LocalMapping の地図処理が完了したという戻りではない。初期2枚の生成経路は A06、追加判定は A13 を参照。 |
| 共有情報と論文の役割 | `System.cc:196–200,218,222–229` は Atlas、辞書、KeyFrameDatabase、および部品相互の参照を渡している。論文 PDF5頁図1・§III は Atlas とデータベースを介する Tracking/Local Mapping/Loop & Map Merging の構成、Tracking の姿勢計算・KeyFrame 選択、Local Mapping の地図更新を示す。具体的にどの thread が呼出しを実行し、どの mutex を取得するかは現行コードの根拠と区別する。 |

## 一次資料と実読範囲

- [公式固定 System.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/System.cc)：Tracking/LocalMapping/LoopClosing の構築・thread 起動、TrackMonocular の直接呼出しと状態コピーをオンライン確認。
- [公式固定 Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)：GrabImageMonocular の Frame 構築・Track 呼出し・姿勢返却、現在 Map の mutex 取得をオンライン確認。
- [ORB-SLAM3 論文 v2](https://arxiv.org/pdf/2007.11898v2)：PDF5頁（誌面5頁）の図1・§III を本文と画像で再読。キャッシュは `sources/ORB_SLAM3_2007.11898v2.pdf`、同名 `.txt`、`sources/ORB_SLAM3_2007.11898v2_page-05.png`。

## 限界

コードの静的読解のみ。実際のスケジューリング、待ち時間、性能、全共有アクセスの競合有無は検証していない。A群の算法を反復せず、P02/P03 の内部処理へは進んでいない。取得上の障害なし。
