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

## Context Handoff
- Goal: タグインデクスの refresh で、更新があったディレクトリのみを対象に差分処理する。
- Changes:
  - `app/services/tag_index_service.py` に `indexed_directories(path, mtime_ns)` テーブルと `IndexedDirectory` を追加し、`build_index` 時に全ディレクトリの更新時刻を保存するようにした。
  - `refresh_index` は `indexed_directories` と現在のディレクトリmtimeを比較し、変更ディレクトリのみ `list_images` で走査する方式へ変更。削除ディレクトリ配下の既存インデクス行も削除対象に含めるようにした。
  - refresh完了時に `indexed_directories` を全更新し、次回 refresh の比較基準を再保存するようにした。
  - `tests/services/test_tag_index_service.py` を更新し、ディレクトリmtimeが変わらない更新では再抽出しないこと、および変更ディレクトリのみ再抽出されることを検証するテストを追加した。
- Decisions:
  - Decision: refreshの対象絞り込みは「ディレクトリmtimeの差分」を一次判定とし、変更ディレクトリ配下のみファイル差分（added/modified/deleted）を評価する。
  - Rationale: `extract_generation_prompts` の再実行コストを減らし、変更が局所的なケースで refresh を高速化するため。
  - Impact: 変更のないディレクトリ配下ファイルは再抽出されず、refreshの処理量が削減される。
- Open Questions:
  - ディレクトリmtimeが変わらないファイル内容更新（上書き）を追跡する必要がある場合、別途ファイル単位の監視戦略が必要。
- Verification:
  - `pytest tests/services/test_tag_index_service.py -q` : 成功（10 passed）
  - `pytest tests/services/test_tag_index_service.py tests/api/test_api_contract.py::test_tag_index_query_and_refresh -q` : 失敗（`httpx` 未導入のため `tests/api/conftest.py` 読み込み時に `ModuleNotFoundError`）

## Context Handoff
- Goal: 前回PRで不足していたテスト実行手順（依存導入）を再発防止として明文化し、pytestを完走させる。
- Changes:
  - `docs/agent-handoff/README.md` に「pytest実行前の依存導入チェック」節を追加し、`requirements-dev.txt` と Playwright Chromium 導入を明示した。
  - 依存導入後に `pytest -q` を再実行し、全テストが通ることを確認した。
- Decisions:
  - Decision: 手順はタスク個別ログだけでなく、共通運用ドキュメントにも残す。
  - Rationale: 同種の手順抜け（pip install省略）を次回以降の作業でも防止するため。
  - Impact: pytest実行時の初期失敗（`httpx` 未導入や Playwright browser 未導入）が再発しにくくなる。
- Open Questions:
  - なし。
- Verification:
  - `python -m pip install -r requirements-dev.txt` : 成功
  - `pytest -q` : 失敗（初回。Playwright browser executable未導入）
  - `python -m playwright install --with-deps chromium` : 成功
  - `pytest -q` : 成功（24 passed）

## Context Handoff
- Goal: refresh進捗表示のうち、scan工程をディレクトリ単位ではなくファイル単位で表示する。
- Changes:
  - `app/services/tag_index_service.py` の `refresh_index` で、`changed_directories` から対象ファイル一覧（`changed_directory_files`）を先に収集するよう変更。
  - `refresh scan` の `tqdm` は `changed_directory_files` を対象にし、`unit="file"` でファイル数進捗を表示するようにした。
  - `refresh list` は従来どおりディレクトリ列挙の indeterminate 表示（`unit="dir"`）を維持。
- Decisions:
  - Decision: list工程はディレクトリ、scan工程はファイルを単位に分離したまま表示する。
  - Rationale: 体感時間の長い scan に対して、実作業量（ファイル数）に沿った進捗を出すため。
  - Impact: scanバーがディレクトリ数ではなく対象画像ファイル総数ベースで進行する。
- Open Questions:
  - なし。
- Verification:
  - `python -m pip install -r requirements-dev.txt` : 成功
  - `python -m playwright install --with-deps chromium` : 成功
  - `pytest -q` : 成功（24 passed）
