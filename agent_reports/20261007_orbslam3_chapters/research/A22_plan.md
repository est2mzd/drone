# A22 調査計画：再初期化への復帰

- 図位置/接続をmanifestで確認し、純MONOCULAR・通常SLAMの再初期化への復帰だけを扱う。
- A20は喪失した画像のTrack中にNO_IMAGES_YETを設定してreturn、A21は次回TrackMonocularのGrab前に要求を消費しNO_IMAGES_YETへ戻す。二つの時点差とその後の共通経路を確認する。
- 実作業者はwrapper入力継続→System::TrackMonocular→Tracking::GrabImageMonocularでFrame構築→TrackのNO_IMAGES_YETからNOT_INITIALIZEDへの変更→MonocularInitializationを、必要行だけローカルで読む。
- Mapの容器の存在と初期化済み状態を区別する。初期化候補解除後の再試行、初期化不成立時returnを最小限で確認し、特徴/対応/二視点成立の詳説は既存A05〜A07へ参照する。次画像一枚で必ず完了するとは書かない。
- 固定コミットの公式Tracking/System等をオンライン一次で照合し、既存ORB-SLAM3 PDF5頁図1/§III Trackingの本文/画像を本章視点で再読する。新PDF取得は不要。
- 4〜5件の根拠をresearch/A22_evidence.mdへ保存して即通知。受領後、小監督が55〜75行程度の本文と自己監査を作る。A23先行、コード実行/変更は行わない。
