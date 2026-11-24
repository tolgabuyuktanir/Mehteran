#!/bin/sh
# Starts Mehteran on macOS and Linux: "sh scripts/mehter.sh <arguments>" (for example: ui).
# It uses Python 3.11 or later when the computer has one. Otherwise it installs uv (no administrator rights)
# and uv provides a private Python. Same search as scripts/start.sh, but it runs "python -m mehteran".
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

# "ui" first brings a git copy up to date, as scripts/start.sh does (the same update of the whole code folder; git
# replaces this file, the running shell keeps reading the old one).
if PY=$(find_python); then
  [ "$1" = "ui" ] && "$PY" -m mehteran update
  exec "$PY" -m mehteran "$@"
fi

UV=$(command -v uv 2>/dev/null)
[ -z "$UV" ] && [ -x "$HOME/.local/bin/uv" ] && UV="$HOME/.local/bin/uv"
if [ -z "$UV" ]; then
  echo "Python 3.11+ not found. Installing a private Python for Mehteran (uv; no administrator rights)..."
  echo "Python 3.11+ bulunamadi. Mehteran icin ayri bir Python kuruluyor (uv; yonetici izni gerekmez)..."
  if ! curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh; then
    echo "Installation failed. Install Python 3.11+ from https://www.python.org/downloads/ and try again."
    echo "Kurulum basarisiz. https://www.python.org/downloads/ adresinden Python 3.11+ kurup yeniden deneyin."
    exit 1
  fi
  UV="$HOME/.local/bin/uv"
fi
[ "$1" = "ui" ] && "$UV" run --no-project --python 3.12 python -m mehteran update
exec "$UV" run --no-project --python 3.12 python -m mehteran "$@"
