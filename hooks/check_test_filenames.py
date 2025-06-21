#!/usr/bin/env python3
"""Pre-commit hook to test test filenames."""
#
# (C) xqt, 2025
#
# Distributed under the terms of the MIT license.
#
from __future__ import annotations

import sys
from pathlib import Path

PATTERN = 'tests.py'


def main(argv) -> int:
    """Test that test filenames ends with tests."""
    failed = False
    for filename in argv[1:]:
        path = Path(filename)
        if not path.name.endswith(PATTERN):
            print(f'Invalid test filename: {path.name};'  # noqa: T201
                  f' does not end with {PATTERN!r}')
            failed = True

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
