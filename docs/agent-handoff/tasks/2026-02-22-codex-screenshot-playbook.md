## Context Handoff
- Goal:
  - `docs/` 配下に、Codex 実行時の最小スクリーンショット手順テンプレートを追加する。
- Changes:
  - `docs/screenshot-playbook.md` を新規作成し、前提条件、`run_playwright_script` 例、`Not Found` 時のデバッグ手順、相対パス保存ルールを記載。
- Decisions:
  - Decision: 実行URLは `http://127.0.0.1:8000/` を明示。
  - Rationale: Codex 実行環境で `localhost` 解決差異が起きるケースの切り分けを容易にするため。
  - Impact: スクリーンショット取得手順の再現性向上、トラブル時の初動を標準化。
- Open Questions:
  - `run_playwright_script` の運用例を README にも重複掲示するかは未決定。
- Verification:
  - `sed -n '1,220p' docs/screenshot-playbook.md` で記載内容を確認（成功）。

## Context Handoff
- Goal:
  - `README.md` の「Codex環境でスクリーンショットが Not Found になる場合の回避策」を、Codex browser tool 前提の手順に更新する。
- Changes:
  - サーバ起動コマンドを `python app.py tests/resources/image_root --host 0.0.0.0 --port 8000` の固定例へ更新。
  - `run_playwright_script` 実行時の `ports_to_forward: [8000]` 必須化、`page.goto` の `http://127.0.0.1:8000/` 優先、`#subdir-list .subdir-card` 待機手順を追記。
  - 失敗時の切り分け順を `curl /api/subdirectories` → browser 側タイムアウトログ確認 → URL 見直しの順で箇条書き追加。
- Decisions:
  - Decision: README の回避策を「接続先URL・ポート転送・セレクタ待機」の3点セットで明文化。
  - Rationale: Not Found/タイムアウトの再発を、実行順序の標準化で減らすため。
  - Impact: Codex browser tool を使うスクリーンショット手順の再現性が向上。
- Open Questions:
  - なし。
- Verification:
  - `sed -n '71,125p' README.md` で追記内容を確認（成功）。
