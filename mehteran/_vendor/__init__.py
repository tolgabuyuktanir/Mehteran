"""Third-party code bundled with Mehteran, so that it stays free of installed packages.

yaml/: PyYAML 6.0.2 (MIT, see yaml/LICENSE), the pure-Python package only (cyaml.py and the C extension removed).
Mehteran reads YAML only through mehteran.yamlio, which uses the safe loader and the safe dumper.
"""
