## Context Handoff
- Goal: 最後の画像表示中に次へ移動した際、ラップ判定の前に画像リストを最新化する。
- Changes:
  - `frontend/src/features/viewer/hooks/useViewer.ts` の `moveNext` を非同期化。
  - 末尾以外では従来どおりローカル配列で次画像へ遷移。
  - 末尾到達時のみ `fetchViewerImages` で再取得し、再取得後の配列長で次インデックスを計算するよう変更。
  - 再取得結果が空の場合は `画像が見つかりません。` を表示するようにした。
- Decisions:
  - Decision: 末尾移動時だけ再取得する。
  - Rationale: 毎回再取得すると不要な通信が増えるため、要件で指定された境界条件に限定した。
  - Impact: ビューアーの次画像移動（右キー/ホイール下）が末尾到達時のみ非同期挙動になる。
- Open Questions:
  - 現時点では配列長のみで判定し、並び順や画像ID差分は追跡しない。
- Verification:
  - `cd frontend && npm run build:bundle`（成功）

## Context Handoff (follow-up)
- Goal: e2e 失敗要因になりうる `moveNext` の戻り値変更（Promise化）を解消しつつ、末尾時の再取得判定を維持する。
- Changes:
  - `moveNext` は `void` 戻り値を維持し、内部で非同期処理を即時実行する形に変更。
  - 末尾時にのみリスト再取得し、再取得後の配列長で next index を算出する挙動は維持。
- Decisions:
  - Decision: 外部公開シグネチャは同期関数のままにする。
  - Rationale: キーハンドラ/既存テストが同期イベントコールバック前提で利用している可能性に合わせるため。
  - Impact: 呼び出し側コードやテストの `moveNext` 取り扱い変更を不要化。
- Open Questions:
  - CI の e2e 失敗ログ詳細（どの assertion か）は未取得。
- Verification:
  - `cd frontend && npm run build:bundle`（成功）
  - `pytest -q tests/e2e/test_ui_flow.py -q`（この環境では playwright 未導入のため実行対象 0）
