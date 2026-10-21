#!/usr/bin/env bash
# Builds every docs/src/*.html into a PDF in docs/pdf/ using headless Google Chrome.
# Usage: tools/build-docs.sh            (all documents)
#        tools/build-docs.sh 01-episode-1   (one document, by file name without .html)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/docs/src"
OUT="$ROOT/docs/pdf"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

mkdir -p "$OUT"

if [[ $# -gt 0 ]]; then
  files=("$SRC/$1.html")
else
  files=("$SRC"/*.html)
fi

for html in "${files[@]}"; do
  name="$(basename "$html" .html)"
  # The PDF file name comes from the <meta name="pdf-name"> tag, falling back to the source name.
  pdf_name="$(sed -n 's/.*<meta name="pdf-name" content="\([^"]*\)".*/\1/p' "$html" | head -1)"
  pdf_name="${pdf_name:-$name}"
  echo "Building $pdf_name.pdf"
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
    --virtual-time-budget=5000 --run-all-compositor-stages-before-draw \
    --print-to-pdf="$OUT/$pdf_name.pdf" "file://$html" 2>/dev/null
done

echo "Done → $OUT"
