# プレビュー確認の定型手順

- 起動コマンド: `python app.py tests/resources/image_root`
- アクセスURL: `http://localhost:8000`
- 初期状態の期待値: サブディレクトリ選択後に画像一覧が表示され、1枚目がメイン表示される
- 失敗時の確認項目: `image_root` のスペル（`-` ではなく `_`）
