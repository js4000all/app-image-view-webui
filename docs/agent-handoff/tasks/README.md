# tasks ディレクトリ

タスクごとの引き継ぎログを保存します。

命名規則: `YYYY-MM-DD-<topic>.md`

例: `2026-02-15-agent-handoff-policy.md`

## browser tool 失敗時の追記テンプレート

browser tool によるスクリーンショット取得や画面到達が失敗したときは、各タスクファイルへ以下を追記する。

```md
## Browser Tool Failure Triage
- Server bind / port: （例: `0.0.0.0:8000`）
- browser tool `ports_to_forward`: 
- `page.goto` URL: 
- `wait_for_selector` target / timeout: 
- `page.url` final value: 
- `page.title`: 
- `page.content()` 先頭（数百文字）: 
- Parallel curl result: `curl http://127.0.0.1:8000/api/subdirectories`
  - stdout:
  - stderr:
  - exit code:
```

この情報セットを残すことで、ネットワーク到達性の問題とUI描画待機の問題を分離して判断できる。
