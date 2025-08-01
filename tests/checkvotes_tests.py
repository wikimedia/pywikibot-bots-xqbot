"""Test vandalism modules."""
#
# (C) xqt, 2016-2025
#
# Distributed under the terms of the MIT license.
#
from __future__ import annotations

import unittest

from pywikibot.comms.http import fetch

from checkvotes import SB_TOOL, SB_TOOL_NEW


class TestPathsMeta(type):

    """Test meta class."""

    def __new__(cls, name, bases, dct):
        """Create the new class."""
        def test_method(tool):

            def test_tools_path(self):
                """Test tools path."""
                if '?' in tool:
                    self.skipTest(f'"{tool}" is a regex!')
                path = 'http://tools.wmflabs.org/{}?user={}'.format(tool,
                                                                    'xqt')
                request = fetch(path)
                self.assertIn(request.status_code, (200, 207),
                              'Http response status {} for {!r}'
                              .format(request.status_code, tool))

            return test_tools_path

        for i, tool in enumerate((SB_TOOL, SB_TOOL_NEW)):
            test_name = 'test_SB_TOOL_' + str(i)
            dct[test_name] = test_method(tool)

        return type.__new__(cls, name, bases, dct)


class TestPaths(unittest.TestCase, metaclass=TestPathsMeta):

    """Test remote paths."""


if __name__ == '__main__':
    unittest.main()
