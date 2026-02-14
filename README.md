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

起動後、ブラウザで `http://localhost:8000` にアクセスしてください。

オプション:
```sh
python app.py /path/to/image-dir --host 0.0.0.0 --port 8000
```

## 画像表示テスト用ディレクトリ
画像の表示テストを行う場合は、ルートディレクトリに `test/resources/image_root` を指定してください。
テスト画像の先頭1枚が初期表示される想定です。

```sh
python app.py test/resources/image_root
```

## Codex環境でスクリーンショットが `Not Found` になる場合の回避策
Codex の browser tool（Playwright 実行環境）では、`localhost` の解決先が
シェルで `python app.py ...` を起動した環境と一致しない場合があります。
このとき、`http://localhost:8000` にアクセスしてもアプリではなく `Not Found` を取得することがあります。

回避策:

1. まずシェル側でアプリが正常起動していることを確認する。

```sh
python app.py test/resources/image_root
curl -i http://localhost:8000/
curl -i http://localhost:8000/api/subdirectories
```

2. browser tool でスクリーンショットを取る前に、`/api/subdirectories` の HTTP ステータスが 200 か確認する。
3. browser tool 側で `localhost` が到達不能な場合は、スクリーンショット運用を行わず、
   代替として `curl` の結果（HTTP 200 と JSON 応答）を確認証跡として扱う。
4. 起動引数のパスを必ず `test/resources/image_root`（`_`）にする（`image-root` は誤り）。
