# ログ仕様 1.0.0

## ファイルと確定処理

1. 推測困難なセッションIDの新規フォルダーを作り、`INCOMPLETE` を永続化する。
2. `metadata.json` を保存し、`journal.csv` のヘッダを書き、Flush(true)が成功してから開始する。
3. journalへイベントとサンプルを混在追記。単一スレッドで順序を確定。約1秒間隔と中断時にFlush(true)。遅い書き込みはメインスレッドを止めるため、続くフレーム停止検出で実験も停止する。
4. 終了イベント→Flush→journal再読込→連番、件数、サンプル順序、最終時刻、最終イベントを検証→2種類のCSVを一時名で出力して確定→`complete.json` を最後に作る。
5. `complete.json` はjournal・metadata・解析CSVのSHA-256と件数・最終連番・時刻を含む。作成時の `INCOMPLETE` は履歴として残す。マーカーだけを盲信せず、復旧ツールで内容を検証する。

CSVはUTF-8、ヘッダあり、数値はInvariantCulture、引用符・改行・カンマはCSVエスケープ。生ログと正常終了CSVは同じ27列。ファイルはセッションをまたいで上書きしない。途中ファイルを正常終了に変更する機能はない。

## メタデータ

- sessionId、trialId（初版は1セッション1試行）、匿名participantCode、condition、startUtc（ISO8601 UTC）。
- applicationVersion、sceneVersion、logVersion、visitRuleVersion、元マスターと派生アセットのSHA-256。
- sampleHz、walkSpeed、eyeHeight、fieldOfView（垂直・度）、旋回速度、滞在閾値、領域寸法・ヒステリシス、フレーム停止閾値、フラッシュ間隔。
- Unityバージョン、実行プラットフォーム、アプリ版、画面寸法、fullscreen、表示/入力方式。
- 48店舗の領域定義（id/name/kind/side/x/z/halfX/halfZ）を設定値として丸ごと保存。

## journal列

| 列 | 定義 |
|---|---|
| type | event / sample |
| seq | 全レコード通し連番。0から、欠番不可 |
| t_s | Stopwatchによる開始後の実測単調時刻（秒）。UTCやframeから生成しない |
| sample_seq | サンプルだけの0始まり連番。イベントは-1 |
| frame | 補助的なUnity frameCount。時刻の代用にしない |
| state | Running / Paused / Aborted等の実験状態 |
| input_mask | ↑1、↓2、←4、→8、A16、D32、PageUp64、PageDown128のbit OR |
| locomotion | None / Keyboard / Stick / Physical / Teleport / Reset。初版が入力するのはNone/Keyboard/Reset |
| root_x/y/z_m、root_qx/qy/qz/qw | アバターrootの世界座標とQuaternion |
| camera_x/y/z_m、camera_qx/qy/qz/qw | カメラの世界座標とQuaternion。rootとは独立 |
| root_speed_m_s | 実際のroot水平変位÷観測フレーム間の実測秒数 |
| walk_distance_m | 有効な観測フレームのroot水平変位を累積。リセット・テレポートを除外 |
| stall_id | 店舗イベントのid。その他0 |
| event | 下記イベント種別。sampleでは空 |
| detail | 判定理由、欠落スロット数、リセット元位置等 |

移動状態はlocomotion・root_speed・input_maskを組み合わせて表す。歩行距離は20Hzサンプル間の直線距離の和ではなく、各フレームのroot変位の和。sampleだけから再計算すると曲がり角で短くなる可能性があり、保存済み累積値と区別する。カメラの姿勢は眼球視線や関心の証拠ではない。

## 時間・欠落・中断

初期サンプルはt=0。以降、スケジューラの予定時刻を過ぎたフレームで1件だけ記録し、実際の取得時刻を付ける。長いフレームを同じ位置の複数サンプルで埋めない。飛ばした予定スロットを `sample_missing` に記録する。単調時刻はイベントを含め非減少、サンプルは厳密増加。

`frame_gap`（初期値0.25秒超）で観測不能区間を明示し、1件の現在位置を記録して停止する。実装側の移動もそのフレームは行わない。停止中の軌跡サンプリングは行わず、pause/resume/focusイベントで区間を示す。再開時にサンプリング時計を再設定するので、中断時間をサンプル欠落として計上しない。

## 訪問判定 rect-hysteresis-low-speed-v1

各店舗中心から内側へ2.7mの位置に長方形を置く。間口3.0m、奥行2.0m。南北店舗は半幅(1.5,1.0)、東西は(1.0,1.5)。rootの水平位置で判定する。領域は実験画面へ描画しない。

- 初回進入：内側の長方形へ入った時にregion_enter。
- 退出：四辺を外へ0.15m広げた長方形から出た時にregion_exit。境界上は内側。
- 滞在：領域内でroot速度≤0.3m/sが3秒継続。連続する2観測点がともに低速の区間だけ加算。進入フレームより前の時間は加算しない。
- 速度超過、退出、中断、reset、endで成立中のdwellを終了。中断は低速時間を0へ戻す。再開後に新たに3秒必要。
- 2回目以降の領域進入でrevisit。滞在を伴わない再進入も含むため、興味・購買意図・滞在再訪と同一視しない。滞在を伴う再訪は生ログから別途定義する。

## イベント

start、end、abort、pause、resume、reset、focus_lost、focus_gained、input_change、region_enter、region_exit、dwell_start、dwell_end、revisit、sample_missing、frame_gap、discontinuity、save_error。

save_errorの保存自体が失敗する場合がある。この時は画面のエラー表示とcomplete.jsonの不在が識別手段。終了要求やウィンドウ閉鎖はabortとして未完了のまま残す。OS killや電源断ではabortイベントを残せない。最後に永続化されたレコードまでを復旧対象とする。

## 今後のXR拡張

IMovementInput / ILocomotionRig / SessionEngine / IJournalを分離。OpenXR追加時もUnity(x,y,z)=Blender(x,z,y)、1m単位を維持。頭部poseはcameraへ、移動原点はrootへ記録する。身体トラッキングの揺れをrootへ合算しない。実歩行を計測する場合は明示的な追跡身体root定義と校正が必要。テレポートはdiscontinuityとして距離を分離し、Stick/Physical/Teleportを区別する。初版にHMD実装や実機確認の実績はない。
