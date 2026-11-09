import sys

if sys.version_info < (3, 11):
    sys.exit("Python 3.11 or later is required / Python 3.11 veya üzeri gerekli (found / bulunan: %d.%d)." % sys.version_info[:2])

# A console or file that cannot show a character must not stop the run (Windows code pages).
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(errors="replace")

from .cli import main  # noqa: E402

sys.exit(main())
