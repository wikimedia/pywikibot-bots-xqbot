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

import pywikibot

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


class TestDUP_Image(unittest.TestCase):

    """Test DUP_Image class."""

    REMARK = 'Urheber und Uploader sind nicht identisch.'
    TMPL = '{{düp|Lizenz|Freigabe | Quelle| Urheber | Hinweis = %s }}' % REMARK

    @classmethod
    def setUpClass(cls):
        cls.site = pywikibot.Site('de', 'wikipedia')
        cls.review_tpl = pywikibot.Page(cls.site, 'düp', 10)

    @classmethod
    def tearDownClass(cls):
        del cls.site
        del cls.review_tpl

    def tearDown(self):
        del self.image

    def init_content(self):
        self.image = imagereview.DUP_Image(self.site, 'Sample.jpg', self.TMPL)
        self.image._templates.append(self.review_tpl)
        self.image.text += self.TMPL
        self.assertEqual(self.image.text, self.image._text)
        self.image.__init__(self.image.site, self.image.title(), self.image.text)
        self.assertEqual(self.image._contents, self.image.text)

    def test_empty_instance(self):
        """Test instance variables"""
        self.image = imagereview.DUP_Image(self.site, 'Sample.jpg')
        self.assertIsNone(self.image._contents)
        self.assertIsNone(self.image._editTime)
        self.assertEqual(self.image._file_revisions, dict())
        self.assertEqual(self.image._revisions, dict())
        self.assertIsNone(self.image.done)
        self.assertFalse(self.image.info)
        self.assertEqual(self.image.reasons, set([]))
        self.assertIsNone(self.image.remark)
        self.assertEqual(self.image.review_tpl, list())

    def test_instance_with_content(self):
        """Test instance variables with content given."""
        self.init_content()
        self.assertIsNone(self.image._editTime)
        self.assertFalse(self.image.done)
        self.assertTrue(self.image.info)
        self.assertEqual(len(self.image.reasons), 5)
        self.assertIsNone(self.image.remark)
        self.assertEqual(self.image.review_tpl[0], self.review_tpl)

    def test_valid_reasons(self):
        """Test validReasons method."""
        self.init_content()
        self.assertTrue(self.image.validReasons)
        self.assertEqual(self.image.remark, self.REMARK)
        self.assertLessEqual(self.image.reasons, set(imagereview.DUP_REASONS))

    def test_hasRefs(self):
        """Test hasRefs method."""
        self.init_content()
        self.assertTrue(self.image.hasRefs)


if __name__ == '__main__':
    try:
        unittest.main()
    except SystemExit:
        pass
