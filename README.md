# app-image-view-webui
ローカル画像ディレクトリを閲覧するシンプルな Web アプリです。

## できること
- 折りたたみ可能なサイドメニュー
- 起動時に指定したディレクトリ配下のサブディレクトリ選択
- サブディレクトリ内の画像一覧表示
- メイン領域で画像を拡大表示
- ← / → キーで画像切り替え

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
