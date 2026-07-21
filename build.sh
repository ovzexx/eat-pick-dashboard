#!/bin/bash
set -e

pip install -r backend/requirements.txt

FOOD_FILE=$(find data/raw -name "*음식DB*" | head -1)
PROC_FILE=$(find data/raw -name "*가공식품DB*" | head -1)

echo "Importing: $FOOD_FILE"
echo "Importing: $PROC_FILE"

python backend/import_data.py "$FOOD_FILE" "$PROC_FILE"
