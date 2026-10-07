# A04 調査計画：グレー化と特徴抽出

- 対象はA04のみ。図A `[画像中の目印を取り出す]`、DFD `[グレー化・特徴抽出]`。D05画像/時刻・D03校正→D06 Frame→A05。
- 実働作業者が根拠を保存・報告した後、小監督が`chapters/04_A04.md`を執筆する。A05以降の調査は禁止。

## 必要な調査

1. ローカル`Tracking::GrabImageMonocular`→単眼Frame→ORBextractorの現行呼出し経路を実読。グレー化、通常/初期用抽出器選択、5*nFeatures設定、抽出・特徴点歪み補正・記述子・MapPoint未対応の順を関数/行番号で確認。
2. `ORBextractor::operator()`が実際に呼ぶ`ComputeKeyPointsOctTree`、画像ピラミッド、FAST、分布調整、IC_Angle、GaussianBlur、computeOrbDescriptorの役割を現行経路で追う。未使用ComputeKeyPointsOldのHarris系を混ぜない。
3. ORB原論文 *ORB: an efficient alternative to SIFT or SURF*（Rubleeほか、ICCV 2011）のPDFを正規一次配布元/大学等の正当な論文配布から取得または再利用。本文・式・図の必要ページを画像でも実読し、URL/版/頁/節/式番号を記録。取得失敗は長く待たず別の正規配布を試し、未確認なら速やかに報告。
4. ネット一次情報は著者/出版社/公式OpenCV文書を実読。ORBの入力/出力とグレー画像、ピラミッド、FAST（Features from Accelerated Segment Test）、方向、BRIEF（Binary Robust Independent Elementary Features）の意味を裏付ける。
5. 教材式候補は(a)スケール画像の対応、(b)重心モーメントm_pqと方向atan2、(c)回転比較による1bit記述とHamming距離。必要最小限に選び、全記号の型/次元/単位/画素座標/比較順を定義可能にする。FASTはしきい値を言葉と簡単な不等式で説明できれば十分。グレー化の係数を使うなら対応する公式一次根拠が必要。
6. 実装はIC_AngleのfastAtan2が度を返し、記述子でラジアン換算、記述子32bytes/256bit。原論文のHarris上位選別と現行OctTreeによる分布選別との差を明示。原論文の式を手元実装そのものと断定しない。
7. 特徴点は2次元の画素位置、記述子は比較用bit列、MapPointは3次元地図点。指定nFeaturesや初期5倍値を必ず検出する保証としない。Frameは画像全面を先に歪み補正する説明ではなく、抽出後の特徴点座標を補正する経路を確認する。

## 提出

`research/A04_evidence.md`へ約2000字を目安に、必要なコード/論文の根拠表、式の出典と記号注意点、未確認点を保存。原論文取得分で増えても重複した長文解説は不要。PDF/抽出テキスト/必要ページ画像は`sources/`へ再利用可能な名前で保存。コード改修、実行、ビルド、インストール、進捗表更新は禁止。

## 原論文追補の追加割当

A05大監督合格・3秒待機完了後、A04原論文追補を単独の改訂作業として正式割当。A05は変更せずA06は先行しない。

1. 著者公開の成功候補URL `https://www.researchgate.net/profile/Gary-Bradski-4/publication/221111151_ORB_an_efficient_alternative_to_SIFT_or_SURF/links/00b4951c369020213a000000/ORB-an-efficient-alternative-to-SIFT-or-SURF.pdf` を取得し、原論文の題名/著者/ページを確認して`sources/`へ保存する。URLは取得成功を確認するまで候補として扱う。
2. 必要ページの本文を抽出し画像で実読する。親情報ではPDF2頁§3.2式(1)-(3)、3頁§4.1式(4)-(6)だが、これを鵜呑みにせず実頁で確かめる。図が理解に関係する場合も実読する。
3. 重心のm00除算、方向、BRIEF比較と回転、12度刻みの参照表の記載箇所を確認。既存章のコード整理式と、原論文の式の一致点/差を短い根拠表へまとめる。現行コードはm10/m01直接方向、回転座標cvRound、連続角度sin/cosによる計算であり、論文と同一の式番号を付けない。
4. `research/A04_evidence.md`へ原論文実読追補を保存。初回の取得失敗履歴は残し、新URLでの成功/確認時点を明確にする。長い理論本文は不要。保存したPDF・頁画像・抽出文のパス、SHA-256、頁/節/式番号、コード対応、残る未確認を報告。
5. 小監督が根拠受領・監査後、本文の原論文未読の記載を更新し、必要な式対応/実装差だけを追補する。
