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

## Context Handoff
- Goal: `refresh_index` を差分判定ベースへ更新し、追加/変更/削除のみをDB反映する。
- Changes:
  - `app/services/tag_index_service.py` の `refresh_index` を差分更新方式に変更し、`indexed_files(path, mtime_ns, size)` と現在ファイル一覧を比較して `added` / `modified` / `deleted` を分類。
  - `added` と `modified` のみ `extract_generation_prompts` を再実行するようにし、`modified` は旧 `file_tags` / `indexed_files` を削除後に再挿入、`deleted` は両テーブルから削除する処理を追加。
  - 差分反映完了後は `load_index_from_db()` を呼び出し、`tag_to_file_ids` などメモリインデクスをDB再読込で再同期。
  - `tests/services/test_tag_index_service.py` に、追加ファイルのみ取込・変更ファイルのみ再抽出・削除ファイルの検索除外を検証するテストを追加。
- Decisions:
  - Decision: 差分反映後のメモリ同期は増分更新ではなく `load_index_from_db()` に統一。
  - Rationale: 初期実装として複雑さを抑えつつ、DB整合性を単一経路で保証するため。
  - Impact: リフレッシュ後のインメモリ状態は常にDB由来となり、更新ロジックの分岐バグを避けやすくなる。
- Open Questions:
  - `extract_generation_prompts` が `None` を返す画像を `indexed_files` に保持しない設計でよいか（未抽出ファイルは毎回 `added` 扱いで再試行される）。
- Verification:
  - `python -m pip install -r requirements-dev.txt` : 成功
  - `PYTHONPATH=. pytest tests/services/test_tag_index_service.py -q` : 成功（6 passed）
  - `PYTHONPATH=. pytest tests/api/test_api_contract.py -q` : 成功（8 passed）

## Context Handoff
- Goal: `refresh_index` の進捗表示を、待ち時間の体感に合う形へ改善する。
- Changes:
  - `app/services/tag_index_service.py` の `refresh_index` に2段階の進捗表示を追加。
    - `[tag-index] refresh scan`: ファイル列挙後の fingerprint 収集（`stat`）を可視化。
    - `[tag-index] refresh apply`: `deleted` 適用 + `added/modified` 再抽出・再挿入を可視化。
  - `tests/services/test_tag_index_service.py` に `refresh_index` の進捗出力テストを追加し、scan/apply の両バーが標準出力に現れることを検証。
- Decisions:
  - Decision: 単一バーで全処理時間を近似するのではなく、scan/apply の2バーを明示する。
  - Rationale: 「バーが出るまで待ち、出たら一瞬で終わる」体験を避け、実際に時間のかかる前処理を先に可視化するため。
  - Impact: 差分件数が少ないケースでも、ユーザーは refresh 中の進行を早い段階で確認できる。
- Open Questions:
  - `list_images_recursive` 自体（rglob+sort）の待ち時間をさらに減らす/可視化する必要があるか。
- Verification:
  - `python -m pip install -r requirements-dev.txt` : 成功
  - `PYTHONPATH=. pytest tests/services/test_tag_index_service.py -q` : 成功（7 passed）
  - `PYTHONPATH=. pytest tests/api/test_api_contract.py -q` : 成功（8 passed）

## Context Handoff
- Goal: refresh開始直後の待ち時間に、母数未確定の進捗を即時表示する。
- Changes:
  - `app/services/tag_index_service.py` に `_list_images_recursive_with_progress()` を追加し、`list_images_recursive` 実行中に別スレッドで `[tag-index] refresh list`（total未指定）を更新する実装を追加。
  - `refresh_index` は上記ヘルパー経由でファイル一覧を取得するよう変更し、その後の `scan` / `apply` 2段階バーは維持。
  - `tests/services/test_tag_index_service.py` の進捗テストを更新し、`refresh list` / `refresh scan` / `refresh apply` の出力を検証。
- Decisions:
  - Decision: ファイル列挙の重い区間は indeterminate バーを別スレッドで回して可視化する。
  - Rationale: 列挙結果（母数）が確定する前に進捗表示を出し、体感上の無応答時間をなくすため。
  - Impact: 大規模ディレクトリでも refresh 実行直後に進捗表示が始まる。
- Open Questions:
  - `build_index` 側にも同様の indeterminate 列挙バーを付与するか。
- Verification:
  - `PYTHONPATH=. pytest tests/services/test_tag_index_service.py -q` : 成功（7 passed）
  - `python -m pip install -r requirements-dev.txt` : 成功
  - `PYTHONPATH=. pytest tests/api/test_api_contract.py -q` : 成功（8 passed）
