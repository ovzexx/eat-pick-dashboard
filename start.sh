#!/bin/zsh
set -e

PROJECT_DIR="${0:A:h}"
cd "$PROJECT_DIR"

if [[ ! -d node_modules || ! -x .venv/bin/uvicorn || ! -f data/foods.db ]]; then
  ./setup.sh
fi

cleanup() {
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "API 서버를 시작합니다: http://127.0.0.1:8787"
.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8787 > api.log 2>&1 &
API_PID=$!

echo "웹앱을 시작합니다: http://127.0.0.1:5173"
echo "종료하려면 Ctrl+C를 누르세요."
npm run dev -- --host 127.0.0.1
