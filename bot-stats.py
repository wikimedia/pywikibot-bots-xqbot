#!/usr/bin/python
"""Update bot statistic."""
#
# (C) Euku, 2008-2024
# (C) xqt, 2024
#
from __future__ import annotations

import operator
import re               # Used for regular expressions
import dateutil.parser
from datetime import datetime
from itertools import chain

import pywikibot        # pywikibot framework
from pywikibot.backports import Iterable, removeprefix
from pywikibot.bot import CurrentPageBot, SingleSiteBot
from pywikibot.data import api
from pywikibot import textlib

former_botnames = [
    'ArchivBot', 'LinkFA-Bot', 'RevoBot', 'MerlBot', 'KLBot2', 'Luckas-bot',
    'Sebbot', 'Beitragszahlen', 'CopperBot', 'ZéroBot', 'TXiKiBoT',
    'Thijs!bot', 'MerlIwBot',
]

userdict = {}
userdict['AkaBot'] = '2004-11-30'
userdict['ApeBot'] = '2003-07-30'
userdict['BWBot'] = '2004-08-10'
userdict['Bota47'] = '2005-07-19'
userdict['Botteler'] = '2004-08-23'
userdict['Chlewbot'] = '2005-11-30'
userdict['Chobot'] = '2005-06-18'
userdict['ConBot'] = '2004-10-26'
userdict['FlaBot'] = '2004-11-21'
userdict['GeoBot'] = '2005-07-15'
userdict['Gpvosbot'] = '2005-06-11'
userdict['KocjoBot'] = '2005-10-08'
userdict['LeonardoRob0t'] = '2004-11-30'
userdict['MelancholieBot'] = '2005-09-22'
userdict['PortalBot'] = '2005-11-01'
userdict['PyBot'] = '2003-05-28'
userdict['RKBot'] = '2005-04-10'
userdict['RedBot'] = '2005-01-21'
userdict['Robbot'] = '2003-10-11'
userdict['RobotE'] = '2005-05-20'
userdict['RobotQuistnix'] = '2005-07-17'
userdict['Sk-Bot'] = '2004-10-20'
userdict['SpBot'] = '2005-10-06'
userdict['Tasca.bot'] = '2005-07-30'
userdict['Tsca.bot'] = '2005-07-30'
userdict['YurikBot'] = '2005-07-31'
userdict['Zwobot'] = '2003-12-02'


class BotStatsUpdater(SingleSiteBot, CurrentPageBot):

    """A bot which updates bot statistics."""

    def query_last_edit(self, username):
        """Load user contribs from API."""
        req = api.Request(site=self.site, action='query')
        req['list'] = 'usercontribs'
        req['ucuser'] = username
        req['ucdir'] = 'older'
        req['uclimit'] = 1
        req['rawcontinue'] = ''
        data = req.submit()
        try:
            for x in data['query']['usercontribs']:
                return x['timestamp']  # last edit
        except Exception:
            pywikibot.exception()
        return None

    @property
    def generator(self) -> Iterable:
        """Yield the page to update."""
        yield pywikibot.Page(self.site, 'Benutzer:Euku/Botstatistik')

    def treat_page(self) -> None:
        """Process the bot statistic page."""
        page_header = (
            '{{Benutzer:Euku/B:Navigation}}\n'
            'Aufgeführt sind alle Bots die einen Bot-Flag besitzen. '
            'Stand: ~~~~~<br />'
            'Ein Bot gilt als inaktiv, wenn er in den letzten drei Monaten '
            'keinen Beitrag geleistet hat.\n\n'
            '[//de.wikipedia.org/w/index.php?title=Benutzer:Euku/Botstatistik'
            '&diff=curr&oldid=prev&diffonly=1 Änderungen der letzten Woche]'
        )

        table_header = """
{|class="sortable wikitable"
! #
! Botname
! Beiträge
! Gesamtbearbeitungen
! Letzte Bearbeitung
! Anmeldedatum\n'
"""

        text = page_header + table_header + self.collect_data()
        self.put_current(
            text,
            summary='Bot: Aktualisiere Bot-Statistik',
            show_diff=not self.opt.always
        )

    def collect_data(self) -> str:
        """Collect bots data and create table content."""
        req1 = api.Request(site=self.site, action='query')
        req1['list'] = 'users'
        req1['ususers'] = '|'.join(str(x) for x in former_botnames)
        req1['usprop'] = 'editcount|registration'
        data1 = req1.submit()

        botlist = []
        req2 = api.Request(site=self.site, action='query')
        req2['list'] = 'allusers'
        req2['augroup'] = 'bot'
        req2['aulimit'] = 'max'
        req2['auprop'] = 'editcount|registration'
        data2 = req2.submit()

        for x in chain(data1['query']['users'], data2['query']['allusers']):
            p1 = re.compile(r'(?P<date>\d\d\d\d\-\d\d\-\d\d).+')
            matches1 = p1.finditer(x['registration'])
            reg = '?'
            for match1 in matches1:
                reg = match1.group('date')
            if reg == '?' or reg == datetime.today().strftime('%Y-%m-%d'):
                if x['name'] in userdict:
                    reg = userdict[x['name']] + '*'
                else:
                    reg = '?'
            botlist.append((textlib.replaceExcept(x['name'], '&amp;', '&', []),
                            x['editcount'], reg))

        botlist = sorted(botlist, key=operator.itemgetter(1), reverse=True)
        pagetext = ''
        counter = 0
        all_edits = 0
        now = datetime.now()
        for bot in botlist:
            counter += 1
            botname, bot_editcounter, bot_creationdate = bot
            all_edits += bot_editcounter
            remark = ''
            last_edit_res = self.query_last_edit(botname)
            if last_edit_res is not None:
                last_edit = dateutil.parser.parse(last_edit_res).replace(tzinfo=None)
                if botname in former_botnames:
                    remark = '(ehemalig)'
                elif (now - last_edit).days > 3 * 30:
                    remark = '(inaktiv)'
                pagetext += '|-\n|%s||[[Benutzer:%s|%s]] %s||[[Spezial:Beiträge/%s|B]]||%s||%s||%s\n' % (
                    counter, botname, botname, remark, botname, bot_editcounter,
                    last_edit.strftime('%Y-%m-%d'), bot_creationdate)
            else:
                if botname in former_botnames:
                    remark = '(ehemalig)'
                pagetext += '|-\n|%s||[[Benutzer:%s|%s]] %s||[[Spezial:Beiträge/%s|B]]||%s||-||%s\n' % (
                    counter, botname, botname, remark, botname, bot_editcounter,
                    bot_creationdate)

        pagetext += '|}\nGesamtbearbeitungen durch diese Bots: %s ([[Benutzer_Diskussion:Euku/Botstatistik#Bots_ohne_einen_Edit_mit_einem_letzten_Edit|eine Schätzung]])<br />\n<nowiki>*</nowiki> = Datum der ersten Bearbeitung<br/>\nehemalig = das Benutzterkonto besitzt kein Botflag mehr' % '{:,}'.format(
            all_edits).replace(',', '.')
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
