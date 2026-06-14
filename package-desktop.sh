#!/usr/bin/env bash
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="./.venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
	PYTHON_BIN="python3"
fi
"$PYTHON_BIN" ./scripts/package.py --variant desktop --platform debian