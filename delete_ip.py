#!/usr/bin/python
"""This script can be used to delete IP talk pages.

Static IPs and blocked IPs are skipped.

Of course, you will need an admin account on the relevant wiki.

The following command line parameters are supported:

-always        Don't prompt to delete pages, just do it.

-summary:XYZ   Set the summary message text for the edit to XYZ.

-total:X       Only delete this total number of discussion pages

-lastedit:X    Only delete the talk page if the last activity is older
               than this given days, default is 30

-keep:X        Only delete the tlk page if the last activity is older
               than this given days and there is a keep template on talk
               page, default is 90
"""
#
# (C) xqt, 2025
#
# Distributed under the terms of the MIT license.
#
from __future__ import annotations

import re
from contextlib import suppress
from datetime import timedelta
from typing import Any

import pywikibot
from pywikibot.data.api import ListGenerator
from scripts.delete import DeletionRobot

SUMMARY = 'Nicht mehr benötigte Diskussionsseite einer dynamischen IP'


def generator(site, start: str):
    """Generator for all talk pages starting with *start*."""
    return site.allpages(start=start + '.', namespace=3, content=True)


class TalkPageDeleter(DeletionRobot):

    """This robot allows deletion of pages en masse."""

    update_options = {
        # options for DeletionRobot, required here
        'undelete': False,
        'isorphan': 0,
        'orphansonly': [],
        # new options
        'total': 0,
        'lastedit': 30,
        'keep': 90
    }

    @staticmethod
    def global_blocked(user: pywikibot.User) -> bool:
        """Check whether the given user is globally blocked."""
        gen = ListGenerator(listaction='globalblocks',
                            site=pywikibot.Site('meta'),
                            bgip=user.username)
        with suppress(StopIteration):
            next(gen)
            return True

        return False

    @staticmethod
    def abuselog_ts(user) -> pywikibot.Timestamp | None:
        """Return the Timestamp of the newest abuse log entry."""
        gen = ListGenerator(listaction='abuselog',
                            site=user.site,
                            afluser=user.username,
                            aflprop='user|timestamp',
                            afllimit=1)
        result = None
        with suppress(StopIteration):
            result = next(gen)

        if result and result['user'] == user.username:
            return pywikibot.Timestamp.set_timestamp(result['timestamp'])

        return None

    def skip_page(self, page) -> bool:
        """Skip the page under some conditions."""
        if self.opt.total and self.counter['delete'] >= self.opt.total:
            self.generator.close()
        if self.counter['skip'] % 100 == 0:
            pywikibot.info('.', newline=False)

        if re.search(r'\{\{(?:[sS]tatische IP|[fF]este IP|[iI]P-sperrung)',
                     page.text):
            return True

        user = pywikibot.User(page.site, page.title(with_ns=False))
        if not user.isAnonymous():
            return True
        if user.is_blocked() or self.global_blocked(user):
            return True
        if user.getUserPage().exists():
            return True

        keep = re.search(r'\{\{[bB]itte behalten', page.text)
        days = self.opt.keep if keep else self.opt.lastedit

        if user.last_edit is not None:
            *_, ts, _comment = user.last_edit
            if pywikibot.Timestamp.now() - ts < timedelta(days=days):
                return True

        _, rev = next(user.deleted_contributions(total=1), (None, None))
        if rev:
            now = pywikibot.Timestamp.now()
            if now - rev.timestamp < timedelta(days=days):
                return True

        event = None
        with suppress(StopIteration):
            event = next(user.logevents(total=1))
        if event and pywikibot.Timestamp.now() - event.timestamp() < timedelta(
                days=days):
            return True

        ts = self.abuselog_ts(user)
        if ts and pywikibot.Timestamp.now() - ts < timedelta(days=days):
            return True

        return super().skip_page(page)


def main(*args: str) -> None:
    """Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    :param args: command line arguments
    """
    summary = SUMMARY
    start = '1'
    options: dict[str, Any] = {}
    unknown = []

    # read command line parameters
    local_args = pywikibot.handle_args(args)
    mysite = pywikibot.Site()

    for arg in local_args:
        opt, _, value = arg.partition(':')
        if opt == '-always':
            options[opt[1:]] = True
        elif opt in ('-keep', '-lastedit', '-total'):
            options[opt[1:]] = int(value)
        elif opt == '-start':
            start = value
        elif opt == '-summary':
            summary = value or pywikibot.input(
                'Enter a reason for the deletion:')
        else:
            unknown.append(arg)

    if not pywikibot.bot.suggest_help(unknown_parameters=unknown):
        bot = TalkPageDeleter(summary=summary,
                              generator=generator(mysite, start), **options)
        bot.run()


if __name__ == '__main__':
    main()
