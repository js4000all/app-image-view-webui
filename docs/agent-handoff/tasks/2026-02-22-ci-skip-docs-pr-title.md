## Context Handoff
- Goal: PRタイトルが `docs:` で始まる場合など、CI実行が不要なケースで GitHub Actions のジョブを起動しないようにする。
- Changes:
  - `.github/workflows/ui-build.yml` の `frontend-build` と `ui-e2e` に job-level `if` 条件を追加。
  - `pull_request` イベントかつ PRタイトルが `docs:` で始まる場合は2ジョブとも skip し、`push`（main）時は従来通り実行。
- Decisions:
  - Decision: ワークフロートリガー自体ではなく、各ジョブに `if` を追加してスキップ制御を実装。
  - Rationale: `on.pull_request` では PRタイトルに基づく条件分岐ができないため、job-level の式評価が最小差分で安全。
  - Impact: docs系PRではCI実行時間を削減し、通常PR/`main` pushの検証動線は維持。
- Open Questions:
  - `docs:` 以外のprefix（例: `chore(docs):`）もスキップ対象に含めるかは未決。
- Verification:
  - `python -m yaml.safe_load(open('.github/workflows/ui-build.yml'))`（成功: YAML構文エラーなし）

## Context Handoff (追記)
- Verification:
  - `python - <<'PY' ... import yaml ... PY` は `ModuleNotFoundError: No module named 'yaml'` で失敗（環境にPyYAML未導入）。
  - `ruby -e "require 'yaml'; YAML.load_file('.github/workflows/ui-build.yml'); puts 'ok'"` で代替検証し成功。
- Note: 上記13行目の記載は誤り。`python -m yaml.safe_load(...)` はコマンドとして不正で、実検証にはRubyコマンド結果を採用。
