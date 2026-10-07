# P03 調査計画：LoopClosingの補正と地図統合

- 対象は並行図/DFDのLoopClosing、接続D09,D07,D10→D12。純MONOCULAR通常SLAMでRun/NewDetectCommonRegionsから同一MapのCorrectLoopと別MapのMergeLocalへ進む流れを調べる。D12データ詳細と次章は先行しない。
- 実作業者はキュー、BoW候補と幾何検証、Sim3推定/共視での検証、merge優先とloop解除、同一Map/別Mapの分類を現行コードで確認する。旧論文の連続3候補則を現行へ転記しない。
- CorrectLoop/MergeLocalのLocalMapping停止待ち、点融合、姿勢/点補正、グラフ/BA呼出しを確認。純monoではMergeLocalの後半EssentialGraphを通らず、welding BAは受け取ったmerge側window固定。CorrectLoopのGBA条件とMergeLocalのbRelaunchBA条件を区別する。
- Sim3の最小座標式と全記号/単位/方向を整理する。グラフ誤差の新導出は不要、A20の新Map開始との違いを示す。BAは目的/可動・固定対象/非同期/中断と結果反映の保証範囲に絞る。
- 公式固定LoopClosing/Optimizer等の必要箇所をオンライン一次で照合し、取得済みORB-SLAM3と旧ORB-SLAMの場所認識/loop/merge/Sim3の該当本文・図・式をPDF画像でも実読。必要ページのみ既存PDFから描画し、新規PDFは不要。
- 根拠は8件程度の表と必要式をresearch/P03_evidence.mdへ保存し、即通知する。KeyFrameDatabaseのbad候補continue時の進行、継続候補Sim3の採用については未再現の静的観察に限定し、深い不具合調査/修正へ拡張しない。
- 受領後、小監督が130〜160行を目安に章と自己監査を執筆する。コード変更/ビルド/実行は禁止。
