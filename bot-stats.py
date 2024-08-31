#!/usr/bin/python
"""Update bot statistic.

The following parameters are supported:

-always           The bot won't ask for confirmation when putting a page

-summary:         Set the action summary message for the edit.
"""
#
# (C) Euku, 2008-2024
# (C) xqt, 2024
#
from __future__ import annotations

import operator
from contextlib import suppress
from itertools import chain

import pywikibot  # pywikibot framework
from pywikibot import Timestamp
from pywikibot.backports import Generator, batched, removeprefix
from pywikibot.bot import CurrentPageBot, SingleSiteBot

# notable unflagged bots
unflagged_bots = ['Beitragszahlen']

# unknown creation date; use first edit timestamp instead
userdict = {
    'AkaBot': '2004-11-30',
    'ApeBot': '2003-07-30',
    'BWBot': '2004-08-10',
    'Bota47': '2005-07-19',
    'Botteler': '2004-08-23',
    'Chlewbot': '2005-11-30',
    'Chobot': '2005-06-18',
    'ConBot': '2004-10-26',
    'FlaBot': '2004-11-21',
    'GeoBot': '2005-07-15',
    'Gpvosbot': '2005-06-11',
    'KocjoBot': '2005-10-08',
    'LeonardoRob0t': '2004-11-30',
    'MelancholieBot': '2005-09-22',
    'PortalBot': '2005-11-01',
    'PyBot': '2003-05-28',
    'RKBot': '2005-04-10',
    'RedBot': '2005-01-21',
    'Robbot': '2003-10-11',
    'RobotE': '2005-05-20',
    'RobotQuistnix': '2005-07-17',
    'Sk-Bot': '2004-10-20',
    'SpBot': '2005-10-06',
    'Tasca.bot': '2005-07-30',
    'Tsca.bot': '2005-07-30',
    'YurikBot': '2005-07-31',
    'Zwobot': '2003-12-02',
}


class BotStatsUpdater(SingleSiteBot, CurrentPageBot):

    """A bot which updates bot statistics."""

    update_options = {'summary': 'Bot: Aktualisiere Bot-Statistik'}

    def former_botnames(self) -> Generator[str, None, None]:
        """Collect former botnames.

        .. note:: This method yields account where bot flag was revoked.
           It does not check whether the flag was granted afterwards.
        """
        pywikibot.info('find former bot names...', newline=False)
        for cnt, event in enumerate(self.site.logevents('rights')):
            if event.action() != 'rights':
                continue
            if 'bot' in event.oldgroups and 'bot' not in event.newgroups:
                if cnt % 10 == 0:
                    pywikibot.info('.', newline=False)
                yield event.data['title']

    def query_last_edit(self, username) -> str | None:
        """Load user contribs from API and return timestamp."""
        with suppress(StopIteration):
            return next(self.site.usercontribs(user=username,
                                               total=1))['timestamp']
        return None

    @property
    def generator(self) -> Generator[str, None, None]:
        """Yield the page to update."""
        yield pywikibot.Page(
            self.site,
            'Wikipedia:Liste der Bots nach Anzahl der Bearbeitungen'
        )

    def treat_page(self) -> None:
        """Process the bot statistic page."""
        page_header = (
            'Aufgeführt sind alle Bots die einen Bot-Flag besitzen. '
            'Stand: ~~~~~<br />'
            'Ein Bot gilt als inaktiv, wenn er in den letzten drei Monaten '
            'keinen Beitrag geleistet hat.\n\n'
            '[//de.wikipedia.org/w/index.php?'
            f'title={self.current_page.title(underscore=True)}'
            '&diff=curr&oldid=prev&diffonly=1 Änderungen der letzten Woche]'
        )

        page_footer = (
            '([[Wikipedia_Diskussion:'
            'Liste der Bots nach Anzahl der Bearbeitungen'
            '#Bots_ohne_einen_Edit_mit_einem_letzten_Edit|eine Schätzung]])'
            '<br />\n<nowiki>*</nowiki> = Datum der ersten Bearbeitung<br/>\n'
            'ehemalig = das Benutzterkonto besitzt kein Botflag mehr\n\n'
            '[[Kategorie:Wikipedia:Bots]]'
        )

        table_header = """
{|class="sortable wikitable"
! #
! Botname
! Status
! Beiträge
! Gesamtbearbeitungen
! Letzte Bearbeitung
! Anmeldedatum\n
"""

        text = page_header + table_header + self.collect_data() + page_footer
        self.put_current(
            text,
            summary=self.opt.summary,
            show_diff=not self.opt.always
        )

    def collect_data(self) -> str:
        """Collect bots data and create table content."""
        botlist = []
        allbots = self.site.allusers(group='bot')
        former = batched(self.site.users(self.former_botnames()), 50)
        unflagged = self.site.users(unflagged_bots)

        seen = set()
        # Use bot users first in the chain.
        # The bot flag can have been granted for former botnames
        for x in chain(allbots, *former, unflagged):
            if x['name'] in seen:
                continue
            seen.add(x['name'])

            suffix = ''
            try:
                ts = str(Timestamp.fromISOformat(x['registration']).date())
            except (TypeError, ValueError):
                try:
                    ts = str(Timestamp.fromisoformat(
                        userdict[x['name']]).date())
                except KeyError:
                    ts = '?'
                else:
                    suffix = '*'

            botlist.append((x['name'].replace('&amp;', '&'),
                            x['editcount'],
                            ts, suffix,
                            x['groups']))

        pywikibot.info('\ncreating wiki table...', newline=False)
        botlist = sorted(botlist, key=operator.itemgetter(1), reverse=True)
        pagetext = ''
        all_edits = 0
        now = Timestamp.now()

        for bot in botlist:
            botname, bot_editcounter, bot_creationdate, suffix, groups = bot
            all_edits += bot_editcounter
            remark, color = 'aktiv', 'DBF3EC'
            last_edit_res = self.query_last_edit(botname)

            if last_edit_res is None:
                last_edit_str = '-'
            else:
                last_edit = Timestamp.fromISOformat(last_edit_res)
                if (now - last_edit).days > 3 * 30:
                    remark, color = 'inaktiv', 'FBEEBF'
                last_edit_str = str(last_edit.date())

            if 'bot' not in groups:
                remark, color = 'ehemalig', 'E5C0C0'
                # ignore older bots with no contribs
                if bot_editcounter == 0:
                    continue

            self.counter['collect'] += 1
            if self.counter['collect'] % 10 == 0:
                pywikibot.info('.', newline=False)

            # for colors see https://meta.wikimedia.org/wiki/Brand/colours
            edits = f'{bot_editcounter:,}'.replace(',', '.')
            pagetext += (
                f'|-\n|{self.counter["collect"]}|'
                f'|[[Benutzer:{botname}|{botname}]]|'
                f'| style="background:#{color}" |{remark}|'
                f'|[[Spezial:Beiträge/{botname}|B]]|'
                f'|{edits}|'
                f'|{last_edit_str}|'
                f'|{bot_creationdate}{suffix}\n'
            )

        pywikibot.info()
        edit_sum = f'{all_edits:,}'.replace(',', '.')
        pagetext += f'|}}\nGesamtbearbeitungen durch diese Bots: {edit_sum} '
        return pagetext


def main(*args: str) -> None:
    """Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    :param args: command line arguments
    """
    options = {}

    for arg in pywikibot.handle_args():
        opt, _, value = arg.partition(':')
        if not opt.startswith('-'):
            continue
        options[removeprefix(opt, '-')] = value or True

    bot = BotStatsUpdater(**options)
    bot.run()


if __name__ == '__main__':
    main()
