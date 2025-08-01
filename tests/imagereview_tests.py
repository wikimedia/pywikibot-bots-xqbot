"""Test imagereview modules."""
#
# (C) xqt, 2016-2025
#
# Distributed under the terms of the MIT license.
#
from __future__ import annotations

import unittest

import pywikibot
from pywikibot import Timestamp, config, pagegenerators

import imagereview


class TestMessages(unittest.TestCase):

    """Test messages."""

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


class TestDUP_Image(unittest.TestCase):  # noqa: N801

    """Test DUP_Image class."""

    REMARK = 'Urheber und Uploader sind nicht identisch.'
    TMPL = '{{düp|Lizenz|Freigabe | Quelle| Urheber | Hinweis = %s }}' % REMARK

    @classmethod
    def setUpClass(cls):
        """Setup class."""
        super().setUpClass()
        cls.site = pywikibot.Site('de', 'wikipedia')
        cls.review_tpl = pywikibot.Page(cls.site, 'düp', 10)

    @classmethod
    def tearDownClass(cls):
        """Cleanup Class."""
        del cls.site
        del cls.review_tpl
        super().tearDownClass()

    def tearDown(self):
        """Cleanup methods."""
        del self.image
        super().tearDown()

    def init_content(self):
        """Instantiate DUP_Image."""
        self.image = imagereview.DUP_Image(self.site, 'Sample.jpg', self.TMPL)
        self.image._templates.add(self.review_tpl)
        self.image.text += self.TMPL
        self.assertEqual(self.image.text, self.image._text)
        self.image.__init__(self.image.site, self.image.title(),
                            self.image.text)
        self.assertEqual(self.image._contents, self.image.text)

    def test_empty_instance(self):
        """Test instance variables."""
        self.image = imagereview.DUP_Image(self.site, 'Sample.jpg')
        self.assertIsNone(self.image._contents)
        self.assertIsNone(self.image._editTime)
        self.assertEqual(self.image._file_revisions, {})
        self.assertEqual(self.image._revisions, {})
        self.assertIsNone(self.image.done)
        self.assertFalse(self.image.info)
        self.assertEqual(self.image.reasons, set())
        self.assertIsNone(self.image.remark)
        self.assertEqual(self.image.review_tpl, [])

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
        """Test valid_reasons method."""
        self.init_content()
        self.assertTrue(self.image.valid_reasons)
        self.assertEqual(self.image.remark, self.REMARK)
        self.assertLessEqual(self.image.reasons, set(imagereview.DUP_REASONS))


class TestCheckImageBot(unittest.TestCase):

    """Test CheckImageBot."""

    @classmethod
    def setUpClass(cls):
        """Setup Class."""
        config.family = 'wikipedia'
        config.mylang = 'de'

    def test_list_option(self):
        """Test run method with list options."""
        bot = imagereview.CheckImageBot(list=True, total=1)
        self.assertEqual(bot.sort, 1)
        self.assertTrue(bot.filter)
        self.assertEqual(bot.total, 1)

    def test_check_option(self):
        """Test run method with check options."""
        bot = imagereview.CheckImageBot(check=True)
        self.assertEqual(bot.sort, 0)
        self.assertFalse(bot.filter)
        self.assertEqual(bot.total, 25)

    def test_build_table_with_list(self):
        """Test buildt table with list option."""
        bot = imagereview.CheckImageBot(list=True)
        table = bot.build_table(save=False)
        if not table:
            self.skipTest('Table of files to review is empty')
        key = list(table.keys())[0]  # py3 comp
        data = table[key]
        item = data[0]
        self.assertIsInstance(key, str)
        self.assertIsInstance(data, list)
        self.assertIsInstance(item, list)
        self.assertEqual(len(item), 5)
        linkedtitle, uploader, filepage, reason, notifies = item
        user, time = uploader
        self.assertIsInstance(linkedtitle, str)
        self.assertIsInstance(uploader, list)
        self.assertIsInstance(filepage, imagereview.DUP_Image)
        self.assertIsInstance(user, str)
        self.assertIsInstance(time, str)
        self.assertIsNone(reason)
        self.assertIsNone(notifies)
        self.assertEqual(filepage.title(as_link=True, textlink=True),
                         linkedtitle)
        self.assertEqual(time, key)
        self.assertIsInstance(Timestamp.fromISOformat(time), Timestamp)

    def test_build_table_with_check(self):
        """Test buildt table with check option."""
        bot = imagereview.CheckImageBot(check=True, total=0)
        bot.cat = 'Nonexisting page for imagereview'
        table = bot.build_table(save=False, unittest=True)
        if not table:
            self.skipTest('Table of files to review is empty')
        key = list(table.keys())[0]  # py3 comp
        data = table[key]
        item = data[0]
        self.assertIsInstance(key, str)
        self.assertIsInstance(data, list)
        self.assertIsInstance(item, list)
        self.assertEqual(len(item), 5)
        linkedtitle, uploader, filepage, reason, notifies = item
        user, time = uploader
        self.assertIsInstance(linkedtitle, str)
        self.assertIsInstance(uploader, list)
        self.assertIsInstance(filepage, imagereview.DUP_Image)
        self.assertIsInstance(user, str)
        self.assertIsInstance(time, str)
        self.assertIsNone(reason)
        self.assertIsNone(notifies)
        self.assertEqual(filepage.title(as_link=True, textlink=True),
                         linkedtitle)
        self.assertEqual(user, key)
        self.assertIsInstance(Timestamp.fromISOformat(time), Timestamp)

    def test_generator(self):
        """Test generator."""
        bot = imagereview.CheckImageBot(check=True, total=0)
        cat = pywikibot.Category(
            bot.site,
            '{}:{}'.format(bot.site.namespaces.CATEGORY.custom_name,
                           bot.source))
        gen = pagegenerators.CategorizedPageGenerator(cat)
        a = [val for i, val in enumerate(gen) if i < 10]
        b = [val for i, val in enumerate(bot.generator) if i < 10]
        self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main()
