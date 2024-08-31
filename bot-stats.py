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
from pywikibot.backports import Generator, removeprefix
from pywikibot.bot import CurrentPageBot, SingleSiteBot

former_botnames = {
    'ArchivBot', 'LinkFA-Bot', 'RevoBot', 'MerlBot', 'KLBot2', 'Luckas-bot',
    'Sebbot', 'Beitragszahlen', 'CopperBot', 'ZéroBot', 'TXiKiBoT',
    'Thijs!bot', 'MerlIwBot',
}

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
        pywikibot.info('find former botnames...', newline=False)
        cnt = 0
        for event in self.site.logevents('rights'):
            if event.action() != 'rights':
                continue
            if 'bot' in event.oldgroups and 'bot' not in event.newgroups:
                cnt += 1
                pywikibot.info('.', newline=False)
                yield event.data['title']
            if cnt >= 50:
                break

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
        pywikibot.info('collecting data...')
        botlist = []
        data1 = self.site.allusers(group='bot')
        data2 = self.site.users(self.former_botnames())
        data3 = self.site.users(former_botnames)

        pywikibot.info('\ncreating botlist...')
        seen = set()
        # Use bot users first in the chain.
        # The bot flag can have been granted for former botnames
        for x in chain(data1, data2, data3):
            if x['name'] in seen:
                continue
            seen.add(x['name'])

            try:
                ts = Timestamp.fromISOformat(x['registration'])
                suffix = ''
            except (TypeError, ValueError):
                ts = Timestamp.fromisoformat(userdict[x['name']])
                suffix = '*'

            botlist.append((x['name'].replace('&amp;', '&'),
                            x['editcount'],
                            ts, suffix,
                            x['groups']))

        pywikibot.info('creating wiki table...', newline=False)
        botlist = sorted(botlist, key=operator.itemgetter(1), reverse=True)
        pagetext = ''
        all_edits = 0
        now = Timestamp.now()
        for bot in botlist:
            self.counter['collect'] += 1
            if self.counter['collect'] % 10 == 0:
                pywikibot.info('.', newline=False)
            botname, bot_editcounter, bot_creationdate, suffix, groups = bot
            all_edits += bot_editcounter
            remark = 'aktiv'
            last_edit_res = self.query_last_edit(botname)
            if last_edit_res is None:
                last_edit_str = '-'
            else:
                last_edit = Timestamp.fromISOformat(last_edit_res)
                if (now - last_edit).days > 3 * 30:
                    remark = 'inaktiv'
                last_edit_str = str(last_edit)[:10]
            if 'bot' not in groups:
                remark = 'ehemalig'
            pagetext += (
                f'|-\n|{self.counter["collect"]}|'
                f'|[[Benutzer:{botname}|{botname}]]|'
                f'|{remark}|'
                f'|[[Spezial:Beiträge/{botname}|B]]|'
                f'|{bot_editcounter}|'
                f'|{last_edit_str}|'
                f'|{str(bot_creationdate)[:10]}{suffix}\n'
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
