# -*- coding: utf-8 -*-
"""Test imagereview modules."""
#
# (C) xqt, 2016-2018
#
# Distributed under the terms of the MIT license.
#
from __future__ import absolute_import, print_function, unicode_literals

import unittest

from tests import utils  # noqa
import afd_notice  # noqa

import pywikibot
from pywikibot import config


class TestBot(afd_notice.AFDNoticeBot):

    """Test class of AFDNoticeBot."""

    def __init__(self, **kwargs):
        """Initializer."""
        super(TestBot, self).__init__(**kwargs)
        self.users = []

    def inform(self, user, **param):
        """Redefine inform method to get informed user as list."""
        self.users.append(user.title(withNamespace=False))


class TestAFDNoticeBot(unittest.TestCase):

    """Test CheckImageBot."""

    @classmethod
    def setUpClass(cls):
        """Setup Class."""
        config.family = 'wikipedia'
        config.mylang = 'de'
        cls.bot = TestBot()
        cls.bot.treat(pywikibot.Page(pywikibot.Link('Hydraulik')))

    def test_creator(self):
        """Test creator."""
        if not self.bot.users:
            self.skipTest('No entries in self.bot.users')
        self.assertEqual(self.bot.users[0], 'Ulfb')

    def test_authors(self):
        """Test main author."""
        if not self.bot.users:
            self.skipTest('No entries in self.bot.users')
        self.assertEqual(self.bot.users[1], 'Xqt')

    def test_length(self):
        """Test wikihistory length."""
        self.assertGreater(len(self.bot.users), 0)
        self.assertLessEqual(len(self.bot.users), 6)


if __name__ == '__main__':
    try:
        unittest.main()
    except SystemExit:
        pass
