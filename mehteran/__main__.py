"""python -m mehteran <command>"""

import sys

# A console or file that cannot show a character must not stop the command (Windows code pages).
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(errors="replace")

from .cli import main  # noqa: E402

sys.exit(main())
