"""Test vandalism modules."""
#
# (C) xqt, 2015-2021
#
# Distributed under the terms of the MIT license.
#
from __future__ import annotations

import re
import unittest

from tests import utils  # noqa
from vandalism import getAccuser, isIn  # noqa


class TestVandalismMethods(unittest.TestCase):

    """Test vandalism modules."""

    dry = True

    def test_get_accuser(self):
        """Test getAccUser method."""
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
            'foo [[Benutzerin:xqt|Xqt]] bar '
            '11:46, 15. Nov. 2012 (CET) baz'),
            ('xqt', '2012 Nov 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar [[benutzerin:xqt|xqt]] '
            '11:46, 15. Nov. 2013 (CET) baz'),
            ('xqt', '2013 Nov 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar [[benutzerin:xqt|xqt]] '
            '11:46, 15. Mai 2014 (CEST)'),
            ('xqt', '2014 Mai 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar [[user:Xqt|xqt]] '
            '11:46, 15. Apr. 2015 (CEST) baz'),
            ('Xqt', '2015 Apr 15 11:46'))
        self.assertEqual(getAccuser(
            'foo bar [[User_talk:xqt|Xqt]] '
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

    def test_vmHeadlineRegEx(self):  # noqa: N802
        """Test vmHeadlineRegEx."""
        self.assertIsNotNone(isIn('== [[Benutzer:Xqt1]] ==',
                                  re.escape('Xqt1')))
        self.assertIsNotNone(isIn('== [[Benutzer:xqt2]] ==',
                                  re.escape('Xqt2')))
        self.assertIsNotNone(isIn('== [[Benutzerin:Xqt3]] ==',
                                  re.escape('Xqt3')))
        self.assertIsNotNone(isIn('== [[User:Xqt4]] ==',
                                  re.escape('Xqt4')))
        self.assertIsNotNone(isIn('== [[user:Xqt5]] ==',
                                  re.escape('Xqt5')))
        self.assertIsNotNone(isIn('== [[user:Xqt5]] ==',
                                  re.escape('Xqt5')))
        self.assertIsNotNone(isIn('== [[Benutzer:77.7.117.89]] ==',
                                  re.escape('77.7.117.89')))
        self.assertIsNotNone(isIn('== [[Benutzer:77.7.117.89]] ==',
                                  re.escape('77.7.117.89')))
        self.assertIsNotNone(isIn(
            '== [[Benutzer:2003:D3:83C0:CB00:45F1:1850:1E89:1E22]] ==',
            re.escape('2003:D3:83C0:CB00:45F1:1850:1E89:1E22')))
        self.assertIsNotNone(isIn(
            '== [[Benutzer:2003:d3:83c0:cb00:45f1:1850:1e89:1e22]] ==',
            re.escape('2003:D3:83C0:CB00:45F1:1850:1E89:1E22')))


if __name__ == '__main__':
    unittest.main()
