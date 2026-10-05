# WorldモデルのRViz表示：作業ログ

記録日：2026-10-06（日本時間）。前の実装からWorldモデルのRViz配信を追加した作業の記録。

## 変更ファイル

- `patrol/rviz/world_model.py`：YAML WorldのMarkerArray配信、計画経路・軌跡のPath配信、シミュレーションログ再生。
- `patrol/rviz/world_model.rviz`：World・経路・軌跡・メートルのグリッドの表示設定。
- `scripts/patrol/show_world_rviz.sh`：ROS環境と描画環境を設定して起動。
- `patrol/demo.py`：シミュレーションログに各時刻の物体形状を保存。
- `patrol/README.md`：実行方法と検証結果を追記。

## 起動・検証結果


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


## 作業中の問題と対処

- 初期Marker数のチェックで17個と想定したが、実際は19個だった。内訳を確認してチェックを訂正した。
- 既定のGPU描画ではMesa/irisの初期化に失敗した。`LIBGL_ALWAYS_SOFTWARE=1`でRVizのOpenGL初期化を確認した。
- 最初のDDS構成では別購読ノードが配信を受け取れなかった。CycloneDDSへ切り替え、3topicの購読と再生完了を確認した。
- RViz画面キャプチャは黒画像になり、XCompositeでも取得できなかった。黒画像は削除し、スクリーンショットとして納品していない。
- 最後のテストプロセス停止操作はツールの承認ポリシーに拒否された。その時点でRVizは起動したままと報告した。現在のプロセス状態は本ログ保存時には再確認していない。

## 制約

表示モデルは合成室内。実際の映像から実寸Worldを自動構築した結果ではない。実機巡回や飛行指令の送信は実施していない。
