## Context Handoff
- Goal: ホーム画面実装を `App.tsx` から分割し、React の責務分離に沿ったディレクトリ構成へ再編する。あわせて、AI エージェント向けのアーキテクチャ文書を追加する。
- Changes:
  - `frontend/src/App.tsx` を薄いルートコンポーネントへ簡素化し、実体を `features/home/pages/HomePage.tsx` へ移動。
  - ホーム画面の API 呼び出し・型・hooks・カードコンポーネントを分離（`frontend/src/features/home/*`, `frontend/src/api/http.ts`, `frontend/src/types/home.ts`）。
  - `docs/ARCHITECTURE.md` を新規作成し、技術スタック・責務分離・主要ディレクトリ・運用コマンドを整理。
  - フロントエンドを再ビルドし、`static/home-app/` の成果物を更新。
- Decisions:
  - Decision: ホーム画面は feature-first（`features/home`）でページ・コンポーネント・hooks・API を分割する。
  - Rationale: 1ファイル集中を避け、表示・状態管理・通信の変更を独立して行えるようにするため。
  - Impact: 今後のホーム画面改修は `App.tsx` ではなく `features/home` 配下を中心に実施でき、影響範囲の把握が容易になる。
- Open Questions:
  - なし。
- Verification:
  - `npm ci`（成功）
  - `npm run build:bundle`（成功）
  - `pip install -r requirements-dev.txt`（成功）
  - `python -m playwright install --with-deps chromium`（成功。apt mirror の一部 403 警告はあるが処理継続しインストール完了）
  - `pytest -q`（成功: 7 passed）
  - `python app.py tests/resources/image_root > /tmp/app.log 2>&1 & echo $! > /tmp/app.pid; sleep 2; curl -sS -o /tmp/home.out -w '%{http_code}' http://localhost:8000/; echo; curl -sS http://localhost:8000/api/subdirectories; kill $(cat /tmp/app.pid)`（成功: `/` が 200、`/api/subdirectories` が正常応答）

---

## Context Handoff
- Goal: AIエージェントが `pip install` 前に `pytest` を実行してしまう誤操作を誘発する記述がないか確認し、必要なら是正する。
- Changes:
  - `README.md` と直近コミット履歴を確認し、現行ドキュメントの導線をレビュー。
  - `docs/ARCHITECTURE.md` の「テスト」節に、`pytest` 実行前に `requirements-dev.txt` をインストールする前提手順（venv作成含む）を追記。
- Decisions:
  - Decision: 問題の誘因は `docs/ARCHITECTURE.md` の「pytest コマンドのみ提示」にあると判断し、同節へ事前セットアップを明示する。
  - Rationale: README は既に `pip install` を先に示しており、重複修正より誤誘導箇所の最小差分修正が妥当。
  - Impact: エージェントが設計ドキュメント参照のみで作業開始しても、依存導入前の `pytest` 実行を避けやすくなる。
- Open Questions:
  - なし。
- Verification:
  - `python app.py tests/resources/image_root > /tmp/app.log 2>&1 & pid=$!; sleep 2; code=$(curl -s -o /tmp/home.html -w '%{http_code}' http://localhost:8000/); echo "HTTP $code"; kill $pid`（成功: `HTTP 200`）
  - `rg -n "pytest" docs README.md .github/workflows`（成功: `docs/ARCHITECTURE.md` の記述位置を特定）
