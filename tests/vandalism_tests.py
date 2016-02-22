# -*- coding: utf-8  -*-
"""Test vandalism modules."""
#
# (C) xqt, 2015
#
# Distributed under the terms of the MIT license.
#
from __future__ import absolute_import, unicode_literals

__version__ = '$Id$'

from vandalism import getAccuser

from tests.aspects import unittest, TestCase


class TestVandalismMethods(TestCase):

    """Test vandalism modules."""

    dry = True

    def test_get_accuser(self):
        """Test getAccUser method"""
        self.assertEqual(getAccuser(''), ('', ''))
        self.assertEqual(getAccuser(
            'foo bar ([[Benutzer:xqt|xqbot]]) '
            '11:46, 15. Nov. 2010 (CET) baz'),
            ('xqt', '2010 Nov 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar ([[Benutzer:xqt|Xqt]]) '
            '11:46, 15. Nov. 2011 (CET) baz'),
            ('xqt', '2011 Nov 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar ([[Benutzerin:xqt|Xqt]]) '
            '11:46, 15. Nov. 2012 (CET) baz'),
            ('xqt', '2012 Nov 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar ([[benutzerin:xqt|xqt]]) '
            '11:46, 15. Nov. 2013 (CET) baz'),
            ('xqt', '2013 Nov 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar ([[benutzerin:xqt|xqt]]) '
            '11:46, 15. Mai 2014 (CEST)'),
            ('xqt', '2014 Mai 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar ([[user:Xqt|xqt]]) '
            '11:46, 15. Apr. 2015 (CEST) baz'),
            ('Xqt', '2015 Apr 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar ([[User_talk:xqt|Xqt]]) '
            '11:46, 15. Nov. 2016 (CEST)'),
            ('xqt', '2016 Nov 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar ([[Spezial:Beiträge/Xqt|xqt]]) '
            '11:46, 15. Nov. 2017 (CEST) baz'),
            ('Xqt', '2017 Nov 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar ([[Benutzer Diskussion:xqt|Diskussion]]) '
            '11:46, 15. Nov. 2018 (CET) baz'),
            ('xqt', '2018 Nov 15 11:46'))


if __name__ == '__main__':
    try:
        unittest.main()
    except SystemExit:
        pass
