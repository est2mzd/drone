# D05 調査計画：画像とフレーム時刻

- 図DFDの画像・フレーム時刻、A03→A04,D06。入力対(I_k,t_k)の受渡しに限定し、A03/D01/D02の既存根拠を再利用する。
- 実workerはwrapper46–47→System::TrackMonocular const参照/clone/必要時resize→GrabImageMonocular→FrameコンストラクタのmTimeStampとmnId/nNextIdを必要箇所だけ確認する。
- 画像配列/画像順番号/相対秒/Frame IDを区別し、組の意味・次元・double時刻・k/fの有限正等間隔前提と小例を整理する。D06内部の先行なし。
- 固定公式System/Frameの該当接続、既存PDF5頁図1/IIIの本文画像を再確認し、3〜5件表をresearch/D05_evidence.mdへ保存・即通知する。新資料/型一般論の拡張/実行は不要。
- 受領後、本文60〜80行と自己監査をまとめて保存・提出する。設定/ソース変更・次章調査は禁止。
