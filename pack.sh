#!/usr/bin/env bash
# GawdZilla — package source for GitHub upload
set -e

NAME="GawdZilla"
VERSION="$(cat VERSION 2>/dev/null || echo 1.0.0)"
OUT="${NAME}-v${VERSION}.zip"

if [[ ! -f "GawdZilla.py" ]]; then
  echo "[!] Run from the project root."
  exit 1
fi

rm -f "$OUT"

zip -r "$OUT" . \
  -x "data/*.db" \
  -x "data/logs/*" \
  -x "data/backups/*.db" \
  -x "data/builds/*.zip" \
  -x "data/media/*" \
  -x "data/certs/*.key" \
  -x "data/certs/*.crt" \
  -x ".venv/*" \
  -x "**/__pycache__/*" \
  -x "**/*.pyc" \
  -x "agents/android/.gradle/*" \
  -x "agents/android/build/*" \
  -x "agents/android/app/build/*" \
  -x "agents/android/*.keystore" \
  -x "agents/android/keystore.properties" \
  -x "agents/android/local.properties" \
  -x ".git/*" \
  -x "*.zip" \
  -x "*.log" \
  -x "*.bak" \
  -x "*.old"

echo "[✓] Packaged: $OUT"
ls -lh "$OUT"
