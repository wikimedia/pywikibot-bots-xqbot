# -*- coding: utf-8  -*-
"""Test vandalism modules."""
#
# (C) xqt, 2016
#
# Distributed under the terms of the MIT license.
#
from __future__ import absolute_import, print_function, unicode_literals

__version__ = '$Id$'

import unittest

from tests import utils  # noqa
from pywikibot.comms.http import fetch

from checkvotes import SB_TOOL, SB_TOOL2, SB_TOOL3, SB_TOOL_NEW


class TestPathsMeta(type):

    """Test meta class."""

    def __new__(cls, name, bases, dct):
        """Create the new class."""
        def test_method(tool):

            def test_tools_path(self):
                """Test tools path."""
                if '?' in tool:
                    self.skipTest('"{0}" is a regex!'.format(tool))
                path = 'http://tools.wmflabs.org/%s?user=%s' % (tool, 'xqt')
                request = fetch(path)
                self.assertIn(request.status, (200, 207),
                              'Http response status {0} for "{1}"'
                              ''.format(request.data.status_code, tool))

            return test_tools_path

        for i, tool in enumerate((SB_TOOL, SB_TOOL2, SB_TOOL3, SB_TOOL_NEW)):
            test_name = 'test_SB_TOOL_' + str(i)
            dct[test_name] = test_method(tool)

        return type.__new__(cls, name, bases, dct)


class TestPaths(unittest.TestCase):

    """Test remote paths."""

    __metaclass__ = TestPathsMeta


if __name__ == '__main__':
    try:
        unittest.main()
    except SystemExit:
        pass
