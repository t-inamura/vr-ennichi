# 権限・ライセンス待ちの引継ぎ

2026-10-20にmainのHEAD `9936337b26214ed9bf2935a26b60b0754ddab140` を確認。GitHub連携のcreate_branchは403 `Resource not accessible by integration`。リモートの `codex/unity-walkthrough-logging` ブランチもPRも作成していない。push=trueというユーザー権限表示は連携アプリの書込可否を保証しない。

クラウド内の作業ブランチで実装し、差分をgit patchとソースアーカイブにまとめる。mainへ直接変更しない。別認証・トークン・ユーザーPCで権限を回避しない。

## GitHubに必要な対応

接続中のGitHub Appで `t-inamura/vr-ennichi` が書込対象に含まれることと、Contents: read/write、Pull requests: read/writeを確認する。CIワークフロー追加にはWorkflowsへの書込権限も必要になる。アプリの権限を設定画面で増やせない場合、対応する接続/権限のあるレビュー経路が必要。秘密トークンをチャットへ貼らない。

権限が用意された後、最新mainとの差分を再確認し、実装ブランチへコミットを登録してdraft PRを作る。`PR_BODY.md` にレビュー用説明を準備してある。完成扱いでmergeしない。

配布patchを別の許可された環境で適用する場合の手順（このタスクでローカルPCを使ったという意味ではない）：

```bash
git switch -c codex/unity-walkthrough-logging 9936337b26214ed9bf2935a26b60b0754ddab140
git am /path/to/ennichi-implementation.patch
# 最新mainに変更があれば、差分を確認して通常のrebase/mergeで解消する。
```

ソースzipは同じbaseに追加・変更したファイルだけを同梱し、マスターや既存の制作履歴を再配布しない。派生アセットzipはリポジトリrootで展開し、`Unity/Assets/Ennichi/Derived/` へ置く。派生バイナリは再生成可能でサイズが大きいためGitの対象から外している。配置後に `prepare_project.py` とUnityのsetupを実行する。

## Unityクラウドに必要な対応

1. Unity 6000.0.65f1とWindows Build Support（Mono）、必要ならMac Build Support（Mono）を使える、ライセンス済みのクラウド環境を指定する。既存の契約・ライセンス条件を確認する。
2. GitHub Actionsを使うなら、**ユーザーPCではない**Linux x64クラウドrunnerへ `ennichi-unity-cloud` ラベルを付ける。新規VM/課金契約は事前に確認する。
3. リポジトリ変数 `ENNICHI_UNITY_EDITOR` と `ENNICHI_BLENDER` にそのクラウド環境の実行ファイルパスを設定。明示的に運用を許可した後だけ `ENNICHI_CLOUD_ENABLED=true` にする。
4. 必要なら `ennichi-cloud` environmentに承認者を設定。ライセンスはrunner側で安全に用意し、リポジトリやログへ含めない。Personal/Pro等の利用可否やライセンス取得をこのタスクでは判断・代行していない。
5. 手動workflowを起動。ライセンス、インポート、コンパイル、native physics checks、視覚承認のどれかが満たされなければビルド成功にしない。

このタスクで有料サービス・VM/GPUの新規起動・GitHub設定・Unityライセンスの変更は実施していない。クラウド内の無料で入手できるポータブルBlender/.NETを使用した。ユーザーのローカルPC、ブラウザ、認証情報、Unity/Blenderには接続していない。
