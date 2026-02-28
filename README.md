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

## テストセットアップ（開発・E2E共通）
開発用テストを実行する前に、まず開発依存を導入してください。

```sh
python -m pip install -r requirements-dev.txt
```

### E2Eテスト（Playwright）
`tests/e2e` では Playwright の Chromium 実体とOS依存ライブラリが必要です。
E2Eを実行する際は、以下をこの順で実行します。

```sh
python -m pip install -r requirements-dev.txt
python -m playwright install --with-deps chromium
pytest tests/e2e -q
```

`python -m playwright install --with-deps chromium` を省略すると、環境によっては E2E が skip / fail します。

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


## ローカル手動確認手順（再現用）
1. サーバーを起動します。
   ```sh
   python app.py tests/resources/image_root
   ```
2. ブラウザで次のURLへアクセスします。
   - `http://localhost:8000`
3. 期待値を確認します。
   - ホーム画面でサブディレクトリ一覧が表示される
   - サブディレクトリをクリックすると閲覧画面へ遷移する
   - 閲覧画面の初期表示で1枚目画像が表示される

## 画像表示テスト用ディレクトリ
画像の表示テストを行う場合は、ルートディレクトリに `tests/resources/image_root` を指定してください。
テスト画像の先頭1枚が初期表示される想定です。

```sh
python app.py tests/resources/image_root
```

## メタデータ取得テスト用ディレクトリ
画像ファイルに含まれるメタデータに関連するテストを行う場合は、`tests/resources/images_with_prompt`内の画像を使ってください。
各画像に含まれるメタデータは次のとおりです。

- 00009.png
  - Positive prompt: "old male", "holding cat", "masterpiece", "best quality"
  - Negative prompt: "worst quality", "bad quality", "bad anatomy", "bad hands"
  - Model: "waiSHUFFLENOOB_vPred04_2335821"
- 00010.avif
  - Positive prompt: "old male", "holding cat", "masterpiece", "best quality"
  - Negative prompt: "worst quality", "bad quality", "bad anatomy", "bad hands"
  - Model: "waiSHUFFLENOOB_vPred04_2335821"
- 00025.avif
  - Positive prompt: "mountain", "scenery", "masterpiece", "best quality"
  - Negative prompt: なし
  - Model: "waiSHUFFLENOOB_vPred04_2335821"
- 00027.avif
  - Positive prompt: "knight", "solo", "masterpiece"
  - Negative prompt: "bad anatomy", "bad hands"
  - Model: "novaAnimeXL_ilV150_2442274"
- 00029.avif
  - Positive prompt: "old male", "solo"
  - Negative prompt: "worst quality"
  - Model: "novaAnimeXL_ilV150_2442274"

## Codex環境でスクリーンショットが `Not Found` になる場合の回避策
Codex の browser tool（Playwright 実行環境）では、`localhost` の解決先が
シェルで `python app.py ...` を起動した環境と一致しない場合があります。
このとき、`http://localhost:8000` にアクセスしてもアプリではなく `Not Found` を取得することがあります。

回避策:

1. シェル側で次の固定コマンドを使ってアプリを起動し、HTTP 応答を確認する。

```sh
python app.py tests/resources/image_root --host 0.0.0.0 --port 8000
curl -i http://127.0.0.1:8000/
curl -i http://127.0.0.1:8000/api/subdirectories
```

2. browser tool 実行時は `run_playwright_script` の `ports_to_forward: [8000]` を必須にする。
3. `page.goto` は `http://127.0.0.1:8000/` を優先し、`localhost` は環境差で失敗し得るため常用しない。
4. スクリーンショット前にアプリ固有セレクタの描画完了を待つ。
   - 例: `await page.wait_for_selector('#subdir-list .subdir-card')`
5. 失敗時は以下の順で切り分ける。
   - `curl http://127.0.0.1:8000/api/subdirectories` が 200 / JSON 応答か確認
   - browser 側の待機タイムアウトログ（`wait_for_selector` / `goto`）を確認
   - `page.goto` の URL（`127.0.0.1` とパス末尾 `/`）を見直す
6. browser tool 側で接続できない場合は、スクリーンショット運用を中止し、`curl` 結果を確認証跡として残す。
7. 起動引数のパスを必ず `tests/resources/image_root`（`_`）にする（`image-root` は誤り）。


## フロントエンド（React + TypeScript + Vite）

ホーム画面（`/`）と閲覧画面（`/viewer`）は、同一バンドルのSPAとして `frontend/` から配信します。

- 開発/ビルド:
  ```sh
  cd frontend
  npm ci
  npm run build:bundle
  ```
- 生成物配置先: `static/home-app/`
- 起動後の確認 URL: `http://localhost:8000/`

### CI（GitHub Actions）

`.github/workflows/ui-build.yml` で以下を実行します。

1. `npm ci`
2. `npm run build:bundle`
3. PR（同一リポジトリ内ブランチ）の場合は、`static/home-app` の差分を Actions がそのブランチへ自動コミット
4. `push(main)` と外部 fork PR の場合は `git diff --exit-code -- static/home-app` で更新漏れを検知

これにより、通常の PR では「Actions が作った成果物をそのままブランチへ反映」でき、
書き込み権限がないケースでも更新漏れを fail として検出できます。

### 生成物同梱ポリシーと代替案

現時点では「`git pull` 後に Python のみで動作確認できる」ことを優先し、
`static/home-app/` をリポジトリに同梱しています。

将来的に成果物サイズが増える場合は、
GitHub Releases や package registry へ成果物を公開し、
デプロイ工程で取得する方式に切り替えるのが望ましいです。


## エージェント引き継ぎ情報の置き場所
- タスク固有の判断・検証ログ: `docs/agent-handoff/tasks/`
- 恒久的に再利用する知識（責務・仕様・運用）: 各ディレクトリの `README.md`

`docs/agent-handoff/current.md` は運用サマリ専用で、タスク本文は保持しません。
