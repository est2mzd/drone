# やったこと

見たいものは動画。背景が黒で、残したものだけが見える。まとめは [005_summary.md](005_summary.md)。4面の意味と、自己位置・地図との関係は [004_pose_and_map.md](004_pose_and_map.md)。

## 動画

| ファイル | 長さ | 中身 |
| --- | --- | --- |
| [videos/20261002_001816_compare.mp4](videos/20261002_001816_compare.mp4) | 58秒 | Mini 3 の保存映像。机とモニタ |
| [videos/001_7faZ9Blu_OI_compare.mp4](videos/001_7faZ9Blu_OI_compare.mp4) | 12秒 | 壁の額 |
| [videos/003_HtFq9C_vbOc_compare.mp4](videos/003_HtFq9C_vbOc_compare.mp4) | 12秒 | 東京の部屋。途中は窓の外 |
| [videos/004_8lz3Qs23cMg_compare.mp4](videos/004_8lz3Qs23cMg_compare.mp4) | 12秒 | ロフト |
| [videos/005_7P5KWUDd4UM_compare.mp4](videos/005_7P5KWUDd4UM_compare.mp4) | 12秒 | 寝室 |
| [videos/008_IXc2JJGk3oE_compare.mp4](videos/008_IXc2JJGk3oE_compare.mp4) | 12秒 | ハンブルクの室内 |
| [videos/009_0M7AJOC3zT4_compare.mp4](videos/009_0M7AJOC3zT4_compare.mp4) | 12秒 | 自宅オフィス |
| [videos/011_pexels_compare.mp4](videos/011_pexels_compare.mp4) | 8秒 | 居間の壁 |
| [videos/012_pexels_compare.mp4](videos/012_pexels_compare.mp4) | 8.5秒 | 廊下 |
| [videos/013_pexels_compare.mp4](videos/013_pexels_compare.mp4) | 8.5秒 | ソファ |
| [videos/014_pexels_compare.mp4](videos/014_pexels_compare.mp4) | 8.5秒 | アパートの台所 |
| [videos/015_pexels_compare.mp4](videos/015_pexels_compare.mp4) | 8秒 | キッチン |
| [videos/016_pexels_compare.mp4](videos/016_pexels_compare.mp4) | 6秒 | 黒いキッチン |
| [videos/017_pexels_compare.mp4](videos/017_pexels_compare.mp4) | 8秒 | 自宅オフィス |

## 試しの一覧

| # | 試し | 結果 | 詳細 |
| --- | --- | --- | --- |
| 1 | 箱の内側で相対差15%、面積50%以上を物体にする | 99件中96件が通る。ほぼ落ちない | [002](002_bbox_depth_result.md) |
| 2 | 相対差を10%と5%に狭める | 10%は84/99。5%は52/99。テーブルは5%で0/8 | 同じ |
| 3 | 5%で揃った画素が一つの塊か | 52件中45件が一つの連結成分 | 同じ |
| 4 | QuadricSLAM。厚み/長辺が0.20未満なら平面 | 102件中40件が薄い。2枚で対応できた組は18 | [003](003_paper_verification.md) |
| 5 | Liao ら。重力から10度以内の面を支持平面にする | 支持平面は7/28フレーム。乗る箱は25/102 | 同じ |
| 6 | CubeSLAM。12本以上が3度以内で交わる点を消失点とする | 消失点が2つあるフレームは16/28 | 同じ |
| 7 | Kimera。画像の12%以上の面を構造とする | 28/28フレームにある。重なる箱は43/102 | 同じ |
| 8 | 4面を静止画で並べる | 8枚。動きは見えない | [figures/](figures/) |
| 9 | 同じ4面を動画にする | 14本。上の表 | [videos/](videos/) |
| 10 | 対数深度の勾配が小さい最大の塊が箱の50%以上か | 1133箱中988。勾配でも大半は一つの滑らかな面 | [video_trials.yaml](video_trials.yaml) |
| 11 | 第一の山の外に25%以上の第二の山があるか | 1133箱中210。混在として落とせるのは約2割 | 同じ |

10と11は、動画の313フレーム（Mini 3 は毎秒1枚、他は毎秒2枚）で数えた。支持平面が出たフレームは55/313。12%以上の面は313/313で、Mini 3 の動画では画面の大半が黄色になる。この閾値の「広い面」は壁一枚ではなく、奥行きがなだらかな領域ごとを一枚の面にしている。

## いま言えること

深度が揃うことと、勾配が小さいことは、どちらも箱の大半を通す。第二の山がある箱だけが、一つの物体ではない候補として約2割残る。支持平面はフレームの2割弱にしか無く、物体の切り出しには足りない。
