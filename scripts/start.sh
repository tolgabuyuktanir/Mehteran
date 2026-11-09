#!/bin/sh
# Starts the application on macOS and Linux: "sh scripts/start.sh <arguments>" (for example: ui).
# It uses Python 3.11 or later when the computer has one. Otherwise it installs uv (no administrator rights)
# and uv provides a private Python for this application.
cd "$(dirname "$0")/.." || exit 1

find_python() {
  for name in python3.14 python3.13 python3.12 python3.11 python3; do
    path=$(command -v "$name" 2>/dev/null) || continue
    # macOS /usr/bin/python3 is old and can open an Xcode installation dialog: skip it.
    [ "$path" = /usr/bin/python3 ] && [ "$(uname)" = Darwin ] && continue
    "$path" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null && { echo "$path"; return 0; }
  done
  return 1
}

if PY=$(find_python); then
  exec "$PY" -m pipeline "$@"
fi

UV=$(command -v uv 2>/dev/null)
[ -z "$UV" ] && [ -x "$HOME/.local/bin/uv" ] && UV="$HOME/.local/bin/uv"
if [ -z "$UV" ]; then
  echo "Python 3.11+ not found. Installing a private Python for this application (uv; no administrator rights)..."
  echo "Python 3.11+ bulunamadi. Bu uygulama icin ayri bir Python kuruluyor (uv; yonetici izni gerekmez)..."
  if ! curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh; then
    echo "Installation failed. Install Python 3.11+ from https://www.python.org/downloads/ and try again."
    echo "Kurulum basarisiz. https://www.python.org/downloads/ adresinden Python 3.11+ kurup yeniden deneyin."
    exit 1
  fi
  UV="$HOME/.local/bin/uv"
fi
exec "$UV" run --no-project --python 3.12 python -m pipeline "$@"
