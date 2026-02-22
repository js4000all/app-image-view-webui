# agent-handoff 運用ルール

このディレクトリは、AIエージェント間の作業コンテキスト引き継ぎ専用です。

## 方針

- `current.md` の単一更新による運用は廃止。
- 並列タスクの競合を避けるため、タスク単位ファイルを `tasks/` に作成して運用する。
- 恒久化すべき情報は各ディレクトリの `README.md` に移す。

## ファイル構成

- `current.md`: 運用方針の要約（タスクログを書かない）
- `tasks/YYYY-MM-DD-<topic>.md`: タスク単位ログ（追記運用）
- `archive/YYYY-MM-DD-<topic>.md`: 完了後に移動した履歴

## 更新ルール

1. 1タスクにつき1ファイルを `tasks/` に作る。
2. 同一タスクでは追記のみで更新し、既存セクションを上書きしない。
3. 完了時に、恒久化が必要な内容だけを該当ディレクトリ `README.md` へ反映する。
4. タスク完了後、必要に応じて `archive/` へ移動する。

## browser tool 失敗時の記録テンプレート

browser tool（Playwright）で画面確認に失敗した場合は、タスクログに次のテンプレートをそのまま記録する。

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

この記録により、「サーバ死活は正常だがブラウザ到達に失敗」なのか「UIレンダリング待機不足（遅延）」なのかを切り分けやすくする。
