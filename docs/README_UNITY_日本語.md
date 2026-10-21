# 縁日デスクトップ実験アプリ（実装初版）

これは**実験参加者への配布前の実装**です。Unityでのコンパイル・実機操作・描画性能と、派生モデルの見た目の承認は別の検証項目です。最新の実施結果は `VALIDATION.md` を参照してください。クラウド同期・OpenXR/HMDは実装していません。

## 固定する環境

- Unity Editor **6000.0.65f1**、Built-in Render Pipeline、C#、Windows x64/Monoを基本ターゲット。
- macOSはStandaloneOSX/Monoのビルド入口を用意。実機・署名・配布・Gatekeeper対応は未検証。
- Blender **5.2.2 LTS**（マスターと一致）、派生アセット形式2。
- 中核テストは .NET SDK **8.0.408**。Pythonツールは標準ライブラリのみ（クラウド検証は3.12.14）。
- Unityのパッケージは `Packages/manifest.json` / `packages-lock.json` に固定。外部レジストリのランタイム依存なし。builtinモジュールの実際の解決は最初のUnity起動で確認する。

## 共同研究者向けの再現手順

以下は権限・ライセンス・対象モジュールが用意された**後の手順**です。このタスクでユーザーPCを操作したという意味ではありません。

```bash
git clone https://github.com/t-inamura/vr-ennichi.git
cd vr-ennichi
# 実装ブランチ/PRが公開された後にそのcommitをcheckoutする。
# 公開前の成果物を使う場合は HANDOFF.md に従う。
git lfs pull --include='outputs/ennichi_50m.blend,outputs/assets/sunset.hdr'
python3 tools/prepare_project.py
blender --background --python tools/export_unity.py -- --appearance baked --samples 16 --output Unity/Assets/Ennichi/Derived/ennichi_baked.ennichi
python3 tools/check_asset.py Unity/Assets/Ennichi/Derived/ennichi_baked.ennichi
```

1. Unity Hubで `Unity/` を6000.0.65f1として開く。マスター `.blend` はAssetsへ置かない。
2. `Ennichi > 1 Create or refresh experiment scene` を実行する。派生モデル・衝突判定・開始シーン・保存先の製品名などを設定する。
3. Sceneビューと元の `outputs/01..05` の画像を比較し、`MODEL_PIPELINE.md` の受入項目を確認する。
   Play中のF2で操作者用の歩行プレビューにも入れる（Escで戻る）。これは未承認モデルでも利用できるが、ログを記録せず、参加者実験には使わない。
4. 実機で許容できると確認した派生SHAに対して `visual_review.example.json` を `visual_review.json` として記入する。承認を捏造しない。再度手順2を実行する。
5. `Ennichi > Run engine collision smoke checks` を実行。これはSceneを置き換えるため、編集を保存してから行う。
6. 再度手順2を実行してPlay。実験開始の入力・キーボード操作・保存を確認する。
7. CLIの `-executeMethod Ennichi.Editor.ProjectSetup.BuildWindows` でWindowsビルド。macOSは `BuildMac`。必要なBuild Supportモジュールを事前に用意する。

承認ファイルがない、SHAが違う、形状確認用previewモデルだけ、のいずれかでは本番ビルドと実験開始を拒否します。ベイクを作り直した場合も再承認が必要です。UIに「BLOCKED」と表示される状態は動作確認済み完成版ではありません。

## 操作（マウス不要）

| 操作 | キー |
|---|---|
| 参加者コード・条件の入力欄移動 | Tab |
| 実験開始 | Enter |
| 前後移動 | ↑ / ↓ |
| 左右旋回 | ← / → |
| 横移動 | A / D |
| カメラを上下へ回転 | PageUp / PageDown |
| 一時停止・明示的な再開 | P |
| 開始位置へ戻して停止 | R（再開はP） |
| 終了確認 | F10、続いてEnter。Escで取消し、停止状態を維持 |
| 正常終了後の次の参加者 | N |

一部のノートPCではPageUp/PageDownにFnが必要です。初期値は視点高1.65m、1.25m/s、垂直FOV60度。斜め移動は正規化して速度を増加させません。開始・復帰時に移動キーが押されていれば、一度離すまで入力を受け付けません。フォーカスが戻っても自動再開しません。長いフレーム停止（初期値0.25秒超）でも停止し、Pによる再開を要求します。

開始位置はUnity座標 `(0, 0.08, -25)`、東向き。足元はCharacterControllerによって床に接地し、カメラはrootから1.65m上です。全身アバターの見た目は追加しておらず、一人称root＋カメラです。ミニマップ、訪問店のハイライト、歩行距離の参加者向け表示はありません。

## 保存場所

`Application.persistentDataPath/Sessions/<UTC>_<ランダムID>/`。製品名をセットアップ手順で固定します。

- Windowsの標準候補：`%USERPROFILE%/AppData/LocalLow/TamagawaAIBot/EnnichiExperiment/Sessions/`
- macOSの標準候補：`~/Library/Application Support/TamagawaAIBot/EnnichiExperiment/Sessions/`
- 実際の保存先は起動画面に表示。Unity/OSの履歴による差があり得るため表示を正とする。

匿名コードに氏名や学籍番号を入れないでください。条件欄も個人情報を入れず、条件ID等にしてください。ログはリポジトリ外へ追記します。書き込み事前確認が失敗すれば開始せず、途中で失敗した場合は `SAVE ERROR / NOT COMPLETED` と表示して停止します。

正常終了時は `complete.json` と解析用 `trajectory.csv` / `events.csv` を出力。`complete.json` が無いセッションは未完了です。起動時の件数表示はマーカーの有無による簡易検出であり、解析前は必ず復旧ツールの監査を通してください。

```bash
python3 tools/recover_logs.py /path/to/session
# 未完了セッションの有効な先頭部分を、別の新規フォルダーへ回収する場合
python3 tools/recover_logs.py /path/to/session --recover-to /outside/repository/recovered-session
```

試験中は約1秒ごとと停止時にOSへフラッシュします。強制終了・電源断・ストレージ障害では末尾が失われる可能性があります。完全なゼロ欠落は保証しません。元のjournalを保持し、回収データを正常終了データと区別してください。暗号化・同意管理・実験データの保管期間はこの実装の範囲外です。

## クラウド実行

`.github/workflows/core-tests.yml` はライセンス不要のC#とPythonテストです。`unity-cloud.yml` は手動実行専用で、既存のライセンス付きクラウドrunnerと `ENNICHI_CLOUD_ENABLED=true` の明示設定が必要です。個人PCをrunnerとして登録しないでください。設定内容は `HANDOFF.md` に記載しています。このタスクではクラウド契約・有料GPU・Unityライセンス設定を変更していません。

公式参照：[Unity 6000.0.65f1](https://unity.com/releases/editor/whats-new/6000.0.65f1)、[CharacterController.Move](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/CharacterController.Move.html)、[persistentDataPath](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Application-persistentDataPath.html)。
