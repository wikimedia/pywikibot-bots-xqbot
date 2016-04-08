# -*- coding: utf-8  -*-
"""Test vandalism modules."""
#
# (C) xqt, 2015
#
# Distributed under the terms of the MIT license.
#
from __future__ import absolute_import, unicode_literals

__version__ = '$Id$'

import inspect
import os
import sys
import unittest

currentdir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import imagereview


class TestMessages(unittest.TestCase):

    """Test messages."""

    net = False

    def test_message_keys(self):
        """Test message keys for mail and talk page."""
        self.assertEqual(imagereview.remark.keys(),
                         imagereview.remark_mail.keys())
        self.assertEqual(set(imagereview.remark.keys()),
                         set(imagereview.DUP_REASONS))

    def test_message_exist(self):
        """Test whether messages exists."""
        self.assertTrue(hasattr(imagereview, 'msg'))
        self.assertTrue(hasattr(imagereview, 'mail_msg'))


if __name__ == '__main__':
    try:
        unittest.main()
    except SystemExit:
        pass
