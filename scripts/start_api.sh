#!/bin/bash
# Run the SEO OS API server
# Usage: bash scripts/start_api.sh [--reload]
cd "$(dirname "$0")/.." || exit 1
uvicorn api.main:app --host 0.0.0.0 --port 8000 "$@"
