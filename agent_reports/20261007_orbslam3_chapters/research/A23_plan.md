# A23 調査計画：終了要求と結果保存

- manifestの図位置/接続を確認し、wrapper読込ループ終了→System::Shutdown→SaveTimedMapPoints/SaveCameraPosesの無条件順次呼出し→終了コードという一章のみを扱う。初回割当のoptional表現は現行読解により訂正し、optionalなのはShutdown内の設定によるSaveAtlasである。
- 作業者はwrapper引数と出力条件、Shutdownのfinish要求とコメントアウトされた待機部、保存関数の呼出し順・void返却・ログ・ofstreamのopen/write成否の未検査をローカルコードで確認する。create_directoriesに例外処理がなく、正常にreturnまで到達した場合の終了コード規則を区別する。
- 各保存関数がGetAllMapPoints().size()でMapを選ぶこと、両呼出しの選択が別であることを必要範囲で確認する。初回割当の最大KeyFrame数という表現は現行読解により訂正。列/座標/validの詳細はD14/D15へ残し、後続データ章を先行しない。
- Shutdownという名称だけでjoin済み/最適化収束済み/完全スナップショットとしない。保存失敗とwrapper成功コード、追跡成功件数を区別し、静的読解と未実施の実行再現を分ける。
- 公式固定コミットのSystem.cc等をオンライン一次で確認し、custom exportsがローカル既存差分で上流固定版にない点を根拠化する。既存ORB-SLAM3 PDF5頁図1/§IIIの並列構成を本文/画像で再読し、終了手順は現行コードに基づくことを明示する。
- 根拠6〜8件程度をresearch/A23_evidence.mdへ保存して即通知。受領後、小監督が90〜115行程度の本文/自己監査を作成し、大監督へ提出する。コード改変/実行、ビルド、実データ保存や後章調査は行わない。
