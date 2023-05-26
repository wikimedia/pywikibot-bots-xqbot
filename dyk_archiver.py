#!/usr/bin/env python3
"""Skript to archive "Did You Know" teasers on de-wiki.

This is not a complete bot; rather, it is a template from which simple
bots can be made. You can rename it to mybot.py, then edit it in
whatever way you want.

Use global -simulate option for test purposes. No changes to live wiki
will be done.


The following parameter is supported:

-always           The bot won't ask for confirmation when putting a page

Usage:

    pwb [-simulate] dyk_archiver [-always]
"""
#
# (C) xqt, 2023
#
# Distributed under the terms of the MIT license.
#
import re
from datetime import date, timedelta
from enum import IntEnum

import pywikibot
from pywikibot import config, textlib
from pywikibot.bot import ExistingPageBot, QuitKeyboardInterrupt, SingleSiteBot


class DayOfWeek(IntEnum):

    """Iso-Wochentagsnamen."""

    Montag = 1
    Dienstag = 2
    Mittwoch = 3
    Donnerstag = 4
    Freitag = 5
    Samstag = 6
    Sonntag = 7


class DYKArchiverBot(SingleSiteBot, ExistingPageBot,):

    """Did You Know archiver Bot."""

    use_redirects = False  # treats non-redirects only

    def __init__(self, *args, **kwargs):
        """Initializer."""
        super().__init__(*args, **kwargs)
        self.prefix = 'Wikipedia:Hauptseite/Schon gewusst'
        self.targets = {}
        self.summaries = []
        self.template = """{{{{Hauptseite Schon-gewusst-Archivbox
|Datum={date}
|Text={text}
|Bild={image}
}}}}

"""

    @property
    def generator(self):
        """Generate weekday pages."""
        today = date.today()
        delta = timedelta(days=1)
        if config.simulate:  # offset date for tests only
            today += delta
            today += delta
        pages = []

        for _ in range(7):
            name = DayOfWeek(today.isoweekday()).name
            page = pywikibot.Page(self.site, f'{self.prefix}/{name}')
            page._dyk_date = today
            pages.append(page)
            today -= delta

        for page in reversed(pages):
            yield page

    def treat(self, page) -> None:
        """Load weekday page, determine the archive and prepare the entry."""
        today = page._dyk_date
        if today.month not in self.targets:
            target_page = pywikibot.Page(
                self.site,
                f'{self.prefix}/Archiv/{today.year}/{today.month:>02}')
            self.targets[today.month] = target_page

        target_text = self.targets[today.month].text
        month_name = self.site.months_names[today.month - 1][0]
        curr_date = f'{today.day}. {month_name} {today.year}'

        if curr_date in target_text:
            pywikibot.info(curr_date + ' already archived. Skipping')
            return

        self.summaries.append(curr_date)
        text = page.text
        regex = textlib.get_regexes('file', self.site)[0]
        pict = regex.search(text).group()
        pict = pict[:-2] + '|rechts]]'
        regex = re.compile(r'(?:(?<=\n)|\A)\* *(.*?)(?=\n|\Z)')
        elements = regex.findall(text)

        teaser = ('{{Navigationsleiste Hauptseite Schon-gewusst-Archiv|2023}}'
                  '\n\n')
        for index in (False, True):
            teaser += self.template.format(date=curr_date,
                                           text=elements[index],
                                           image=pict if not index else '')

        self.targets[today.month].text = target_text.replace(
            '{{Navigationsleiste Hauptseite Schon-gewusst-Archiv|2023}}\n\n',
            teaser)

    def teardown(self):
        """Save all archive pages. May be one or two."""
        summary = 'Bot: Ergänze Archiv für ' + ', '.join(self.summaries)
        for target in self.targets.values():
            try:
                self.userPut(target, target.latest_revision.text, target.text,
                             summary=summary)
            except QuitKeyboardInterrupt:
                break


def main(*args: str) -> None:
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    :param args: command line arguments
    """
    options = {}
    # Process global arguments to determine desired site
    local_args = pywikibot.handle_args(args)

    # Parse your own command line arguments
    for arg in local_args:
        arg, _, value = arg.partition(':')
        option = arg[1:]
        options[option] = True

    # run the bot
    DYKArchiverBot(**options).run()


if __name__ == '__main__':
    main()
