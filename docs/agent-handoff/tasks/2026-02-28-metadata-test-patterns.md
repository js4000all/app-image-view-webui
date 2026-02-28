## Context Handoff
- Goal: メタデータ入りテスト画像（00009/00010/00025/00027/00029）のバリエーションをテストで網羅し、回帰検知を強化する。
- Changes:
  - `tests/services/test_prompt_extractor.py` をパラメータ化し、5種類の画像それぞれで positive/negative prompt 抽出結果を検証。
  - `tests/services/test_tag_index_service.py` のインデックス対象を5画像に拡張し、`solo` や `knight` を含むクエリ条件を追加。
  - `tests/api/conftest.py` の `copied_prompt_image_root` fixture を `tests/resources/images_with_prompt/dir1` から5画像を配置するよう更新。
  - `tests/api/test_api_contract.py` のタグインデックス件数期待値を5画像/8タグ以上へ更新し、テストデータ参照パスを `dir1` 配下へ修正。
- Decisions:
  - Decision: メタデータ差分の検証は README 記載の prompt 値をそのまま期待値として採用する。
  - Rationale: ドキュメント化済みの仕様を単一の真実源とし、画像更新時の不整合を即座に検知できるため。
  - Impact: prompt extractor / tag index の単体・API契約テストの期待値が README と同期される。
- Open Questions:
  - Model名の抽出は現状 `prompt_extractor` の返却仕様外であり、将来仕様で必要なら別途抽出ロジックとテスト追加が必要。
- Verification:
  - `PYTHONPATH=. pytest tests/services/test_prompt_extractor.py tests/services/test_tag_index_service.py tests/api/test_api_contract.py -q` : 成功

- Verification (retry log):
  - `PYTHONPATH=. pytest tests/services/test_prompt_extractor.py tests/services/test_tag_index_service.py tests/api/test_api_contract.py -q` : 初回は `httpx` 未導入で失敗。
  - `python -m pip install -r requirements-dev.txt` 実行後、同コマンドを再実行して `16 passed`。
