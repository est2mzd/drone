# A09 調査計画

- 図A「姿勢を予測・照合」、D06/D08/D10→A10。純単眼・通常SLAMのTrackReferenceKeyFrame/TrackWithMotionModelと失敗時fallbackを扱い、A10の局所地図拡大・探索は調べない。
- 作業者はTrackingの分岐、CheckReplacedInLastFrame、UpdateLastFrame、速度更新/適用、ORBmatcherの対応探索、Optimizer::PoseOptimizationの必要行を確認。MapPointは固定、現在Frameの姿勢だけ変数となることを確認する。
- 予測式のTcw、前画像の姿勢、相対変換mVelocityの積順序と座標系を確認。時間差で正規化する速度量ではないこと、等時間間隔の近似と実装のtimestamp非使用を区別する。
- 公式固定コミットソースをネット一次資料として確認。取得済みORB-SLAM原論文PDFのV.Bおよび姿勢最適化のAppendixを本文・必要頁画像で再読。式は実読箇所・現行コードと照合し、旧論文との差を記録する。PDF追加取得はしない。
- 6〜8件、必要十分な短い根拠表を research/A09_evidence.md に保存。式の全記号/フレーム/単位とコード由来か論文由来か、論文頁/節、未確認点を含む。閾値の網羅調査は不要。
- 受領監査後、小監督が chapters/09_A09.md を90〜120行目安で執筆、reviews/A09.md へ自己監査。A06の同時姿勢・点調整との違いを示し、A10へ渡す初期姿勢・対応までで止める。
