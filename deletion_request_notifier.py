#!/usr/bin/python
"""
Inform users about deletion requests.

This script informs creator and main authors about deletion requests.

The following parameters are supported:

-always           If used, the bot won't ask if it should file the message
                  onto user talk page

-init             Initialize the cache file

-retry            Retry wikihistory a second time

"""
#
# (C) xqt, 2013-2023
#
# Distributed under the terms of the MIT license.
#
from __future__ import annotations

import pickle
import re

from collections import Counter
from contextlib import suppress
from datetime import datetime
from itertools import chain

import pywikibot
from pywikibot import textlib
from pywikibot.bot import ExistingPageBot, SingleSiteBot
from pywikibot.comms.http import fetch, requests
from pywikibot.date import enMonthNames
from pywikibot.tools import is_ip_address

msg = '{{ers:user:xqbot/LD-Hinweis|%(page)s|%(action)s|%(date)s}}'
opt_out = 'Benutzer:Xqbot/Opt-out:LD-Hinweis'


class DeletionRequestNotifierBot(ExistingPageBot, SingleSiteBot):

    """A bot which inform user about Articles For Deletion requests."""

    summary = ('Bot: Benachrichtigung über Löschdiskussion zum Artikel '
               '[[%(page)s]]')

    def __init__(self, **kwargs):
        """Initializer."""
        self.available_options.update({
            'init': False,
            'retry': 60,
        })
        super().__init__(**kwargs)
        self.ignoreUser = set()
        self.writelist = []

    def moved_page(self, source) -> str | None:
        """
        Find the move target for a given page.

        :param source: page title
        :type source: str or pywikibot.Link
        :return: target page title
        """
        page = pywikibot.Page(pywikibot.Link(source))
        gen = iter(self.site.logevents(logtype='move', page=page, total=1))
        with suppress(StopIteration):
            lastmove = next(gen)
            return lastmove.target_title
        return None

    def setup(self):
        """Read ignoring lists."""
        pywikibot.info('Reading ignoring lists...')
        ignore_page = pywikibot.Page(self.site, opt_out)
        self.ignoreUser.clear()
        for page in ignore_page.linkedPages():
            if page.namespace() in (2, 3):
                self.ignoreUser.add(
                    page.title(with_ns=False,
                               with_section=False).split('/')[0])
        ignore_page = pywikibot.Page(
            self.site, 'Gedenkseite für verstorbene Wikipedianer',
            ns=self.site.namespaces.lookup_name('Project'))
        for page in ignore_page.linkedPages():
            if page.namespace() in (2, 3):
                self.ignoreUser.add(
                    page.title(with_ns=False,
                               with_section=False).split('/')[0])
        pywikibot.info(f'{len(self.ignoreUser)} users found to opt-out')

    def teardown(self):
        """Some cleanups."""
        self.writefile(self.writelist)
        self.opt.init = False

    @property
    def generator(self):
        """Generator property."""
        oldlist = set() if self.opt.init else self.readfile()
        cat1 = pywikibot.Category(self.site,
                                  'Kategorie:Wikipedia:Löschkandidat')
        cat2 = pywikibot.Category(self.site,
                                  'Kategorie:Wikipedia:Löschkandidat/Vorlagen')
        gen = chain(cat1.articles(), cat2.articles())
        newlist = {p.title() for p in gen}
        pywikibot.info('Check for moved pages...')
        for title in oldlist - newlist:
            try:
                target = self.moved_page(title)
            except KeyError:  # Log enty (move) has no 'move' key
                target = None
            if target:
                oldlist.add(target)
                pywikibot.info(f'<<< {title} was moved to {target}')

        pywikibot.info('Processing data...')
        self.writelist = oldlist
        for article in newlist - oldlist:
            if not self.opt.init:
                yield pywikibot.Page(pywikibot.Link(article))
            self.writelist.add(article)
        # all of them are done, delete the old entries
        else:
            self.writelist = newlist

    def readfile(self):
        """
        Read page titles from file.

        @return: set of page titles
        @rtype: set
        """
        pywikibot.info('\nReading old article list...')
        filename = pywikibot.config.datafilepath('data', 'la.data')
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
            pywikibot.info(f'{len(data)} articles found')
        except (OSError, EOFError):
            data = set()
        return data

    def writefile(self, data):
        """
        Write page titles to file.

        @param data: set of page titles
        @type data: set
        """
        pywikibot.info(f'Writing {len(data)} article names to file')
        filename = pywikibot.config.datafilepath('data', 'la.data')
        with open(filename, 'wb') as f:
            pickle.dump(data, f)

    def get_revisions_until_request(self):
        """Read the version history until the deletion template was found."""
        for r in self.current_page.revisions(content=True):
            if '{{Löschantragstext' not in r.text:
                return
            user = None if r.anon else r.user
            yield user, r.timestamp

    def treat_page(self):
        """Process a given page.

        Get the creator of the page and get the main authors from wikihistory.
        """
        page = self.current_page
        pywikibot.info('is tagged for deleting.\n')

        # read the oldest_revision with content
        old_rev = next(page.revisions(total=1, reverse=True, content=True))

        # If the oldest version is a redirect, don't asume him as creator.
        # Maybe the page was just moved.
        # In case of copyright violence, the text might be deleted. Don't
        # inform the creator in that case.
        if not (old_rev.text is None
                or page.site.redirect_regex.search(old_rev.text)):
            creator = old_rev.user
        else:
            creator = None

        # You may not inform the latest editors:
        # either they tagged the deletion request or they saw it
        latest = set()
        oldest = old_rev.timestamp
        for user, timestamp in self.get_revisions_until_request():
            if user:
                latest.add(user)
            oldest = timestamp

        delta = datetime.now() - datetime.utcnow()
        oldest += delta
        month = self.site.mediawiki_message(enMonthNames[oldest.month - 1])
        daytalk = f'{oldest.day}. {month} {oldest.year}'

        # inform creator
        if creator and creator not in latest:
            try:
                user = pywikibot.User(self.site, creator)
            except pywikibot.exceptions.InvalidTitleError:
                # Vorlage:Countytabletop
                pywikibot.exception()
            else:
                if self.could_be_informed(user, 'Creator'):
                    pywikibot.info('>>> Creator is ' + creator)
                    self.inform(user, page=page.title(), action='angelegte',
                                date=daytalk)

        # inform main authors for articles
        for author, percent in self.find_authors(page):
            if author in self.ignoreUser:
                pywikibot.info(
                    f'>>> Main author {author} ({percent} %) has opted out')
                continue
            if (author not in latest and author != creator):
                try:
                    user = pywikibot.User(self.site, author)
                except pywikibot.exceptions.InvalidTitleError:
                    pywikibot.exception()
                    pywikibot.error(
                        f'author name {author} is an invalid title')
                    continue
                if self.could_be_informed(user, 'Main author'):
                    pywikibot.info(
                        f'>>> Main author {author} with {percent} % edits')
                    self.inform(user,
                                page=page.title(),
                                action='{}überarbeitete'.format(
                                    'stark ' if percent >= 25 else ''),
                                date=daytalk)
            elif author != creator:
                pywikibot.info(
                    f'"{author}" has already seen the deletion request.')

    def could_be_informed(self, user: pywikibot.User, group) -> bool:
        """Check whether user could be informed.

        Also print additional informations.
        :param user: The user to be informed
        :return: whether user could be informed or not
        """
        if user.username in self.ignoreUser:
            pywikibot.info(f'>>> {group} { user.username} has opted out')
        elif not user.isRegistered():
            pywikibot.info(f'>>> {group} is an IP user, skipping')
        elif user.is_blocked():
            pywikibot.info(f'>>> {group} {user.username} is blocked, skipping')
        elif 'bot' in user.groups():
            pywikibot.info(f'>>> {group} {user.username} is a bot, skipping')
        else:
            return True
        return False

    def find_authors(self, page: pywikibot.Page):
        """Retrieve main authors of given page.

        .. note:: userPut() sets current_page therefore we cannot use it.

        :param page: Page object to retrieve main authors
        :return: yield tuple of user name and edit quantity
        :rtype: generator
        """
        percent = 0
        if page.namespace() == pywikibot.site.Namespace.MAIN:
            url = (f'https://wikihistory.toolforge.org/dewiki/'
                   f'getauthors.php?page_id={page.pageid}&onlynew=1')
            for _ in range(5):  # retries
                try:
                    r = fetch(url)
                except (requests.exceptions.ConnectionError,
                        requests.exceptions.ReadTimeout):
                    pywikibot.exception()
                else:
                    if r.status_code != 200:
                        pywikibot.warning(
                            f'wikihistory request status is {r.status_code}')
                    elif 'Timeout' in r.text:
                        pywikibot.warning('wikihistory timeout.')
                    else:
                        pattern = (r'><bdi>(?P<author>.+?)</bdi></a>\s'
                                   r'\((?P<percent>\d{1,3})&')
                        for main, main_cnt in re.findall(pattern, r.text):
                            main_cnt = int(main_cnt)
                            percent += main_cnt
                            if ' weitere' in main or main_cnt < 10:
                                break
                            yield main, main_cnt
                            if percent > 66:
                                break
                        break
                    if self.opt.retry:
                        pywikibot.info(
                            f'Retry in {self.opt.retry} s.')
                    pywikibot.sleep(self.opt.retry)

        if percent:
            return

        # A timeout occured or not main namespace, calculate it yourself
        pywikibot.info(f'No wikihistory data available for {page}.\n'
                       f'Retrieving revisions.')
        cnt: Counter[float | int]
        cnt = Counter()

        for rev in page.revisions():
            if is_ip_address(rev.user):
                continue
            if rev.minor:
                cnt[rev.user] += 0.2  # type: ignore[assignment]
            else:
                cnt[rev.user] += 1

        s = sum(cnt.values())
        s2 = sum(i ** 2 for i in cnt.values())
        n = float(max(len(cnt), 1))
        x_ = s / n
        q = (s2 / n - x_ ** 2)
        # avg + stdabw
        limit = max(3, q ** 0.5 * 1.5 + x_) if q > 0 else 3

        for main, main_cnt in cnt.most_common(7):
            if main_cnt < limit:
                break
            yield main, main_cnt * 100 / s

    def inform(self, user: pywikibot.User, **param):
        """
        Inform user about deletion request.

        :param user: user to be informed
        :keyword page: page title
        :type page: str
        :keyword action: action done by editor
        :type action: str
        """
        talk = user.getUserTalkPage()
        while talk.isRedirectPage():
            talk = talk.getRedirectTarget()
            if talk == user.getUserTalkPage():
                pywikibot.warning(f'{talk} forms a redirect loop. Skipping')
                return
        if not talk.isTalkPage():
            pywikibot.warning(f'{talk} is not a talk page. Skipping')
            return
        if talk.exists():
            text = talk.text + '\n\n'
            if textlib.does_text_contain_section(
                    text, '[[{page}]]'.format(**param)):
                pywikibot.info(
                    f'NOTE: user {user.username} was already informed')
                return
        else:
            text = ''
        param['user'] = user.username
        text += msg % param
        if not self.userPut(talk, talk.text, text, minor=False,
                            summary=self.summary % param,
                            ignore_save_related_errors=True,
                            ignore_server_errors=True):
            pywikibot.warning(f'Page {talk} not saved.')


def main():
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    :param args: command line arguments
    :type args: list of unicode
    """
    options = {}
    for arg in pywikibot.handle_args():
        opt, _, value = arg.partition(':')
        if not opt.startswith('-'):
            continue
        opt = opt[1:]
        if not value:
            value = True
        elif value.isdigit():
            value = int(value)
        options[opt] = value

    bot = DeletionRequestNotifierBot(**options)
    while True:
        bot.run()
        pywikibot.info('Waiting 300 seconds...\n')
        try:
            pywikibot.sleep(300)
        except KeyboardInterrupt:
            bot.exit()
            break


if __name__ == '__main__':
    main()
