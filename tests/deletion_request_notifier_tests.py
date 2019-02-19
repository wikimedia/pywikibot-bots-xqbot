# -*- coding: utf-8 -*-
"""Test imagereview modules."""
#
# (C) xqt, 2016-2018
#
# Distributed under the terms of the MIT license.
#
from __future__ import \
     absolute_import, division, print_function, unicode_literals

import unittest

import pywikibot
from pywikibot import config

from tests import utils  # noqa
from deletion_request_notifier import DeletionRequestNotifierBot  # noqa


class DRNTestBot(DeletionRequestNotifierBot):

    """Test class of DeletionRequestNotifierBot."""

    def __init__(self, **kwargs):
        """Initializer."""
        super(DRNTestBot, self).__init__(**kwargs)
        self.users = []

    def inform(self, user, **param):
        """Redefine inform method to get informed user as list."""
        self.users.append(user.title(withNamespace=False))


class TestDeletionRequestNotifierBot(unittest.TestCase):

    """Test DeletionRequestNotifierBot."""

    @classmethod
    def setUpClass(cls):
        """Setup Class."""
        config.family = 'wikipedia'
        config.mylang = 'de'
        cls.bot = DRNTestBot()
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