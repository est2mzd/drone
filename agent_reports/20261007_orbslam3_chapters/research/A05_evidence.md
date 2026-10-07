# A05 根拠メモ：初期地図の有無の判断

調査日：2026-10-07。対象は図AのA04→A05→A06/A08。ローカルORB-SLAM3 HEADは `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下のコード行は `third_party/ORB_SLAM3/` 基準。Tracking.cc、Tracking.h、Atlas.ccにHEADとの差分なし。System.ccは既存変更があるためローカル行を示す。

| 根拠 | 確認結果 | 検証箇所 |
|---|---|---|
| 1 状態の型と初期値 | `mState`は`eTrackingState`。NO_IMAGES_YET=0、NOT_INITIALIZED=1、OK=2。コンストラクタではNO_IMAGES_YETで始まる。整数は状態ラベルであり地図点数ではない。 | include/Tracking.h:120–132、src/Tracking.cc:44–49 |
| 2 初回の遷移 | Track内でNO_IMAGES_YETならNOT_INITIALIZEDへ変更し、その後mLastProcessedStateへ保存する。「画像未入力」と「初期化未成立」は区別される。 | src/Tracking.cc:1862–1867 |
| 3 初期化への分岐 | `if(mState==NOT_INITIALIZED)`で初期化経路へ入る。STEREO/RGBD等以外のelseからMonocularInitializationを呼ぶ。本構成のMONOCULARはこの経路。MapPointsの個数をこのifで数えてはいない。 | src/Tracking.cc:1899–1908 |
| 4 未成立／成立後 | 呼出し後もmState!=OKなら現在FrameをmLastFrameへ保存しreturn。OKならこのreturnを通らず初期化分岐を抜ける。同じ呼出しで直後のelseへ入り直すわけではない。分岐入口でNOT_INITIALIZED以外ならelseの追跡経路へ進む。 | src/Tracking.cc:1912–1925 |
| 5 Atlasの器 | 保存Atlasをロードしない起動ではSystemがnew Atlas(0)する。引数付きAtlasコンストラクタがCreateNewMapを呼び、new Mapをactiveとして登録する。この器の生成だけではTrackingの初期化成立を意味しない。 | src/System.cc:117–137、src/Atlas.cc:33–37、58–76 |
| 6 オンライン一次資料 | 下記の公式固定コミットraw本文でNO_IMAGES_YETの遷移、NOT_INITIALIZED分岐、初期化呼出し、未成立時return、elseを実読しローカルと照合。Web表示の正規化行番号はローカル行番号と異なる。 | [公式Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)、検索語`if(mState==NOT_INITIALIZED)` |
| 7 論文PDF | PDF5頁・印刷頁5の図1を画像で、III節を抽出本文と画像で再読。図はTracking内の初期姿勢推定にmap creationを含め、Atlasにactive/non-active mapを置く。本文はactive mapを入力フレームの位置推定先として説明する。mStateの列挙値や今回のif式そのものは掲載していない。 | [ORB-SLAM3 v2](https://arxiv.org/pdf/2007.11898v2)、5頁図1・III節。キャッシュ`../sources/ORB_SLAM3_2007.11898v2.pdf`、同名txt、`ORB_SLAM3_2007.11898v2_page-05.png` |

コード由来の整理式：当該分岐到達時の状態をs∈eTrackingStateとすると、初期化へ入る述語はB(s)=(s==NOT_INITIALIZED)。例：s=1なら初期化経路へ入るが、「地図点が1個」という意味ではない。図の「初期地図がある？」はこの状態管理を簡略化した説明であり、Atlasポインタの非null判定に置き換えない。elseに入ることだけで現在フレームの追跡成功が保証されるわけでもない。

未確認・範囲：A06の二視点処理・初期化成立条件の内訳、喪失後の状態遷移全体は未調査。Track前段の早期returnに到達しない通常入力を上の整理式の前提とする。動画実行による遷移ログは採取していない。今回の一次資料取得障害なし。
