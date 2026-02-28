## Context Handoff
- Goal: 画像生成プロンプトのポジティブ語句をタグ化し、再帰収集・インデクス再構築・AND/OR検索を `/api` から利用可能にする。
- Changes:
  - `app/services/tag_index_service.py` を新規追加し、`build_index` / `refresh_index` / `query` を実装。SQLite 永続化（`tag_index.sqlite3`）と `tag -> set[file_id]`, `file_id -> tags[]` のメモリインデクスを保持。
  - `app/repositories/filesystem.py` に `list_images_recursive` を追加し、全サブディレクトリ配下の画像を取得。
  - `app/main.py` で起動時にタグインデクスを初回構築、`app/api/routes.py` と `app/models/schemas.py` にタグ検索/リフレッシュAPIを追加。
  - `tests/services/test_tag_index_service.py` と `tests/api/test_api_contract.py` / `tests/api/conftest.py` を更新し、検索とリフレッシュのAPI契約を検証。
- Decisions:
  - Decision: 初回実装では `refresh_index` を全件再構築にし、将来差分更新のため `FileFingerprint(mtime_ns, size)` と `file_metadata` 構造を先に導入。
  - Rationale: 仕様充足と堅牢性を優先し、差分ロジックの複雑化を避けつつ移行パスを確保するため。
  - Impact: 将来、`refresh_index` の内部実装を差分方式に置換してもAPI契約は維持できる。
- Open Questions:
  - 検索結果に `file_id` のみを返す現行仕様で十分か（将来的にタグハイライトやファイル名同梱要件が出る可能性）。
  - タグ正規化（casefold）のみで十分か（全角半角・記号正規化の要否）。
- Verification:
  - `python -m pip install -r requirements-dev.txt` : 成功
  - `python -m playwright install --with-deps chromium` : 成功
  - `PYTHONPATH=. pytest tests/services/test_tag_index_service.py tests/api/test_api_contract.py tests/services/test_prompt_extractor.py -q` : 成功（10 passed）
  - `PYTHONPATH=. pytest -q` : 成功（11 passed）

## Context Handoff
- Goal: インデクス構築中の進捗をローカルコンソールで可視化する。
- Changes:
  - `app/services/tag_index_service.py` に進捗表示処理 `_print_progress` を追加し、`build_index` の開始時・各ファイル処理後にプログレスバーを標準出力へ出力。
  - `tests/services/test_tag_index_service.py` に進捗バー出力確認テストを追加。
- Decisions:
  - Decision: 外部依存（tqdm等）は追加せず、標準出力へのキャリッジリターン更新でプログレスバーを実装。
  - Rationale: 依存を増やさず、既存起動フローに最小差分で要件を満たすため。
  - Impact: インデクス構築時にローカルコンソールで進行率を確認可能になった。
- Open Questions:
  - 大規模件数時に出力頻度を間引くか（現在は各ファイルで更新）。
- Verification:
  - `PYTHONPATH=. pytest tests/services/test_tag_index_service.py tests/api/test_api_contract.py -q` : 成功
  - `PYTHONPATH=. pytest -q` : 成功

## Context Handoff
- Goal: 進捗表示の実装を `tqdm` ベースへ置き換える。
- Changes:
  - `app/services/tag_index_service.py` の自前 `_print_progress` を削除し、`build_index` のループを `tqdm(..., desc="[tag-index] build", unit="file")` で進捗表示する実装へ変更。
  - `requirements.txt` に `tqdm` を追加。
  - `tests/services/test_tag_index_service.py` の進捗テスト期待値を `tqdm` 出力に合わせて更新。
- Decisions:
  - Decision: 進捗表示は `tqdm` を採用し、出力先は `file=sys.stdout` を明示。
  - Rationale: 視認性と保守性を高めつつ、要望（tqdm利用可）に合わせるため。
  - Impact: インデクス構築時の進捗表示が標準的なバー形式になり、将来の拡張（postfix等）が容易。
- Open Questions:
  - なし。
- Verification:
  - `PYTHONPATH=. pytest tests/services/test_tag_index_service.py tests/api/test_api_contract.py -q` : 成功
  - `PYTHONPATH=. pytest -q` : 成功

## Context Handoff
- Goal: 起動時にDBからタグインデクスを復元し、空DBまたはロード失敗時のみフルビルドへフォールバックする。
- Changes:
  - `app/services/tag_index_service.py` に `load_index_from_db()` を追加し、`indexed_files`/`file_tags` から `tag_to_file_ids`・`file_id_to_tags`・`file_metadata` を再構築してロード件数を返すようにした。
  - `app/main.py` の `create_app()` を変更し、起動時はDBロード→必要時のみ `build_index()` の順で実行、`load_count` と `fallback_build` を1行ログ出力するようにした。
  - `tests/services/test_tag_index_service.py` に、DB保存後に別インスタンスでロード復元できるテストを追加した。
  - `tests/api/test_api_contract.py` に、事前作成DBを起動時にロードして検索APIが機能する契約テスト（空ディレクトリ起動でフルビルド非前提）を追加した。
- Decisions:
  - Decision: DBロード結果の判定は「ロード件数（int）」で扱い、0件は成功扱いにしたうえで起動制御でフォールバック判定する。
  - Rationale: 空DBをエラーと区別し、起動時の分岐を単純化するため。
  - Impact: 既存DBがある環境では起動時の不要な全件再構築を回避できる。
- Open Questions:
  - DB破損時の詳細ログ（例: 例外種別）を追加で出すかどうか。
- Verification:
  - `PYTHONPATH=. pytest tests/services/test_tag_index_service.py tests/api/test_api_contract.py -q` : 成功
