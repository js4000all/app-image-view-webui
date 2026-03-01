#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-quick}"

if [[ "$MODE" != "quick" && "$MODE" != "full" ]]; then
  echo "Usage: $0 [quick|full]" >&2
  exit 1
fi

echo "[verify] Export OpenAPI spec from FastAPI"
python tools/export_openapi.py

echo "[verify] Install frontend dependencies"
npm --prefix frontend ci

echo "[verify] Generate SPA API client from OpenAPI spec"
npm --prefix frontend run generate:api-client

echo "[verify] Ensure spec/client are committed"
git diff --exit-code -- frontend/openapi/openapi.json frontend/src/generated/api

echo "[verify] Build SPA bundle"
npm --prefix frontend run build:bundle

if [[ "$MODE" == "full" ]]; then
  echo "[verify] Install Python dev dependencies"
  python -m pip install -r requirements-dev.txt

  echo "[verify] Install Playwright Chromium"
  python -m playwright install --with-deps chromium

  echo "[verify] Run E2E tests"
  pytest tests/e2e -q
else
  echo "[verify] Skip heavy E2E checks in quick mode"
fi

echo "[verify] Completed: mode=$MODE"
