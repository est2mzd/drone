# Mini 3 単眼・室内巡回プロトタイプ（2026-10-06）

## 今回の成果と到達点

既存の映像転送・カメラ校正・ORB-SLAM3を利用して、オフラインの画像特徴地図、地図内でのカメラ位置推定、メートル座標での3D経路計画、停止条件付き速度制御、Androidへの指令受信を追加した。実映像の位置推定と、別の合成室内での巡回を約31秒の動画で表示する。

**実機の室内自律巡回は未達。** 実映像から実寸の障害物地図を自動生成し、その地図でMini 3を自律飛行させた結果ではない。単眼の尺度、ジンバルを含むカメラと機体の座標変換、位置の不確かさ、現在の障害物観測の実機検証が残る。Androidの実機出力は初期状態で無効。

## 検討内容の整理

参照したチャットは「DJI Mini VSLAM構築」「ORB SLAM3可否回答」「ORB SLAM3搭載比較」。ローカルの `user_directions/` と `agent_reports/` も確認した。

- 映像は Mini 3 → RC-N1 → Pixel 8a → Wi-Fi → Ubuntu。既存bridgeと同じ経路を使う。
- 今回の要求は単眼。過去の外付けステレオ＋IMU案とは分けた。SDKの姿勢・速度をraw IMUとしてORB-SLAM3のVIOへ入れない。
- 単眼地図の座標は任意尺度。既知寸法などで測定したSim(3)変換がなければメートルの目的座標へつながない。屋内でGNSSを基準位置や正解軌跡として扱わない。
- 点群全体を飛行地図にする案より、壁・家具を位置と寸法付きのYAMLで管理する案を採用した。画像特徴地図は位置推定、ボックス地図は通行判定に用いる。
- 検出BBox内の深度が揃うことは物体クラスの正しさを保証しない。既存レポートで確認されたため、YOLOクラス名から障害物の実寸や空き空間を自動確定しない。
- ORBの疎な点がない場所を空き空間とは判定しない。明示的に確認した `verified_free` の外は通行不可。
- Mini 3のジンバルは機体と独立して動く。カメラ座標をそのまま機体BODY指令に使わない。今回のruntimeは測定済み外部パラメータと固定ジンバルを要求する。

## 実装

`localization.py` は既存の `t tx ty tz qx qy qz qw valid` を **Tcw（世界→カメラ）** と解釈し、カメラ位置を `-Rcw.T @ tcw` で求める。校正の歪み係数を使ってORB対応点を三角測量し、正の奥行き・視差・再投影誤差で選別する。保存するNPZには3D点、ORB記述子、カメラ内部パラメータ、参照時刻を含む。クエリ画像はORB照合→PnP-RANSAC→LMで、同じ地図座標の姿勢を推定する。ORB-SLAM3のAtlasを再読込する機能ではなく、姿勢出力から別途作る特徴点地図である。

`navigation.py` はメートル単位、Z上向きの3Dボックス地図を使う。障害物を機体半径＋余裕で膨張し、6近傍の3D A*と直線区間の短縮で経路を作る。区間と膨張ボックスの交差は解析的に確認するので、薄い壁をサンプリング間隔で飛び越さない。壁は薄いboxとして登録できる。動的障害物の追加で地図版が変わると再計画する。

`Controller` は速度上限0.25m/s、位置の期限300ms、周囲形状の期限300ms、位置不確かさ上限0.10m、停止距離を扱う。不明尺度・未校正・追跡喪失・観測遅延・経路なし・緊急停止では速度ゼロ。ゼロ速度指令は飛行制御器への目標であり、物理的な即時停止の保証ではない。制動加速度0.30m/s²はシミュレーションの仮定で、機体で未測定。

`runtime.py` は測定済みSim(3)とカメラ→機体変換を適用し、前・右・下の機体座標へ変換する。カメラ位置からカメラ取付位置のオフセットを引いて機体位置を得る。SDK軸の実機確認フラグがなければ提案速度だけを出し、送信用の速度はゼロ。`sigma_m` は検証された推定器から渡す必要がある。現在のPnPは校正済みメートル位置共分散を推定しないため、再投影RMSを位置精度に読み替えてはいけない。

`PatrolCommandBridge.java` はポート5001でNDJSON指令を受信する。64桁hexトークン、セッション、連番、有効期限、有限数、3D速度ノルムを検査する。300ms通信監視と10Hzのゼロ指令を実装した。初期状態 `LIVE_OUTPUT_ENABLED=false` は受信のみでVirtual Stickを有効化しない。実機送信のコード経路は追加したが未検証であり、現在の位置推定結果でこの設定を変更する段階にはない。離陸・自動着陸は実装していない。

`MainActivity.kt` と画面に、トークン入力と手動受信開始・停止を追加した。画面がバックグラウンドへ移ると受信を停止する。ネットワークからarmingを行う機能はない。

## 動画の見方

前半は実際の `20261002_001816.mp4`。画像上の緑点は推定姿勢から投影した地図点。右に任意尺度のXZ地図と軌跡を表示する。`LOCALIZED` はPnPの幾何条件を通った研究用出力であり、飛行に十分な精度を意味しない。失敗時は `LOST` と表示する。

後半は実映像とは別の合成室内。左は3D俯瞰、右は平面地図。4つの指定座標へ巡回する。12〜14秒で位置観測喪失を注入し停止、18秒で新しい障害物を追加して再計画する。シミュレーションの位置・周囲形状は正解値を与えている。画像から推定した位置で閉ループ巡回するデモではない。表示は加速している。

## 再現手順

リポジトリ `/home/takuya/work/drone` で実行する。Python依存はOpenCV、NumPy、PyYAML。動画書き出しにはffmpeg。依存一覧は `patrol/requirements.txt`。

```bash
python3 -m patrol.cli build-map \
  --video mini3_bridge/pc/recordings/20261002_001816.mp4 \
  --poses slam/out/20261002_001816_points_poses.txt \
  --calibration mini3_calib/out/mini3.yaml \
  --reference-end 35 \
  --output patrol/out/landmarks.npz

python3 -m patrol.cli demo \
  --video mini3_bridge/pc/recordings/20261002_001816.mp4 \
  --poses slam/out/20261002_001816_points_poses.txt \
  --map patrol/out/landmarks.npz \
  --world patrol/maps/demo.yaml \
  --output-dir patrol/out/demo

python3 -m unittest discover -s patrol/tests -v
javac -d patrol/out/java-check \
  mini3_bridge/app/src/main/java/com/fsr/djibridge/PatrolCommandGate.java \
  patrol/tests/PatrolCommandGateTest.java
java -cp patrol/out/java-check PatrolCommandGateTest
```

別の映像では先に既存 `scripts/orb_slam3/run.sh` を実行し、そのカメラで測定した内部パラメータと、新しいposesファイルを使う。Mini 3用の校正を別データセットのカメラに流用しない。

目的座標は `patrol/maps/demo.yaml` の `patrol_goals` を変更する。床・壁・家具の `min/max`、確認済み空間、clearanceも同じ地図に記述する。`demo.yaml` は合成部屋であり、実際の部屋の地図ではない。

Androidのビルドは `mini3_bridge` 内で `./gradlew :app:assembleDebug`。今回の最終ビルドは成功した。端末へのインストール、接続、飛行は今回実行していない。既存のDJI App Keyと署名の設定は維持している。

Dry-run通信を端末で確認する際は、PCで `python3 -c 'import secrets; print(secrets.token_hex(32))'` を使ってトークンを発行し、端末へ入力する。同じトークンをファイルへ保存し、次を実行する。

```bash
python3 -m patrol.bridge_cli \
  --host PHONE_IP \
  --token-file TOKEN_FILE \
  --log patrol/out/demo/simulation_log.json
```

このCLIは常にゼロ速度を送る。合成地図の速度を実機の座標と誤認して送らないためである。PCと端末の時計は同期が必要。時計が合わなければ期限検査で停止する。

## 検証結果

- 特徴地図: 30参照フレーム、11,185点。
- 記述子地図の参照時刻は35秒より前。35秒以降の44クエリ中36でPnP成立、8で不成立。
- ORB姿勢との位置差: 中央値0.11297、最大0.44460 **SLAM単位**。メートル・cmへの換算不可。
- CPU推定時間p95は実行ログ `validation.json` に記録。約70ms。映像転送遅延・capture timestamp・コントローラ・端末SDKの全経路遅延ではない。
- 巡回: 合成時間97.8秒で4地点完了。各移動区間の衝突判定を通過。追跡喪失期間の速度は全てゼロ。
- Pythonの意味のある12テスト（ローカルTCP通信を含む）と、Androidから分離したJava指令検査10ケースに合格。
- APK: Android/Kotlin/Java/リソースを含む `assembleDebug` が成功。端末での動作は未確認。
- 動画: H.264、1280×720、yuv420p、約30.87秒。実映像とシミュレーションのフレームを目視確認した。

比較軌跡は同じORB処理から得たもので、独立した正解位置ではない。またORBのpose graphは映像全体を使って最適化されており、「別撮影の完全な未使用データによる精度評価」ではない。PnP成立率81.8%は位置の正解率ではない。大きな位置差が残り、単眼の視差不足や誤対応への対策が必要。

## 実機巡回まで残る作業

1. 固定したジンバル・同一画角で再撮影し、既知距離または測量済み目印で尺度・世界座標とカメラ／機体の外部パラメータを測る。
2. 別撮影の帰還・巡回映像と独立した位置基準で評価し、位置誤差・姿勢誤差・追跡回復・不確かさを測る。現在の位置ずれを先に改善する。
3. 実寸の壁・家具・確認済み空間を登録する。実時間の周囲形状・遮蔽物・未知空間の観測と地図更新を接続する。現在の `add_obstacle` は外部観測の入力インターフェースであり、自動知覚器ではない。
4. 映像のcapture timestampと時計同期、全経路の遅延、通信途絶、SDKの制御権移行、機体BODY軸の正負、制動性能を端末・機体で検証する。
5. 上記の成功後に、人が監視して低速の閉ループ飛行を検証する。上・後ろ・横の死角は前向き単眼映像だけでは現在の障害物を確認できないため、通行範囲やセンサ構成の制約が残る。

## 一次資料

- [DJI MSDK対応製品](https://developer.dji.com/mobile-sdk/): Mini 3はAndroid MSDK対応。
- [Virtual Stick公式仕様](https://developer.dji.com/api-reference-v5/android-api/Components/IVirtualStickManager/IVirtualStickManager.html): Mini 3についてVirtual Stickの機体側障害物回避を前提にしない。
- [Virtual Stickパラメータ](https://developer.dji.com/api-reference-v5/android-api/Components/IVirtualStickManager/Value_FlightController_Struct_VirtualStickFlightControlParam.html)
- [Mini 3仕様](https://www.dji.com/mini-3/specs)
- [ORB-SLAM3公式実装](https://github.com/UZ-SLAMLab/ORB_SLAM3)

自前コードだけを追加し、third_partyの公式実装・ユーザーの既存未コミット変更は保持した。コミット・pushは行っていない。

## WorldモデルをRVizで表示する

```bash
cd /home/takuya/work/drone
scripts/patrol/show_world_rviz.sh
```

灰色のボックスが壁・家具、緑の枠が確認済み空間、橙の枠がclearanceを含む障害物領域、青の球が巡回座標、黄色の球が開始位置。静止表示では開始点から最初の目的座標への計画経路も出す。

今回の巡回ログを再生するには次を使う。ログ中の物体形状のスナップショットを使い、18秒時点で新しい障害物を追加する。

```bash
scripts/patrol/show_world_rviz.sh \
  --log /home/takuya/Documents/Codex/2026-10-06/home-takuya-work-drone/outputs/simulation_log.json \
  --speed 4
```

モデルを変更した場合は `--world YOUR_WORLD.yaml` を指定する。地図が違うログを混ぜない。

ROS 2 Jazzyで `/patrol/world` (MarkerArray)、`/patrol/plan` (Path)、`/patrol/trajectory` (Path) を配信する。Fixed Frameは `patrol_world`、単位はメートルでZ上向き。全topicはReliable・Transient Localで、後からRVizを開いても最新の内容を受け取れる。任意尺度SLAMの `map` とは座標を分ける。

この環境では既定のGPU描画が失敗したため、launcherはソフトウェア描画を既定にした。DDSは検証済みのCycloneDDS、ドメイン77、ローカル通信を既定にする。全てこのプロセスの環境変数のみで、システム設定は変更しない。既存の環境で調整する場合は `LIBGL_ALWAYS_SOFTWARE`、`RMW_IMPLEMENTATION`、`ROS_DOMAIN_ID` で上書きできる。

検証: メッセージの寸法・座標・frame・19個の初期markerを確認。実際のROS購読でWorld・計画経路・軌跡の配信を確認し、再生終了時に障害物3個・軌跡979点・COMPLETE状態を確認した。RVizはソフトウェア描画でOpenGL 4.5を初期化し起動した。画面キャプチャはこの環境では取得できなかったため、RVizスクリーンショットは添付していない。
