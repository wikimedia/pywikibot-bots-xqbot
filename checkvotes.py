#!/usr/bin/python
"""Script to verify the eligibility for votes on de-wiki.

The following parameters are supported:

&params;

-admin            Check admin votings

-voting           Check community votings

-sg               Check arbcom election
"""
#
# (C) xqt, 2010-2024
#
# Distributed under the terms of the MIT license.
#
from __future__ import annotations

import re

from contextlib import suppress

import pywikibot
from pywikibot import config, i18n, pagegenerators
from pywikibot.bot import ExistingPageBot, SingleSiteBot
from pywikibot.comms import http
from pywikibot.exceptions import Error
from pywikibot.textlib import replaceExcept

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {  # noqa: N816
    '&params;': pagegenerators.parameterHelp
}
DOMAIN = 'https://stimmberechtigung.toolforge.org'
SB_TOOL_NEW = ''
SB_TOOL = '~?stimmberechtigung(?:/|/index.php)?'


def VotingPageGenerator():
    site = pywikibot.Site()
    page = pywikibot.Page(site, 'Vorlage:Beteiligen')
    text = page.get()
    folder = 'Wikipedia:Meinungsbild'
    R = re.compile(r'\[\[%s(er)*/(.+?)\|' % folder)
    for pre, pagename in R.findall(text):
        yield pywikibot.Page(site, f'{folder}{pre}/{pagename}')


def BlockUserPageGenerator():
    site = pywikibot.Site()
    page = pywikibot.Page(site, 'Vorlage:Beteiligen')
    text = page.get()
    folder = 'Wikipedia:Benutzersperrung/'
    R = re.compile(rf'\[\[{folder}(.+?)\|')
    for pagename in R.findall(text):
        yield pywikibot.Page(site, folder + pagename)


def AdminPageGenerator():
    global votepage
    site = pywikibot.Site()
    page = pywikibot.Page(site, 'Wikipedia:Kandidaturen')
    text = page.get()
    folder = 'Wikipedia:Adminkandidaturen/'
    R = re.compile(r'\{\{:?%s(.+?)[\||\}]' % folder)
    for pagename in R.findall(text):
        if pagename.lower() != 'intro':
            if not votepage or votepage == pagename:
                yield pywikibot.Page(site, folder + pagename)


def CratsPageGenerator():
    site = pywikibot.Site()
    page = pywikibot.Page(site, 'Wikipedia:Kandidaturen')
    text = page.get()
    folder = 'Wikipedia:Bürokratenkandidaturen/'
    R = re.compile(r'\{\{%s(.+?)[\||\}]' % folder)
    for pagename in R.findall(text):
        if pagename.lower() != 'intro':
            if not votepage or votepage == pagename:
                yield pywikibot.Page(site, folder + pagename)


def OversightPageGenerator():
    folder = 'Wikipedia:Oversightkandidaturen'
    site = pywikibot.Site()
    page = pywikibot.Page(site, folder)
    text = page.get()
    R = re.compile(rf'\[\[(?:{folder})?/([^/]+?)(?:/|\|[^/]+?)\]\]')
    for pagename in R.findall(text):
        if pagename.lower() not in ('intro', 'archiv'):
            yield pywikibot.Page(site, f'{folder}/{pagename}')


def CheckuserPageGenerator():
    global url
    site = pywikibot.Site()
    ts = pywikibot.Timestamp.now()
    page = pywikibot.Page(
        site, f'Wikipedia:Checkuser/Wahl/{ts.strftime("%B")}_{ts.year}')
    text = page.get()
    urlRegex = re.compile(
        rf'\[(?:http:)?//tools.wmflabs.org/({SB_TOOL})\?([^ ]*?) +.*?\]')
    url = urlRegex.findall(text)[1]
    R = re.compile(r'[#\*] *(?:Kandidatur +)?\[\[/(.+?)/(?:\|.+)?\]\]')
    for pagename in R.findall(text):
        yield pywikibot.Page(site, f'{page.title()}/{pagename}')


def WwPageGenerator(admin=''):
    global votepage
    site = pywikibot.Site()
    page = pywikibot.Page(site, 'Wikipedia:Adminwiederwahl')
    R = re.compile(r'\{\{(?:WP:)?Adminwiederwahl(?:/\*)?\|(.+?)\}\}')
    if admin:
        if '/' not in admin:  # subpage name is given
            admin = f'{page.title()}/{admin}'
        yield pywikibot.Page(site, admin)
    text = page.get()
    for pagename in R.findall(text):
        if votepage == '' or votepage == pagename:
            yield pywikibot.Page(site, f'{page.title()}/{pagename}')


def SgPageGenerator():
    """Generator for arbcom election."""
    global url, votepage
    site = pywikibot.Site()
    ts = pywikibot.Timestamp.now()
    if ts.month not in (5, 11):
        return
    page = pywikibot.Page(site,
                          f'Wikipedia:Schiedsgericht/Wahl/%s {ts.year}'
                          % ('Mai' if ts.month == 5 else 'November'))
    text = page.get()
    urlRegex = re.compile(
        rf'\[(?:http:)?//tools.wmflabs.org/({SB_TOOL})\?([^ ]*?) +.*?\]')
    url = urlRegex.findall(text)[1]  # zweites Auftreten nehmen
    R = re.compile(r'[#\*] *\[\[/(.+?)/\]\]')
    for pagename in R.findall(text):
        if votepage == '' or votepage == pagename:
            yield pywikibot.Page(site, f'{page.title()}/{pagename}')


def getDateString(page, template=False):
    global url
    if template:
        templates = page.templatesWithParams()
        for tmpl in templates:
            title = tmpl[0].title(with_ns=False)
            if title == 'Meinungsbild-Box' or title == 'BSV-Box':
                d = {}
                for x in tmpl[1]:
                    if '=' not in x:
                        continue
                    s = x.split('=')
                    d[s[0]] = s[1].strip() or '0'
                if 'jahr' in d:
                    d['jahr1'] = d['jahr']
                if 'monat' in d:
                    d['monat1'] = d['monat']
                if 'tag' in d:
                    d['tag1'] = d['tag']
                if 'stunde1' in d:
                    d['stunde'] = d['stunde1']
                if 'minute1' in d:
                    d['minute'] = d['minute1']
                s = ('day=%(tag1)s&mon=%(monat1)s&year=%(jahr1)s'
                     '&hour=%(stunde)s&min=%(minute)s' % d)
                return (SB_TOOL, s)
        return
    elif url:
        return url
    else:
        text = page.get()
        urlRegex = re.compile(
            r'\{\{(?:fullurl|vollständige_url):tool(lab)?s:(%s)\|(.+?)\}\}'
            % SB_TOOL)
        try:
            result = urlRegex.findall(text)[0]
        except IndexError:
            try:
                urlRegex = re.compile(
                    rf'\[(?:https\:)?//tools\.wmflabs\.org/({SB_TOOL})\?(.+?) .+?\]')
                result = urlRegex.findall(text)[0]
            except IndexError:
                urlRegex = re.compile(
                    r'\[(?:https\://)?stimmberechtigung\.toolforge\.org/\?(.+?) .+?\]')
                result = urlRegex.findall(text)[0]
        return result


class CheckBot(ExistingPageBot, SingleSiteBot):

    """CheckBot to check votings."""

    use_redirects = False
    ignore_server_errors = True
    ignore_save_related_errors = True

    # Edit summary message that should be used.
    msg = {
        'de': 'Bot: Stimmberechtigung geprüft',
        'en': 'Robot: Votings checked',
    }

    def __init__(self, template, blockinfo, **kwargs):
        """
        Initializer.

        Parameters:
            * generator - The page generator that determines on which pages
                          to work on.
        """
        super().__init__(**kwargs)
        self.blockinfo = blockinfo
        self.template = template
        # Set the edit summary message
        self.summary = i18n.translate(self.site, self.msg)
        self.url = None
        self.parts = None
        self.info = None
        config.cosmetic_changes = False

    def setup(self):
        """Setup bot before threading pages."""
        self.months = {}
        for i, (name, abbr) in enumerate(self.site.months_names, start=1):
            number = f'{i:02}'
            self.months[name] = number
            self.months[abbr] = number

    def treat_page(self):
        """Treat the current page."""
        page = self.current_page
        self.parts = None
        self.info = None
        text = page.text

        if not text:
            pywikibot.info(f'Page {page} has no content, skipping.')
            return

        global ww
        if not ww:
            urlPath = getDateString(page, self.template)
            if urlPath is None:
                pywikibot.info('Could not retrieve urlPath for Timestamp')
                return
        # regex = re.compile(ur"^#[^#:]*?\[\[Benutzer:(?P<user>[^/]+?)[\||\]]", re.MULTILINE)
        # regex = re.compile(ur"^#[^#:]*?\[\[(?:[b|B]enutzer|[u|U]ser):(?P<user>[^/]+?)[\||\]].*?(?P<hour>\d\d):(?P<min>\d\d), (?P<day>\d\d?)\. (?P<month>\w+)\.? (?P<year>\d\d\d\d) \(CES?T\)",
##        regex = re.compile(
##            r"^#[^#:]*?(?:\[http:.+?\])?[^#:]*?(?:<.+?>)?\[\[(?:[bB]enutzer(?:in)?|[uU]ser|BD|Spezial)(?P<talk>[_ ]Diskussion|[_ ]talk)?:(?:Beiträge/)?(?P<user>[^/#]+?)(?:/[^\\\]])?[\||\]].*?(?P<hour>\d\d):(?P<min>\d\d), (?P<day>\d\d?)\. (?P<month>\w+)\.? (?P<year>\d\d\d\d) \(CES?T\)",
##            re.MULTILINE|re.UNICODE)
        regex = re.compile(
            r'^#(?!:).*?(?:\[http:.+?\])?[^#:]*?(?:<.+?>)?\[\[(?:[bB]enutzer(?:in)?|[uU]ser|BD|Spezial)(?P<talk>[_ ]Diskussion|[_ ]talk)?:(?:Beiträge/)?(?P<user>[^/#]+?) *(?:/[^\\\]])?[\||\]].*?(?P<hour>\d\d):(?P<min>\d\d), (?P<day>\d\d?)\. (?P<month>\w+\.?) (?P<year>\d\d\d\d) \(CES?T\)',
            re.MULTILINE | re.UNICODE)
        i = 0
        self.summary = i18n.translate(self.site, self.msg)
        delimiter = ', entferne'
        userlist = set()
        userpath = {}
        global sg
        # Lösung suchen für:
        # Baird&#39;s Tapir
        # S1 ist umbenannt
        # ✓ : Tool findet da nichts

        # umbenannt aber hat edits
        problems = {
            'TotalUseless': 'Tous4821',
            'Dr. Brahmavihara': 'Brahmavihara',
            'G. Hampel': 'Rittendorfer',
            'Fiona Baine': 'Fiona B.',
            'Micha L. Rieser': 'Micha',
            'Serten': 'Poletarion',
            'DrPsychJan': 'Sanisso',
        }
        seen = set()
        comment = ''
        pos = text.find('== Abstimmung ==')
        if pos > 0:
            pywikibot.info('splitting text')
            head = text[:pos]
            text = text[pos:]
        else:
            head = ''
        for sig in regex.findall(text):
            username = sig[1]
            if i == 10:
                pywikibot.info('.', newline=False)
                i = 0
            else:
                i += 1
            if username in problems:
                username = problems[username]
            else:
                username = username.replace('&nbsp;', ' ')  # Scherzkekse
            if username in seen:
                pywikibot.info(f'{username} already seen on this page')
                continue
            seen.add(username)
            user = pywikibot.User(self.site, username)
            loop = True
            while user.getUserPage().isRedirectPage():
                username = user.getUserPage().getRedirectTarget().title(
                    with_ns=False)
                # target is talk page
                if username == user.title(with_ns=False):
                    loop = False
                    break
                if username in seen:
                    pywikibot.info(f'{username} already seen on this page')
                    break
                seen.add(username)
                user = pywikibot.User(self.site, username)
            else:
                loop = False

            if loop:
                raise Error(f'Redirect loop for {user} found')
            if not user.isRegistered():
                raise Error(f'User {user} is not registered')
            if not user.editCount():
                raise Error(f'User {user} has no edits')

            userpage = pywikibot.Page(self.site, username)

            if ww:
                month = self.months[sig[5]]
                dates = {'hour': sig[2],
                         'min': sig[3],
                         'day': sig[4],
                         'mon': month,
                         'year': sig[6]}
                if len(dates['day']) == 1:
                    dates['day'] = '0' + dates['day']
                query = 'day=%(day)s&mon=%(mon)s&year=%(year)s&hour=%(hour)s&min=%(min)s' \
                        % dates
                mwTimestamp = '%(year)s%(mon)s%(day)s%(hour)s%(min)s' \
                              % dates
                # ## Problem: was ist 31. August + 6 Monate? 28. Februar oder Anfang März
                # iMonth = int(month)
                # if iMonth > 6:
                #     month = '0'+str(iMonth-6)
                #     dates['year'] = str(int(dates['year']) + 1)
                # else:
                #     month = str(iMonth+6)
                # dates['mon'] = month
                # mwExpired = '%(year)s%(mon)s%(day)s%(hour)s%(min)s' \
                #             % dates
                # print mwExpired
                sigDate = pywikibot.Timestamp.fromtimestampformat(
                    mwTimestamp + '00')
                curDate = pywikibot.Timestamp.now()
                # expDate = pywikibot.Timestamp.fromtimestampformat(mwExpired)
                # delta = curDate-expDate
                # if delta.days > 0:
                #     print username, mwExpired, 'ist seit', delta.days, 'Tagen abgelaufen bei genauer Zählung.'
                # delta = curDate-sigDate
                regUsername = re.escape(username)
                day = min(curDate.day, 28 if curDate.month in (2, 8) else 30)  # Jan/Feb 1-3 Tage zu spät
                if curDate.month > 6:
                    oldDate = curDate.replace(month=curDate.month - 6,
                                              day=day)
                else:
                    oldDate = curDate.replace(month=curDate.month + 6,
                                              year=curDate.year - 1, day=day)
                if sigDate < oldDate:
                    delta = oldDate - sigDate
                    pywikibot.info(f'{username} ({mwTimestamp}) ist seit '
                                   f'{delta.days} Tagen abgelaufen.')
                    # TODO: 1 Eintrag wird nicht erkannt
                    old = text
                    if text.count('\n#') == 1:
                        text = re.sub(
                            r'\r?\n#(?!:).*?(?:\[http:.+?\])?[^#:]*?(?:<.+?>)?\[\[(?:[Bb]enutzer(?:in)?:|[U|u]ser:|BD:|Spezial:Beiträge/)%s *(?:/[^/\]])?[\||\]][^\r\n]*(?:[\r]*\n)?'
                            % regUsername,
                            r'\n', text, count=1)
                        if old == text:
                            text = re.sub(
                                r'\r?\n#(?!:).*?(?:<.+?>)?\[\[(?:[Bb]enutzer(?:in)?[ _]Diskussion:|[Uu]ser[ _]talk:|BD:|Spezial:Beiträge/)%s *(?:/[^/\]])?[\||\]][^\r\n]*(?:[\r]*\n)?'
                                % regUsername,
                                r'\n', text, count=1)
                    else:
                        text = re.sub(
                            r'\r?\n#(?!:).*?(?:\[http:.+?\])?[^#:]*?(?:<.+?>)?\[\[(?:[Bb]enutzer(?:in)?:|[Uu]ser:|BD:|Spezial:Beiträge/)%s *(?:/[^/\]])?[\||\]][^\r\n]*(?:\r?\n#[#:]+.*?)*\r?\n#([^#:]+?)'
                            % regUsername,
                            r'\n#\1', text, count=1)
                        if old == text:
                            text = re.sub(
                                r'\r?\n#(?!:).*?(?:\[http:.+?\])?[^#:]*?(?:<.+?>)?\[\[(?:[Bb]enutzer(?:in)?[ _]Diskussion|[Uu]ser[ _]talk):%s *[\||\]][^\r\n]*(?:\r?\n#[#:]+.*?)*(?:\r?\n)+#([^#:]+?)'
                                % regUsername,
                                r'\n#\1', text, count=1)
                    comment = ', abgelaufene Stimmen entfernt.'
                    continue  # Eintrag kann gelöscht werden

                path = '%s/%s?mode=bot&user=%s&%s' \
                       % (DOMAIN,
                          SB_TOOL_NEW,
                          userpage.title(as_url=True).replace('_', '+'),
                          query)
            else:
                path = '%s/%s?mode=bot&user=%s&%s' \
                       % (DOMAIN,
                          SB_TOOL_NEW,
                          userpage.title(as_url=True).replace('_', '+'),
                          urlPath[1].replace('user=', ''))

            # check voting rights
            try:
                data = http.fetch(uri=path)
            except KeyboardInterrupt:
                return
            except Exception:
                pywikibot.info(f'ERROR retrieving {username}')
                pywikibot.exception()
                continue

            rights = {}
            values = {'Ja': True, 'Nein': False}
            for line in data.text.strip().splitlines():
                key, _, value = line.partition(': ')
                key = key.replace('Stimmberechtigung', '').strip()
                key = key.replace('Abstimmung', '').strip()
                rights[key] = values.get(value, value)

            for err in ('Fehler', "Can't connect to the database"):
                if err in rights:
                    raise Error(f'User {username}: {rights[err]}')

            result = rights['Schiedsgericht'] if sg else rights['Allgemeine']
            if result is False or config.verbose_output:
                pywikibot.info(f'\nBenutzer:{username} ist%s stimmberechtigt'
                               % ('' if result else ' nicht'))

            if self.blockinfo:  # write blocking info
                try:
                    if user.isBlocked():
                        self.getInfo(user)
                        if self.parts['duration'] == 'inifinite':
                            pywikibot.info(
                                '\nUser:%(user)s is blocked til/for '
                                '%(duration)s since %(time)s (%(comment)s)'
                                % self.parts)
                        else:
                            pywikibot.info(
                                '\nUser:%(user)s is blocked til/for '
                                '%(duration)s since %(time)s'
                                % self.parts)
                except Exception:
                    pywikibot.exception()
                    pywikibot.info(f'HTTP-Error 403 with Benutzer:{username}.')
                    raise

            # 'Klar&amp;Frisch' macht Probleme
            is_bot = 'bot' in user.groups()
            if is_bot:
                pywikibot.info(f'\nUser:{username} is a Bot')

            # Ändere Eintrag
            # gesperrte noch prüfen!
            if result is False or is_bot:
                userlist.add(username)
                userpath[username] = path.strip().replace('mode=bot&', '')
                self.summary += f'{delimiter} [[Benutzer:{username}]]'
                delimiter = ','
                text = replaceExcept(
                    text + '\n',  # für Ende-Erkennung
                    r'\r?\n#([^#:].*?\[\[Benutzer(?:in)?:%s[\||\]][^\r\n]*?)\r?\n'
                    % username,
                    r'\n#:<s>\1</s> <small>nicht stimmberechtigt --~~~~</small>\n', [])

        text = head + text
        if self.userPut(page, page.text, text,
                        summary=self.summary + comment):
            for username in userlist:
                user = pywikibot.User(self.site, username)
                talkpage = user.getUserTalkPage()
                if talkpage.isRedirectPage():
                    talkpage = talkpage.getRedirectTarget()
                if talkpage.isTalkPage():
                    if not talkpage.exists():
                        talk = ''
                    else:
                        talk = talkpage.get()
                    title = page.title(with_ns=False).split('/')[1]
                    if '== Stimmberechtigung ==' not in talk:
                        talk += ('\n\n== Stimmberechtigung ==\n\nDeine '
                                 'Abstimmung bei [[%s|%s]] wurde gestrichen. '
                                 'Du warst [%s nicht stimmberechtigt]. --~~~~'
                                 % (page.title(), title, userpath[username]))
                    else:
                        sectionR = re.compile(
                            r'\r?\n== *Stimmberechtigung *==\r?\n')
                        match = sectionR.search(talk)
                        if match:
                            talk = (talk[:match.end()]
                                    + '\nDeine Abstimmung bei [[%s|%s]] wurde '
                                      'gestrichen. Du warst [%s nicht '
                                      'stimmberechtigt]. --~~~~\n'
                                    % (page.title(), title,
                                       userpath[username])
                                    + talk[match.end():])
                    self.userPut(talkpage, talkpage.text, talk,
                                 summary='[[WP:Bot]]: Mitteilung zu %s'
                                 % page.title(as_link=True),
                                 minorEdit=False)

    def getInfo(self, user):
        """Get info about a blocked user."""
        if not self.info:
            self.info = self.site.logpages(1, mode='block',  # noqa: B305
                                           title=user.getUserPage().title(),
                                           dump=True).next()
            self.parts = {
                'admin': self.info['user'],
                'user': self.info['title'],
                'usertalk': user.getUserTalkPage().title(),
                'time': self.info['timestamp'],
                'duration': self.info['block']['duration'],
                'comment': self.info['comment'],
            }

    def skip_page(self, page):
        """Check whether the page should be skipped."""
        global ww
        if ww:
            restrictions = page.protection()
            with suppress(KeyError):
                if 'sysop' in restrictions['edit']:
                    pywikibot.info(f'\nPage {page} is locked; skipping.')
                    return True
        return super().skip_page(page)


def main(*args):
    # This factory is responsible for processing command line arguments
    # that are also used by other scripts and that determine on which pages
    # to work on.
    genFactory = pagegenerators.GeneratorFactory()
    # The generator gives the pages that should be worked upon.
    gen = None
    # This temporary array is used to read the page title if one single
    # page to work on is specified by the arguments.
    pageTitleParts = []
    always = False
    blockinfo = False
    template = False  # fetch date from template
    global url, sg, ww, votepage
    url = None
    sg = False
    ww = False
    votepage = ''

    # Parse command line arguments
    local_args = pywikibot.handle_args(args)
    for arg in local_args:
        option, _, value = arg.partition(':')
        votepage = value
        if option == '-always':
            always = True
        elif option == '-blockinfo':
            blockinfo = True
        elif option == '-admin':
            gen = AdminPageGenerator()
        elif option == '-crats':
            gen = CratsPageGenerator()
        elif option == '-oversight':
            gen = OversightPageGenerator()
        elif option == '-os':
            gen = OversightPageGenerator()
        elif option == '-cu':
            gen = CheckuserPageGenerator()
        elif option == '-voting':
            gen = VotingPageGenerator()
            template = True
        elif option == '-sg':
            gen = SgPageGenerator()
            sg = True
        elif option == '-ww':
            gen = WwPageGenerator(value)
            ww = True
        elif option == '-blockuser':
            gen = BlockUserPageGenerator()
            template = True
        else:
            # check if a standard argument like
            # -start:XYZ or -ref:Asdf was given.
            if not genFactory.handle_arg(arg):
                pageTitleParts.append(arg)

    if pageTitleParts:
        # We will only work on a single page.
        pageTitle = ' '.join(pageTitleParts)
        page = pywikibot.Page(pywikibot.Site(), pageTitle)
        template = 'Meinungsbild' in pageTitle or \
                   'Benutzersperrung' in pageTitle
        gen = iter([page])

    if not gen:
        gen = genFactory.getCombinedGenerator()
    if gen:
        # The preloading generator is responsible for downloading multiple
        # pages from the wiki simultaneously.
        gen = pagegenerators.PreloadingGenerator(gen)
        bot = CheckBot(template, blockinfo, always=always, generator=gen)
        bot.run()
    else:
        pywikibot.show_help()


if __name__ == '__main__':
    main()
