## Context Handoff
- Goal: 画像ダウンロード遅延の主因と判断した `StreamingResponse` 配信経路を改善し、既存 API 契約を維持したまま転送効率を回復する。
- Changes:
  - `app/api/routes.py` の `GET /api/image/{file_id}` 本文レスポンスを `StreamingResponse(file_obj)` から `FileResponse(path=...)` へ変更。
  - `ETag` / `Last-Modified` / `Cache-Control` / `Content-Length` ヘッダと 304 判定ロジックは維持。
  - `HEAD /api/image/{file_id}` は従来どおりヘッダのみレスポンスを維持。
- Decisions:
  - Decision: 画像本文配信は FastAPI の `FileResponse` に寄せる。
  - Rationale: バイナリ画像を file object の逐次ストリームで返すより、ファイル配信向け実装を使う方がスループット低下リスクを抑えられるため。
  - Impact: API 仕様互換を保ったまま、画像ダウンロード速度の改善が期待できる。
- Open Questions:
  - 実運用データサイズでの速度改善幅を、同一環境で `curl` 計測し定量確認する必要がある。
- Verification:
  - `pytest tests/api -q`
  - `python app.py tests/resources/image_root --host 127.0.0.1 --port 8001`
  - `curl -sS -o /dev/null -w '%{http_code} %{speed_download} %{time_total}
' http://127.0.0.1:8001/api/image/<file_id>`
