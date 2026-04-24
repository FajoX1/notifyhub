#!/usr/bin/env sh
set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python binary not found at $PYTHON_BIN"
  echo "Set PYTHON_BIN, for example: PYTHON_BIN=python3 scripts/test.sh"
  exit 1
fi

echo "Running Django checks..."
"$PYTHON_BIN" -m app check --settings=app.config.settings_test

echo "Running Django tests (SQLite in-memory)..."
"$PYTHON_BIN" -m app test --settings=app.config.settings_test

echo "Done."