#!/bin/zsh
set -e

PROJECT_DIR="${0:A:h}"
cd "$PROJECT_DIR"

echo "[1/3] 프론트엔드 패키지를 준비합니다."
[[ -d node_modules ]] || npm install

echo "[2/3] Python API 환경을 준비합니다."
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -q -r backend/requirements.txt

echo "[3/3] 영양 데이터베이스를 준비합니다."
if [[ ! -f data/foods.db ]]; then
  downloads_dir="$($PROJECT_DIR/.venv/bin/python -c 'from pathlib import Path; print(Path.home() / "Downloads")')"
  processed_file=("$downloads_dir"/*298288*xlsx(N[1]))
  food_file=("$downloads_dir"/*19495*xlsx(N[1]))
  if (( ${#processed_file} == 0 || ${#food_file} == 0 )); then
    echo "Downloads 폴더에서 원본 엑셀 파일을 찾지 못했습니다."
    echo "파일명에 298288 및 19495가 포함되어 있는지 확인해 주세요."
    exit 1
  fi
  .venv/bin/python backend/import_data.py "$processed_file[1]" "$food_file[1]"
else
  echo "기존 data/foods.db를 사용합니다."
fi

echo "준비가 완료되었습니다. ./start.sh 를 실행하세요."
