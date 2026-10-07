# A21 調査計画：現在地図のリセット

- 図Bの現在地図リセット、A19からA21を経てA22へ接続する章だけを扱う。純MONOCULAR・通常SLAMでSystem要求が次回TrackMonocularに消費される経路を対象とする。
- 作業者はSystemの要求/消費、Tracking::ResetActiveMapの既定引数を伴う経路、LocalMapping/LoopClosingへのactive map reset要求と完了待ちを必要範囲で確認する。全停止や全処理終了と同一視しない。
- KeyFrameDatabase::clearMap、Atlas::clearMap、Map::clearの対象と操作を照合する。同一Mapオブジェクト/IDの再利用、他地図の保持、deleteコメントと集合消去の相違を記録し、全メモリ解放と断定しない。
- Tracking側の状態/Frame/参照/初期化情報/履歴lost印を確認する。全Atlas消去・全ID初期化・全履歴削除ではない点を、全体Resetとの必要最小限の比較で説明する。A20新規Map追加との違いを整理し、A22次入力の詳細へ先行しない。
- 公式固定コミットの対象コードをオンライン一次で照合し、既存ORB-SLAM3 PDF5頁図1/§III Atlas・Trackingの本文/画像を再読する。現行リセット手順はコード根拠であり、論文概説と区別する。
- 根拠6〜8件程度をresearch/A21_evidence.mdへ保存して即通知。受領後、小監督が80〜115行程度の本文/自己監査を作り、大監督へ提出する。コード実行/変更、ビルド、メモリ動作の再現検証は行わない。
