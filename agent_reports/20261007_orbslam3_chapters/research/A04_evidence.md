# A04 根拠メモ：グレー化と特徴抽出

初回調査の記録を以下に保持する。原論文アクセスの最新状況は末尾「原論文追補」を参照。

2026-10-07。A04計画に従う。接続D05画像/時刻・D03校正→A04→D06 Frame→A05。版はA01のORB_SLAM3 HEAD `4452a3c4`（完全SHAはA01）。対象Tracking/Frame/ORBextractor/ORBmatcherに既存差分なし。下表のパスは `third_party/ORB_SLAM3/src/` 基準。

| 根拠 | 観測事実／資料記述 |
| --- | --- |
| `Tracking.cc:1566-1589` | 3/4チャネルをRGB設定に応じグレー化。初期状態または `(lastID-initID)<mMaxFrames` では初期抽出器、それ以外は通常抽出器をFrameへ渡す。 |
| `Tracking.cc:588-601` | 通常nFeatures、初期用5*nFeaturesで生成。現行設定なら1000/5000という要求値であり、実検出数の保証ではない。 |
| `Frame.cc:307-330,418-424` | ExtractORB→特徴数確認→UndistortKeyPoints→MapPointポインタをNULLで初期化。点がなければ途中return。出力mvKeysは2次元特徴点、mDescriptorsは比較用bit列で、まだ3次元MapPointではない。 |
| `ORBextractor.cc:1086-1118` | 入力型はCV_8UC1（8bit単チャネル）を要求。ComputePyramid→ComputeKeyPointsOctTreeを実行。ComputeKeyPointsOld呼出しはコメント。 |
| 同`:414-445,1170-1186,1143-1151` | 段別倍率と目標数を用意し、画像を段階的に縮小。段内で得た点の座標は倍率を掛け原画像座標へ戻す。 |
| 同`:781-895,757-775` | 各セルでFAST、空セルなら低いminThFASTで再試行。DistributeOctTreeで分布調整し、各末端領域の最大response点を残す。Harris応答の再計算はない。Old方式もHarrisそのものとは断定しない。 |
| 同`:76-102,471-477,893-895` | IC_Angleが円形近傍のm10/m01を計算しfastAtan2へ渡す。方向計算にはピラミッド画像を使う。公式APIは返り値を度と説明する。 |
| 同`:106-142,1077-1083,1131-1138` | 記述用画像に7×7・sigma=2のGaussianBlur。角度をπ/180倍してsin/cosへ渡し、回転した整数標本位置の輝度を `<` で比較。32bytes=256bit。12度刻みの参照表を使うという公式紹介を手元実装へ転記しない。 |
| `Frame.cc:747-778` | 抽出後の点座標をundistortPointsで補正しmvKeysUnへ格納。画像全面の事前補正ではない。先頭歪み係数が0ならmvKeysをコピーする実装。 |
| `ORBmatcher.cc:2058-2073` | 32bit語8個をXORし立ったbitを数える。Hamming距離のコード根拠。比較処理の内部調査へは進まない。 |

式は**論文番号のないコード整理式**とする。

- スケール：`s_l=a^l`、`u_0=s_l u_l`。lは整数の段番号、a>1は無次元倍率、u_lは当該段の2次元画素座標、u_0は元画像の画素座標。画像寸法の丸めと補間があるため連続画像の厳密等式とはしない。
- 方向：`m_pq=Σ_(x,y∈Ω) x^p y^q I(x,y)`、`θ=atan2(m_01,m_10)`。Ωは特徴点中心の円形整数画素近傍、x右/y下、単位px。Iは8bit輝度、p/qは非負整数、m_pqの単位は輝度×px^(p+q)。実装はm10/m01を直接計算し、重心のm00除算はしない。理論のθはrad、コードのKeyPoint.angleは度で、記述子内に変換がある。両モーメントが小さければ方向の安定を保証しない。
- bit比較：`b_i=1[Ĩ(c+round(Rθ p_i)) < Ĩ(c+round(Rθ q_i))]`。i=0…255、b_i∈{0,1}。Ĩは平滑化した段画像、cは丸めた特徴点中心、p_i/q_iは固定比較パターンの2次元画素オフセット。Rθは2×2回転行列、roundは成分ごとのcvRoundに対応。画素値が等しい場合は0。座標は当該段のx右/y下。画面上の正角は時計回りに見える。
- `d_H(b,c)=Σ_i(b_i XOR c_i)`。二つの256bit列の相違数で単位はbit、範囲0…256。距離が小さいことだけで同じ3次元点とは確定しない。

一次資料（ネット実読、OpenCV 4.13.0。手元リンク版との一致は未確認）：

- [ORB公式紹介](https://docs.opencv.org/4.13.0/d1/d89/tutorial_py_orb.html)：FAST＋BRIEF、ピラミッド、重心方向、Harris上位選別を説明。Harrisは**この紹介の記述**であり原論文PDF実読の結果ではない。現行OctTreeとの差を明示する。
- [FAST公式紹介](https://docs.opencv.org/4.13.0/df/d0c/tutorial_py_fast.html)：FAST=Features from Accelerated Segment Test。環上の連続画素が中心輝度+tより明るい、または中心輝度−tより暗い条件。例のn=12を手元の既定値と決めつけない。
- [fastAtan2公式API](https://docs.opencv.org/4.13.0/db/de0/group__core__utils.html)：方向は度。ORBのBRIEFはBinary Robust Independent Elementary Features。グレー化係数の式は今回採用しない。
- [ORB-SLAM3論文v2](https://arxiv.org/pdf/2007.11898v2)：既存キャッシュPDF5頁/紙面5の図1・III節を本文とpage-05.pngで再実読。Frame→Extract ORBがTrackingの入口にある。原論文ORBの式出典の代用にはしない。

取得障害・未確認：Rubleeほか *ORB: an efficient alternative to SIFT or SURF*（ICCV 2011）の**原論文PDFは未取得・未読、式番号未確認**。以下の正規導線を試し、大監督/小監督の指示で取得調査を終了した。

| URL | 結果 |
| --- | --- |
| `https://www.willowgarage.com/sites/default/files/orb_final.pdf` | Webアクセス不可（http指定も同様） |
| `https://www.cs.ubc.ca/~lowe/525/papers/rublee_iccv11.pdf`、同`rublee.pdf` | 直接取得HTTP404 |
| `https://doi.org/10.1109/ICCV.2011.6126544` | IEEEのJavaScript検証画面、本文未取得 |
| `https://rpg.ifi.uzh.ch/docs/teaching/2024/06_feature_detection_2.pdf` | 大学講義PDFは取得成功。78頁リンク注釈だけを導線に使用し、原論文として扱わない |
| 上記78頁が示す著者Gary BradskiのResearchGate PDF（下記） | 直接取得HTTP403 |

著者リンク：<https://www.researchgate.net/profile/Gary_Bradski/publication/221111151_ORB_an_efficient_alternative_to_SIFT_or_SURF/links/00b4951c369020213a000000/ORB-an-efficient-alternative-to-SIFT-or-SURF.pdf>

実動画の点数、精度、照明・ぼけ・回転等に対する性能は未測定。原論文との全実装差分は未検証。コード実行・変更、ビルド、インストール、進捗表変更、他章先行は行っていない。

## 原論文追補（2026-10-07、A05合格後の単独割当）

[新しい著者プロフィールのPDF URL](https://www.researchgate.net/profile/Gary-Bradski-4/publication/221111151_ORB_an_efficient_alternative_to_SIFT_or_SURF/links/00b4951c369020213a000000/ORB-an-efficient-alternative-to-SIFT-or-SURF.pdf)はWeb本文抽出に成功。題名は *ORB: an efficient alternative to SIFT or SURF*、著者Ethan Rublee／Vincent Rabaud／Kurt Konolige／Gary Bradski、所属Willow Garage、全8頁を確認。アクセスできた著者配布PDFの本文を下表で照合した。IEEE最終組版との同一性は未確認。

| 原論文本文で確認した箇所 | 現行コードとの対応・注意 |
| --- | --- |
| PDF2頁§3.1：FAST検出点をHarris尺度で順位付けし上位N点、各ピラミッド段で実施。 | 初回は公式OpenCV紹介だけの根拠だったが、今回は原論文本文でも確認。現行`ORBextractor.cc:781–895,757–775`のOctTree分布選別と区別する。 |
| 2頁§3.2、式(1)モーメント、式(2)重心`C=(m10/m00,m01/m00)`、式(3)`θ=atan2(m01,m10)`。 | 現行`:76–102`は円形近傍のm10/m01を直接計算。m00除算を省くが方向式の形は式(3)と対応する。数学的説明ではm00>0を前提とし、重心が原点なら方向未定義。 |
| 3頁§4.1、式(4)輝度比較、式(5)比較bitの格納、n=256。 | 現行`:122–142`も前者輝度が小さい時1、等しい時0。コード整理式のi=0…255と原論文i=1…nの添字を混同しない。 |
| 3頁§4.1、`Sθ=RθS`、式(6)回転した比較位置での記述。直後に2π/30=12度刻みの参照表。 | 現行`:106–119`はKeyPoint角度をradへ変換しsin/cosを計算、回転座標をcvRoundする。12度量子化の参照表は使わない。「連続角度」は12度刻みでない意味で、浮動小数演算・画素丸めを含む。回転行列の式そのものに原論文の式番号(6)を付けない。 |
| 3頁§4.1：平滑化は積分画像を用いた5×5小窓。図2の抽出本文は人工回転・雑音条件の方向比較。 | 現行`:1131–1138`は7×7 GaussianBlur、sigma=2。図2の画像・軸配置は下記障害により視認未確認で、性能の追加結論には用いない。 |

**実読と保存の限界**：式番号・分数・比較順はWeb抽出本文で確認したが、ページ画像はまだ視認できていない。通常curlとブラウザUAのcurlはともにHTTP403。Webのscreenshot呼出しは参照表示だけを返し、画像ピクセルが作業者へ届かなかった。別Web入口も同様で、IABは利用不可。よって原PDF・頁PNG・pdftotext抽出物はローカル未保存、PDF SHA-256は未取得。未取得ファイルのパスやハッシュを捏造しない。アクセス経緯と参照先だけを`../sources/ORB_Rublee_ICCV2011_access_note.md`へ保存した。画像実読／PDFキャッシュ要件は未完了として監督へ引き継ぐ。
