# Codexスクリーンショット最小テンプレート

## 前提
- アプリサーバーが `0.0.0.0:8000` で起動済みであること。
- 例: `python app.py tests/resources/image_root --host 0.0.0.0 --port 8000`

## `run_playwright_script` 呼び出し例

```json
{
  "ports_to_forward": [8000],
  "script": "from playwright.sync_api import sync_playwright\n\nwith sync_playwright() as p:\n    browser = p.chromium.launch()\n    page = browser.new_page()\n\n    page.goto('http://127.0.0.1:8000/')\n    page.wait_for_selector('#subdir-list .subdir-card')\n\n    # 必要操作（例: 先頭サブディレクトリをクリック）\n    page.locator('#subdir-list .subdir-card').first.click()\n\n    page.screenshot(path='artifacts/home.png', full_page=True)\n    browser.close()"
}
```

## 画面が `Not Found` のときのデバッグ手順

`Not Found` が表示された場合は、`page.content()` と `page.url` を保存して原因を切り分ける。

```python
html = page.content()
current_url = page.url

with open('artifacts/not-found.html', 'w', encoding='utf-8') as f:
    f.write(html)

with open('artifacts/not-found-url.txt', 'w', encoding='utf-8') as f:
    f.write(current_url + '\n')
```

- 保存したHTMLにアプリの要素（`#subdir-list` など）があるか確認する。
- URLが想定どおり `http://127.0.0.1:8000/` か確認する。
- API疎通確認として `http://127.0.0.1:8000/api/subdirectories` のステータスも別途確認する。

## 画像保存先ルール
- スクリーンショットやデバッグ出力は、必ず相対パスで保存する。
- 例: `artifacts/home.png`（推奨）
- 絶対パス（例: `/tmp/home.png`）は使わない。
