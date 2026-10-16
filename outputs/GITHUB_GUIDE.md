# GitHubでの管理と共同作業

## 保存先と方針

- GitHub: **https://github.com/t-inamura/vi-ennichi**（公開）
- このMacの作業場所: **`~/work/vr-ennichi`**
- 現行モデル: **`outputs/ennichi_50m.blend`**
- ブランチ: `main`
- 元の作業フォルダはコピー元として保持しています。今後の編集は新しい作業場所で行います。

初期セットアップは、全ファイルのコピーと照合、Git LFS導入、Git初期化、初回コミット、GitHubへのpush、別フォルダへの取得照合の順で行います。

モデル、素材、画像、コード、説明書に加えて、制作途中のモデル、`.blend1`、修正スクリプト、ログ、素材取得情報も管理します。再生成可能なPythonキャッシュ、OSの一時ファイル、認証情報は追跡しません。

| 形式 | 管理方式 |
|---|---|
| `.blend`、`.blend1`などの番号付きバックアップ、`.hdr`、`.exr` | Git LFS |
| Python、Markdown、JSON、SVG、ログ | 通常のGit |
| PNG、JPEG | 通常のGit |

Git LFSは大きなファイルの実体を別領域に保存し、Gitには参照情報を記録します。[GitHub公式の説明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage)を参照してください。

## 最初に取得する

macOSでHomebrewを使う場合は `brew install git-lfs` で導入します。他OSでは [Git LFS公式サイト](https://git-lfs.com/) のインストール方法を使います。

```sh
git clone https://github.com/t-inamura/vi-ennichi.git vr-ennichi
cd vr-ennichi
git lfs install --local
git lfs pull
git lfs ls-files
```

Blenderで `outputs/ennichi_50m.blend` を開きます。ファイルが数行のテキストになっている場合はLFSの参照情報だけを取得しています。上の `git lfs pull` で実体を取得してください。ZIPダウンロードより、このclone手順を推奨します。

## 普段の更新

作業前に、未保存のBlender編集や未コミットの変更がない状態で最新を取得します。

```sh
cd ~/work/vr-ennichi
git status
git pull --ff-only
git lfs pull
```

Blenderで新しい保存先のモデルを編集・保存したら、次の順で記録します。`git add` の対象には意図して変更したファイルだけを指定してください。

```sh
git status --short
git add outputs/ennichi_50m.blend
git diff --cached --stat
git commit -m "Update festival stall layout"
git push
```

画像や生成スクリプトも変更した場合は一緒に追加します。LFSファイルの送信は `git push` 時にフックが実行します。認証・LFSエラーが出た場合は、push成功を確認してから共同研究者に共有してください。

`validation.json` は制作時点の検証記録です。モデル変更後に古い検証値を最新として扱わず、再確認して更新します。`blend_sha256` の確認例:

```sh
shasum -a 256 outputs/ennichi_50m.blend
```

## 共同編集

公開URLで閲覧・cloneできます。直接pushする共同研究者には、管理者がGitHubの Settings → Collaborators から権限を付与します。今回のセットアップでは共同研究者の招待は行っていません。

複数人で変更する場合は作業ブランチを使い、プルリクエストでレビューします。

```sh
git switch -c edit/stall-layout
# 編集・保存・git add・git commit
git push -u origin edit/stall-layout
```

同じ `.blend` を複数人で同時編集すると、一般的なテキストのようには自動統合できません。担当者を決めるか、部品を別ファイルに分けてから作業してください。プルリクエストにはプレビュー画像と変更の説明を添えます。

## 過去の版を確認する

作業中の変更をコミットするか別名で保存したうえで、`git log --oneline` で対象コミットを確認します。そのコミットから確認用ブランチを作ると、現在の `main` の履歴を変えずに過去版を開けます。

```sh
git log --oneline
# COMMIT_IDを実際のコミットIDに置き換える
git switch -c inspect/previous COMMIT_ID
git lfs pull
# 確認を終え、未保存・未コミットの変更がない状態で戻る
git switch main
git lfs pull
```

`.blend1` と `work/ennichi_previous.blend` は制作途中の保存データです。現行版は常に `outputs/ennichi_50m.blend` から開いてください。

## 再生成と保存場所の注意

通常の再生成手順は [README_日本語.md](README_日本語.md) にあります。モデルの再生成は現在の `.blend` を上書きするため、手編集した内容をコミットしてから実行します。

完成モデルの画像素材は内蔵されています。元のファイルを維持するため、Blender内部の保存パス情報と制作ログには制作時の作業場所が残っています。別の環境でレンダー画像を保存するときは、Blenderの出力先を現在の作業フォルダに指定してください。`outputs/render_views.py` はスクリプト自身の場所を出力先に使います。

制作途中の `work/` スクリプトは記録用です。保存先は同じリポジトリの `outputs/` を参照するように更新していますが、現行モデルへの一括実行は想定していません。日本語文字を再生成する場合は日本語フォント、他OSでレンダリングする場合はCyclesの使用デバイス設定を確認してください。

## 参考

- [Git LFSの設定](https://docs.github.com/en/repositories/working-with-files/managing-large-files/configuring-git-large-file-storage)
- [Git LFSを使った共同作業](https://docs.github.com/en/repositories/working-with-files/managing-large-files/collaboration-with-git-large-file-storage)
