# ARCHITECTURE

このドキュメントは、AI エージェントが `app-image-view-webui` の構成を短時間で把握し、変更影響を見積もるためのガイドです。

## 技術スタック

- **Backend**: Python, FastAPI, Uvicorn
- **Frontend (Home/Viewer画面)**: React + TypeScript + Vite
- **テスト**: pytest（API / E2E）
- **配信方式**:
  - `/` は `static/home-app/index.html`（Reactビルド成果物）を配信
  - `/viewer` も同一の `static/home-app/index.html`（SPA）を配信
  - `/api/*` は FastAPI の JSON API

---

## 全体ディレクトリ構成（要点）

- `app/`: FastAPI アプリ本体
  - `main.py`: ルート定義とアプリ組み立て
  - `api/routes.py`: API エンドポイント
  - `services/`: ユースケースロジック
  - `repositories/`: ファイルシステムアクセス
  - `models/`: API 入出力スキーマ
- `frontend/`: React + TypeScript の画面ソース
  - `src/features/home/`: ホーム画面の機能単位モジュール
  - `src/features/viewer/`: 閲覧画面の機能単位モジュール
- `static/`: 配信される静的ファイル
  - `home-app/`: SPA の React ビルド成果物
  - `styles.css`: 共通スタイル
- `tests/`: API / E2E テスト
- `docs/`: 運用・設計ドキュメント

---

## Frontend（ホーム画面）の構成方針

ホーム画面は「**機能単位（feature-first）**」で分割しています。

- `frontend/src/App.tsx`
  - エントリーポイントから呼ばれる薄いルートコンポーネント
- `frontend/src/features/home/pages/HomePage.tsx`
  - 画面全体のレイアウトとユースケース結合（再読み込み、名前変更後の更新）
- `frontend/src/features/home/components/SubdirectoryCard.tsx`
  - ディレクトリ1件分の表示と rename 操作
- `frontend/src/features/home/hooks/useSubdirectories.ts`
  - サブディレクトリ一覧の取得状態管理（loading/status）
- `frontend/src/features/home/hooks/useSubdirectoryThumbnails.ts`
  - サムネイル遅延読み込み（IntersectionObserver）
- `frontend/src/features/home/api/homeApi.ts`
  - ホーム画面で使う API 呼び出し
- `frontend/src/api/http.ts`
  - 汎用 HTTP ヘルパー
- `frontend/src/types/home.ts`
  - ホーム画面関連型

この分割により、`App.tsx` への責務集中を避け、画面ロジック・表示・通信を独立して変更できます。

---

## Backend の責務分離

- `routes.py`: HTTP の入出力責務（リクエスト・レスポンス）
- `services/`: 業務ルール（ディレクトリや画像一覧の取得、検証）
- `repositories/filesystem.py`: OS ファイル操作の詳細

変更時は、原則として上位レイヤーから下位レイヤーへの依存方向を維持してください。

---

## 変更時の実務ルール（AIエージェント向け）

1. **まず回帰防止**: 一覧表示と viewer 遷移の基本導線を壊さない。
2. **最小差分**: 無関係な整形や命名変更を混ぜない。
3. **成果物更新**: `frontend` 変更時はビルドし、`static/home-app/` の成果物差分も確認する。
4. **検証を記録**: 実行コマンドと結果を `docs/agent-handoff/tasks/*.md` に残す。

---

## よく使うコマンド

### アプリ起動

```sh
python app.py tests/resources/image_root
```

### フロントエンドビルド

```sh
cd frontend
npm ci
npm run build:bundle
```

### テスト

依存関係を未インストールの状態で `pytest` を実行すると失敗するため、先に開発用依存を導入してください。

```sh
pip install -r requirements-dev.txt
pytest -q
```
