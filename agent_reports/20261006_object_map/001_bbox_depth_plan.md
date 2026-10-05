# 段1 作業計画: 箱の内側で深度が揃うかを測る

小監督者。大監督者の `000_chief_plan.md` で段1の承認済み。この段の範囲だけを作業する。

## 作業者が作るもの

`object_map/extract_objects.py`

1枚の画像について、次を `object_map/out/<映像名>/f######.yaml` に書く。

- 検出器 `yolo11n` の箱とクラスとスコア。
- 箱の各辺から 10% 内側の範囲。縁は背景が混ざる、という RGB-D の物体 SLAM で既に言われている選別を、割合の計算の前に置く。
- 内側の深度について、相対差 15% に最も多くの画素が収まるときの割合と、その画素の深度中央値。
- 割合が 50% 以上、かつ内側の面積が 400 画素以上なら `accepted: true`、理由 `agree`。
- そうでなければ `depth_split`、`small_box`、`empty_depth`。
- `person` `dog` `cat` `bird` は `dynamic: true`。深度が揃っても、この段の採用フラグとは別に印を付ける。地図へ入れる静止物かは段4でこの印を見る。

深度は `depth-anything/DA3-SMALL`、長辺 504、1枚ずつ。`third_party/depth_anything3/overlay.py` と同じ呼び方。YAML の `depth_unit` は `relative`。メートルの `position_xyz` は書かない。

## データ

- 手元: `mini3_bridge/pc/recordings/20261002_001816.mp4`
- ネット: `object_map/video_sources.txt` の10本。先頭12秒を `object_map/videos/` に保存する。出典 URL は残す。映像と検出の重みは Git に入れない。

各映像から等間隔に2フレーム。

## 検査

モデルを読む前に、`extract_objects.py --self-check` で次を確認する。

- 一様な深度は割合 1。
- 60% が深度 1、40% が深度 5 なら割合 0.6、中央値は 1。
- 深度 1 と 1.1 が半々なら、相対差 15% では一つにまとまり割合 1。
- 小さい乱数の深度で、総当たりと同じ割合になる。

## 作業者の分担

- 作業者A: 室内映像10本の取得と出典一覧。
- 作業者B: 観測スクリプト、自己検査、Mini 3 と取得映像の実行、`object_map/out/summary.yaml`。

## この段が終わったときに小監督者が見ること

`summary.yaml` のクラスごとの採用率と、不採用理由の内訳。重ね画像を数枚見て、採用した箱が一つの物の上にあるかを確認する。世界地図の作業には入らない。結果は `002_bbox_depth_result.md` に書き、段2の計画は大監督者の承認を取ってから書く。
