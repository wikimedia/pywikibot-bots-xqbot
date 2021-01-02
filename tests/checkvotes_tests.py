"""Test vandalism modules."""
#
# (C) xqt, 2016-2021
#
# Distributed under the terms of the MIT license.
#
from __future__ import annotations

import unittest

from pywikibot.comms.http import fetch

from tests import utils  # noqa
from checkvotes import SB_TOOL, SB_TOOL_NEW  # noqa: I100


class TestPathsMeta(type):

    """Test meta class."""

    def __new__(cls, name, bases, dct):
        """Create the new class."""
        def test_method(tool):

            def test_tools_path(self):
                """Test tools path."""
                if '?' in tool:
                    self.skipTest('"{}" is a regex!'.format(tool))
                path = 'http://tools.wmflabs.org/%s?user=%s' % (tool, 'xqt')
                request = fetch(path)
                self.assertIn(request.status_code, (200, 207),
                              'Http response status {} for "{}"'
                              ''.format(request.data.status_code, tool))

            return test_tools_path

        for i, tool in enumerate((SB_TOOL, SB_TOOL_NEW)):
            test_name = 'test_SB_TOOL_' + str(i)
            dct[test_name] = test_method(tool)

        return type.__new__(cls, name, bases, dct)


class TestPaths(unittest.TestCase, metaclass=TestPathsMeta):

    """Test remote paths."""

    pass


if __name__ == '__main__':
    unittest.main()
