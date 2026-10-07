# A11 追跡の成立判定：根拠メモ

確認日：2026-10-07。対象は純単眼 `MONOCULAR`・通常SLAM（`mbOnlyTracking=false`）。ORB-SLAM3固定版 `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4`。以下の行番号はローカル `third_party/ORB_SLAM3/src/Tracking.cc`。同ファイルは固定版から未変更。

|項目|確認結果|ローカル根拠|
|---|---|---|
|数える対象|`mnMatchesInliers` を0にし、現在フレームの各特徴スロットについて、MapPoint対応あり・最適化後の外れ値フラグが偽・`Observations()>0` の場合に加算する。生のORB特徴数でも、重複除去したMapPoint集合の大きさでもない。|3004–3025|
|第1判定|`currentFrameId < lastRelocFrameId + mMaxFrames` かつ点数 `<50` なら即false。以後の例外では覆らない。秒の比較ではなくFrame ID比較。`mnLastRelocFrameId` 初期値は0であり、実際の再局在成功後だけ発動するとは限らない。`mMaxFrames` は設定側FPSから代入される。|3030–3031、48、585（旧設定読込は1152–1158）|
|第2判定|第1判定で戻らなかった場合、点数 `>10` かつその時点の `mState==RECENTLY_LOST` ならtrue。`>=10` ではない。|3033–3034|
|通常単眼の最終判定|IMU分岐を通らない通常MONOCULARでは、点数 `<30` がfalse、それ以外がtrue。従って第2判定の例外がなければ30点以上を受理する。|3037–3061（特に3055–3061）|
|呼出し側への反映|通常SLAMでは既存の `bOK` がtrueのときだけ `bOK=TrackLocalMap()`。falseなら局所地図追跡は呼ばれない。その後trueなら状態をOKへ更新。falseの場合は、その時点で状態がOKの場合だけRECENTLY_LOSTへ変更し、現在画像時刻を記録する。falseで常に同じ状態へ上書きする処理ではない。|2122–2131、2142–2162|

## 条件順序の整理

`n=mnMatchesInliers` は上記の対応スロット数（単位：個）、`r=(currentFrameId < lastRelocFrameId+mMaxFrames)`、`s` は判定時の状態とする。純単眼では上から順に、① `r && n<50` → false、② `s==RECENTLY_LOST && n>10` → true、③それ以外 → `n>=30`。これはコードを整理した規則であり、論文掲載式ではない。

入力を仮定した境界例：`r=true,n=49,s=RECENTLY_LOST` は①でfalse。`r=false,s=RECENTLY_LOST` は10点でfalse、11点でtrue。`r=false,s=OK` は29点でfalse、30点でtrue。例外経路の実動画での到達性を測定した例ではない。`mMaxFrames` はフレーム数として使われる設定値で、ラッパーの `CAP_PROP_FPS` 取得値や時刻差から直接計算した秒数ではない。

## 一次資料・PDF実読

- [公式固定コミット Tracking.cc](https://raw.githubusercontent.com/UZ-SLAMLab/ORB_SLAM3/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc)：計数・50条件・`>10`例外・30条件をネット本文でも確認。Web表示の整形行番号ではなく上表のローカル行番号で追跡する。
- [ORB-SLAM原論文 v2](https://arxiv.org/pdf/1502.00956v2)：PDF8頁＝誌面7頁、V.D “Track Local Map”の本文とページ画像を再読。局所地図点との対応を増やして姿勢を最適化する説明を確認。現行コードの上記50/10/30の順序付き成立条件は、この段落の記述から導かない。同頁V.Eの50点条件は新キーフレーム挿入の条件であり、本章の追跡受理条件と混同しない。
- キャッシュ：`sources/ORB_SLAM_1502.00956v2.pdf`、同 `.txt`、`sources/ORB_SLAM_1502.00956v2_page-08.png`（画像実読済み）。

未確認・限界：実行・実動画による判定回数や精度測定は未実施。受理は実装上の対応数と状態による判定で、真の姿勢精度や今後の追跡継続を保証しない。A12以降の喪失処理には進んでいない。取得障害なし。
