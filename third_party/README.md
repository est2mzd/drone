外部のソースを置く場所。このディレクトリの中身は `README.md` と `depth_anything3/overlay.py` 以外 `.gitignore` に入っていて、このリポジトリの追跡対象には含めない。クローン、固定コミット、ビルド、Depth Anything 3 の仮想環境のコマンドはリポジトリ直下の README「環境設定」にある。

| ディレクトリ | 内容 | 固定 |
| --- | --- | --- |
| `Mobile-SDK-Android-V5/` | DJI Mobile SDK V5 の公式ツリー。参照用。アプリのビルドには Maven の MSDK 5.18.0 を使い、ここは Gradle モジュールにしない | `dev-sdk-main` の `a48aa4e7` |
| `ORB_SLAM3/` | ORB-SLAM3。`slam/` がリンクする。時刻付きの点と姿勢は `slam/patches/orbslam3_timed_points.patch` を当てた差分 | `4452a3c4` |
| `Pangolin/` | Pangolin v0.6 のソース。ORB-SLAM3 のビルド依存。gcc 13 向けに `slam/patches/pangolin_gcc13.h` を読ませ、FFmpeg 対応は切る | `dd801d24` |
| `pangolin-install/` | Pangolin のインストール先。Git リポジトリではない。`slam` の CMake はここを `CMAKE_PREFIX_PATH` にする | cmake install |
| `depth_anything3/` | 保存した映像へ Depth Anything 3 の深度と箱を重ねる自前スクリプト。モデル本体は Hugging Face の `depth-anything/DA3-SMALL` | `overlay.py` だけ Git に入る |
