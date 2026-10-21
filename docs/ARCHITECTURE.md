# 責務の分離

| 層 | 実装 | 責務 |
|---|---|---|
| 入力 | IMovementInput / KeyboardInput | キーを移動コマンドとbitmaskへ変換 |
| 移動・表示 | ILocomotionRig / DesktopRig | CharacterController、rootとcameraの分離、速度・FOV |
| 実験進行 | ExperimentApp | 匿名コード/条件入力、フォーカス、明示開始/終了、キー解放待ち、UI |
| 判定 | SessionEngine / VisitDetector / SampleClock | 実測時刻、状態機械、領域・滞在・再訪、歩行距離 |
| 保存 | IJournal / FileJournal | 追記、Flush(true)、監査、解析CSV、最後の完了マーカー |
| 導入 | export_unity.py / EnnichiImporter / ProjectSetup | マスター保護、座標変換、派生アセット、再現設定 |
| 解析補助 | recover_logs.py | 読取監査、未完了ログの有効先頭部分を別出力へ回収 |

CoreアセンブリはUnityへの参照なし。クラウドC#テストとUnityが**同じソース**をコンパイルする。Pythonで同じアルゴリズムを再実装したテストだけでC#を検証したことにはしていない。

RunningからPausedへの移行は手動、フォーカス喪失、アプリ中断、フレーム停止、リセット。PausedからRunningは明示操作だけ。保存例外はFaultedへラッチし、そのセッションでは回復して実験を継続しない。正常EndだけがCompleted。ウィンドウ閉鎖はAborted、強制終了はcompleteマーカー不在のIncomplete。

UI処理・フレーム更新・保存はUnityメインスレッド内で順序を固定。バックグラウンド書込キューは採用せず、満杯キューの欠落や終端競合を避ける。ただし遅いディスクではフレーム停止する。実験PCの実測で同期書込が要件を満たさない場合は、明示的なキュー長・ドロップイベント・終了時drain保証付きの別IJournal実装へ置換する。

将来OpenXRを追加する場合、入力/rigを交換し、SessionEngineとIJournalを保持する。HMD実機を使わないまま頭部追跡・実歩行・テレポートの安全性や精度を認証しない。Camera orientationとeye gazeは別データであり、眼球計測を追加するときは新しいセンサー・校正・ログ版として扱う。
