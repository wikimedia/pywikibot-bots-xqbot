#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Inform users about deletion requests.

This script informs creator and main authors about deletion requests.

The following parameters are supported:

-always           If used, the bot won't ask if it should file the message
                  onto user talk page

-init             Initialize the cache file

"""
#
# (C) xqt, 2013-2016
#
# Distributed under the terms of the MIT license.
#
from __future__ import absolute_import, unicode_literals

__version__ = '$Id: b8b58400a557856fe9df819978e4b30036e4a643 $'
#

from collections import Counter
import pickle
import time

import pywikibot
from pywikibot import config, pagegenerators, textlib
from pywikibot.bot import SingleSiteBot

msg = u'{{ers:user:xqbot/LD-Hinweis|%(page)s|%(action)s}}'
opt_out = u'Benutzer:Xqbot/Opt-out:LD-Hinweis'


class AFDNoticeBot(SingleSiteBot):

    """A bot which inform user about Articles For Deletion requests."""

    summary = "Bot: Benachrichtigung über Löschdiskussion zum Artikel [[%(page)s]]"

    def __init__(self, **kwargs):
        """Constructor."""
        self.availableOptions.update({
            'init': False,
        })
        super(AFDNoticeBot, self).__init__(**kwargs)
        self.ignoreUser = set()
        self.always = self.getOption('always')
        self.init = self.getOption('init')
        self._start_ts = pywikibot.Timestamp.now()

    def moved_page(self, source):
        """
        Find the move target for a given page.

        @param source: page title
        @type source: str or pywikibot.Link
        @return: target page title
        @rtype: str
        """
        page = pywikibot.Page(pywikibot.Link(source))
        gen = iter(self.site.logevents(logtype='move', page=page, total=1))
        try:
            lastmove = next(gen)
        except StopIteration:
            pass
        else:
            return lastmove.target_title

    def run(self):
        """Run the bot."""
        if self.init:
            oldlist = set()
        else:
            oldlist = self.readfile()
        pywikibot.output(u'Reading ignoring lists...')
        ignorePage = pywikibot.Page(self.site, opt_out)
        self.ignoreUser.clear()
        for page in ignorePage.linkedPages():
            if page.namespace() in (2, 3):
                self.ignoreUser.add(page.title(withNamespace=False,
                                               withSection=False).split('/')[0])
        ignorePage = pywikibot.Page(self.site,
                                    u'Gedenkseite für verstorbene Wikipedianer',
                                    ns=self.site.ns_index('Project'))
        for page in ignorePage.linkedPages():
            if page.namespace() in (2, 3):
                self.ignoreUser.add(page.title(withNamespace=False,
                                               withSection=False).split('/')[0])

        pywikibot.output(u'%d users found to opt-out' % len(self.ignoreUser))
        cat1 = pywikibot.Category(self.site,
                                  'Kategorie:Wikipedia:Löschkandidat')
        cat2 = pywikibot.Category(self.site,
                                  'Kategorie:Wikipedia:Löschkandidat/Vorlagen')
        gen = pagegenerators.CombinedPageGenerator((cat1.articles(),
                                                    cat2.articles()))
        newlist = set((p.title() for p in gen))
        pywikibot.output(u'Check for moved pages...')
        for title in oldlist - newlist:
            try:
                target = self.moved_page(title)
            except KeyError:  # Log enty (move) has no 'move' key
                target = None
            if target:
                oldlist.add(target)
                pywikibot.output('<<< %s was moved to %s' % (title, target))

        pywikibot.output(u'Processing data...')
        writelist = oldlist
        for article in newlist - oldlist:
            if not self.init:
                pywikibot.output(u'\n>>> %s <<< is tagged for deleting'
                                 % article)
                self.treat(article)
                self._treat_counter += 1
            writelist.add(article)
        # all of them are done, delete the old entries
        else:
            writelist = newlist
        self.writefile(writelist)
        self.init = False

    def readfile(self):
        """
        Read page titles from file.

        @return: set of page titles
        @rtype: set
        """
        pywikibot.output(u'\nReading old article list...')
        filename = pywikibot.config.datafilepath("data", 'la.data')
        try:
            laFile = open(filename, 'rb')
            data = pickle.load(laFile)
            laFile.close()
            pywikibot.output(u'%d articles found' % len(data))
        except(IOError, EOFError):
            data = set()
        return data

    def writefile(self, data):
        """
        Write page titles to file.

        @param data: set of page titles
        @type data: set
        """
        if not config.simulate or self.init:
            pywikibot.output(u'Writing %d article names to file'
                             % len(data))
            filename = pywikibot.config.datafilepath("data", 'la.data')
            try:
                laFile = open(filename, 'wb')
                pickle.dump(data, laFile)
                laFile.close()
            except IOError:
                raise

    def treat(self, pagename):
        """
        Process a given page.

        Get the creator of the page and calculate the main authors.

        @param pagename: page title
        @type pagename: str
        """
        page = pywikibot.Page(pywikibot.Link(pagename))
        if not page.exists():
            return
        cnt = Counter()
        # read the oldest_revision with content
        old_rev = next(page.revisions(total=1, reverse=True, content=True))

        # If the oldest version is a redirect, don't asume him as creator.
        # Maybe the page was just moved.
        # In case of copyright violence, the text might be deleted. Don't
        # inform the creator in that case.
        if not (old_rev.text is None or
                page.site.redirectRegex().search(old_rev.text)):
            creator = old_rev.user
        else:
            creator = None

        # You may not inform the latest editor:
        # either he tagged the deletion request or he saw it
        latest = next(page.revisions(total=1)).user

        # evtl. anonyme/unregistrierte von Zählung ausnehmen
        for rev in page.revisions():
            if rev.minor:
                cnt[rev.user] += 0.2
            else:
                cnt[rev.user] += 1

        s = sum(cnt.values())
        s2 = sum(i ** 2 for i in cnt.values())
        n = float(len(cnt))
        x_ = s / n
        # avg + stdabw
        # faktor von 1 auf 1,5 erhöht für bessere Trennschärfe
        # (siehe Bem. von Gestumblindi)
        limit = max(5, (s2 / n - x_ ** 2) ** 0.5 * 1.5 + x_)
        # main, main_cnt = cnt.most_common(1)[0]

        # inform creator
        if creator and creator != latest and creator not in self.ignoreUser:
            user = pywikibot.User(self.site, creator)
            if user.isRegistered() and not (user.isBlocked() or
                                            'bot' in user.groups()):
                pywikibot.output(u'>>> Creator is ' + creator)
                self.inform(user, page=page.title(), action=u'angelegte')

        # inform main authors
        for main, main_cnt in cnt.most_common(7):
            if main_cnt < limit:
                break
            if main != latest and main != creator and \
               main not in self.ignoreUser:
                user = pywikibot.User(self.site, main)
                if user.isRegistered() and not (user.isBlocked() or
                                                'bot' in user.groups()):
                    pywikibot.output(u'>>> Main author %s with %d Edits'
                                     % (main, main_cnt))
                    self.inform(user, page=page.title(),
                                action=u'stark überarbeitete')

    def inform(self, user, **param):
        """
        Inform user about deletion request.

        @param user: user to be informed
        @type user: pywikibot.User
        @keyword page: page title
        @type page: str
        @keyword action: action done by editor
        @type action: str
        """
        talk = user.getUserTalkPage()
        while talk.isRedirectPage():
            talk = talk.getRedirectTarget()
            if talk == user.getUserTalkPage():
                pywikibot.output(u'WARNING: %s forms a redirect loop. Skipping'
                                 % talk)
                return
        if not talk.isTalkPage():
            pywikibot.output(u'WARNING: %s is not a talk page. Skipping' % talk)
            return
        if talk.exists():
            text = talk.text + u'\n\n'
            if textlib.does_text_contain_section(text,
                                                 u'[[%(page)s]]' % param):
                pywikibot.output(u'NOTE: user %s was already informed'
                                 % user.name())
                return
        else:
            text = u''
        param['user'] = user.name()
        text += msg % param
        if not self.userPut(talk, talk.text, text, minor=False,
                            summary=self.summary % param,
                            ignore_save_related_errors=True,
                            ignore_server_errors=True):
            pywikibot.output(u'WARNING: Page %s not saved.'
                             % talk.title(asLink=True))


def main():
    options = {}
    for arg in pywikibot.handle_args():
        options[arg[1:]] = True

    bot = AFDNoticeBot(**options)
    while True:
        bot.run()
        pywikibot.output('Waiting 300 seconds...\n')
        pywikibot.stopme()
        try:
            time.sleep(300)
        except KeyboardInterrupt:
            bot.exit()
            break

if __name__ == "__main__":
    main()
