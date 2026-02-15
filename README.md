# app-image-view-webui
ローカル画像ディレクトリを閲覧するシンプルな Web アプリです。

## できること
- 起動時に指定したホームディレクトリ以下のディレクトリを一覧表示
- ディレクトリ内の画像ファイルを閲覧する画面
- 左右キーやマウスホイールで画像切り替え
- ディレクトリ名の変更
- 画像の削除

## セットアップ
```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 起動方法
```sh
python app.py /path/to/image-dir
```

内部では `uvicorn` で FastAPI アプリを起動します。
起動後、ブラウザで `http://localhost:8000` にアクセスしてください。

オプション:
```sh
python app.py /path/to/image-dir --host 0.0.0.0 --port 8000 --static-dir ./static
```


## 画像表示テスト用ディレクトリ
画像の表示テストを行う場合は、ルートディレクトリに `tests/resources/image_root` を指定してください。
テスト画像の先頭1枚が初期表示される想定です。

```sh
python app.py tests/resources/image_root
```

## Codex環境でスクリーンショットが `Not Found` になる場合の回避策
Codex の browser tool（Playwright 実行環境）では、`localhost` の解決先が
シェルで `python app.py ...` を起動した環境と一致しない場合があります。
このとき、`http://localhost:8000` にアクセスしてもアプリではなく `Not Found` を取得することがあります。

回避策:

1. まずシェル側でアプリが正常起動していることを確認する。

```sh
python app.py tests/resources/image_root
curl -i http://localhost:8000/
curl -i http://localhost:8000/api/subdirectories
```

2. browser tool でスクリーンショットを取る前に、`/api/subdirectories` の HTTP ステータスが 200 か確認する。
3. browser tool 側で `localhost` が到達不能な場合は、スクリーンショット運用を行わず、
   代替として `curl` の結果（HTTP 200 と JSON 応答）を確認証跡として扱う。
4. 起動引数のパスを必ず `tests/resources/image_root`（`_`）にする（`image-root` は誤り）。


## UIマイグレーション準備（React + TypeScript + Vite）

既存の `static/home.html` / `static/viewer.html` は変更せず、
マイグレーション確認用に `frontend/` 配下へ最小 React アプリ（Hello world）を追加しています。

- 開発/ビルド:
  ```sh
  cd frontend
  npm ci
  npm run build:bundle
  ```
- 生成物配置先: `static/react-hello/`
- 起動後の確認 URL: `http://localhost:8000/react-hello/`

### CI（GitHub Actions）

`.github/workflows/ui-build.yml` で以下を実行します。

1. `npm ci`
2. `npm run build:bundle`
3. PR（同一リポジトリ内ブランチ）の場合は、`static/react-hello` の差分を Actions がそのブランチへ自動コミット
4. `push(main)` と外部 fork PR の場合は `git diff --exit-code -- static/react-hello` で更新漏れを検知

これにより、通常の PR では「Actions が作った成果物をそのままブランチへ反映」でき、
書き込み権限がないケースでも更新漏れを fail として検出できます。

### 生成物同梱ポリシーと代替案

現時点では「`git pull` 後に Python のみで動作確認できる」ことを優先し、
`static/react-hello/` をリポジトリに同梱しています。

将来的に成果物サイズが増える場合は、
GitHub Releases や package registry へ成果物を公開し、
デプロイ工程で取得する方式に切り替えるのが望ましいです。
