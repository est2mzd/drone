# 室内巡回・Worldモデル・RViz：作業記録

記録日：2026-10-06（日本時間）
対象：`/home/takuya/work/drone`

## ログ一覧

- [001：検討整理・実装・検証結果](001_implementation_and_validation.md)
- [002：WorldモデルのRViz対応・起動確認](002_world_model_rviz.md)

## 現在の到達点

単眼SLAM出力からの画像特徴地図とPnP位置推定、手動で定義する実寸YAML World、3D経路計画、停止条件付き制御、AndroidのDry-run指令受信、動画とRViz表示を実装した。**実機の室内自律巡回は未達**。映像から実寸Worldを自動構築する処理、尺度・機体外部パラメータ・現在の障害物観測の実機検証が残る。

## 検証の要点

- 画像特徴地図：11,185点。
- 記述子地図の参照時刻外：44画像中36画像でPnP成立。独立した位置正解率ではない。
- 巡回シミュレーション：97.8秒で4地点を完了。
- Python：12テスト合格。Javaの指令検査：10ケース合格。APKビルド成功。
- RViz：World・経路・軌跡のROS配信を確認。再生完了時、障害物3個、軌跡979点、COMPLETE。

## 成果物の場所

- 実装・操作説明：`patrol/README.md`
- World定義：`patrol/maps/demo.yaml`
- 動画・評価JSON・再生ログ・ソースZIP：`/home/takuya/Documents/Codex/2026-10-06/home-takuya-work-drone/outputs/`

このフォルダは作業履歴、READMEは現在の操作方法として使う。今回までのログをここへ残し、今後も`agent_reports/`内の作業別フォルダにMarkdownで記録する。
