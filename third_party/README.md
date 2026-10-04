外部のソースを置く場所。このディレクトリの中身は `README.md` 以外 `.gitignore` に入っていて、このリポジトリの追跡対象には含めない。

| ディレクトリ | 内容 |
| --- | --- |
| `Mobile-SDK-Android-V5/` | DJI Mobile SDK V5 の公式ツリー。参照用。取得手順はリポジトリ直下の README にある。 |
| `ORB_SLAM3/` | ORB-SLAM3。`slam/` がリンクする。 |
| `Pangolin/` | Pangolin のソース。ORB-SLAM3 のビルド依存。 |
| `pangolin-install/` | Pangolin のインストール先。`slam` の CMake はここを `CMAKE_PREFIX_PATH` にする。 |
