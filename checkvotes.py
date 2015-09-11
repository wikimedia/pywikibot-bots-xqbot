#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Script to verify the eligibility for votes on de-wiki.

The following parameters are supported:

&params;

-dry              If given, doesn't do any real changes, but only shows
                  what would have been changed.

-admin            Check admin votings

-voting           Check community votings

-sg               Check arbcom election
"""
from __future__ import unicode_literals

__version__ = '$Id: b7d0f7af1cfce7db63fe73ddf71d24191b41d14a $'
#

import re

import pywikibot
from pywikibot import config, pagegenerators

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {
    '&params;': pagegenerators.parameterHelp
}
SB_TOOL_NEW = 'stimmberechtigung/'
SB_TOOL = '~?stimmberechtigung/(?:index.php)?'
SB_TOOL1 = '~stimmberechtigung/index.php'
SB_TOOL2 = 'stimmberechtigung/index.php'
SB_TOOL3 = 'stimmberechtigung/'


def VotingPageGenerator():
    site = pywikibot.Site()
    page = pywikibot.Page(site, u'Vorlage:Beteiligen')
    text = page.get()
    FOLDER = 'Wikipedia:Meinungsbild'
    R = re.compile(r'\[\[%s(er)*/(.+?)\|' % FOLDER)
    for pre, pagename in R.findall(text):
        yield pywikibot.Page(site, '%s%s/%s' % (FOLDER, pre, pagename))


def BlockUserPageGenerator():
    site = pywikibot.Site()
    page = pywikibot.Page(site, 'Vorlage:Beteiligen')
    text = page.get()
    FOLDER = 'Wikipedia:Benutzersperrung/'
    R = re.compile(r'\[\[%s(.+?)\|' % FOLDER)
    for pagename in R.findall(text):
        yield pywikibot.Page(site, FOLDER + pagename)


def AdminPageGenerator():
    global votepage
    site = pywikibot.Site()
    page = pywikibot.Page(site, 'Wikipedia:Kandidaturen')
    text = page.get()
    FOLDER = 'Wikipedia:Adminkandidaturen/'
    R = re.compile(ur'\{\{%s(.+?)[\||\}]' % FOLDER)
    for pagename in R.findall(text):
        if pagename.lower() != 'intro':
            if not votepage or votepage == pagename:
                yield pywikibot.Page(site, FOLDER + pagename)


def CratsPageGenerator():
    site = pywikibot.Site()
    page = pywikibot.Page(site, 'Wikipedia:Kandidaturen')
    text = page.get()
    FOLDER = 'Wikipedia:Bürokratenkandidaturen/'
    R = re.compile(ur'\{\{%s(.+?)[\||\}]' % FOLDER)
    for pagename in R.findall(text):
        if pagename.lower() != 'intro':
            if not votepage or votepage == pagename:
                yield pywikibot.Page(site, FOLDER + pagename)


def OversightPageGenerator():
    FOLDER = 'Wikipedia:Oversightkandidaturen'
    site = pywikibot.Site()
    page = pywikibot.Page(site, FOLDER)
    text = page.get()
    R = re.compile(r'\[\[(?:%s)?/([^/]+?)(?:/|\|[^/]+?)\]\]' % FOLDER)
    for pagename in R.findall(text):
        if pagename.lower() not in ('intro', 'archiv'):
            yield pywikibot.Page(site, '%s/%s' % (FOLDER, pagename))


def CheckuserPageGenerator():
    global url
    site = pywikibot.Site()
    ts = pywikibot.Timestamp.now()
    page = pywikibot.Page(site,
                          'Wikipedia:Checkuser/Wahl/%s_%d'
                          % (ts.strftime("%B"), ts.year))
    text = page.get()
    urlRegex = re.compile(
        r'\[(?:http:)?//tools.wmflabs.org/(%s)\?([^ ]*?) +.*?\]' % SB_TOOL)
    url = urlRegex.findall(text)[1]
    R = re.compile(r'[#\*] *\[\[/(.+?)/(?:\|.+)?\]\]')
    for pagename in R.findall(text):
        yield pywikibot.Page(site, '%s/%s' % (page.title(), pagename))


def WwPageGenerator():
    global votepage
    site = pywikibot.Site()
    page = pywikibot.Page(site, 'Wikipedia:Adminwiederwahl')
    text = page.get()
    R = re.compile(r'\{\{Adminwiederwahl\|(.+?)\}\}')
    for pagename in R.findall(text):
        if votepage == '' or votepage == pagename:
            yield pywikibot.Page(site, '%s/%s' % (page.title(), pagename))


def SgPageGenerator():
    global url, votepage
    site = pywikibot.Site()
    ts = pywikibot.Timestamp.now()
    page = pywikibot.Page(site,
                          'Wikipedia:Schiedsgericht/Wahl/%s %d'
                          % ("Mai" if ts.month == 5 else "November", ts.year))
    text = page.get()
    urlRegex = re.compile(
        r'\[(?:http:)?//tools.wmflabs.org/(%s)\?([^ ]*?) +.*?\]' % SB_TOOL)
    url = urlRegex.findall(text)[1]  # zweites Auftreten nehmen
    # R = re.compile(ur'\* *\[\[Wikipedia:Schiedsgericht/Wahl/Mai 2010/(.+?)\|.+?\]\] \**')
    R = re.compile(ur'[#\*] *\[\[/(.+?)/\]\]')
    for pagename in R.findall(text):
        if votepage == u'' or votepage == pagename:
            yield pywikibot.Page(site, u'%s/%s' % (page.title(), pagename))


def getDateString(page, template=False):
    global url
    if template:
        templates = page.templatesWithParams()
        for tmpl in templates:
            if tmpl[0] == 'Meinungsbild-Box' or tmpl[0] == 'BSV-Box':
                d = {}
                for x in tmpl[1]:
                    s = x.split('=')
                    d[s[0]] = s[1].strip()
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
                s = 'day=%(tag1)s&mon=%(monat1)s&year=%(jahr1)s&hour=%(stunde)s&min=%(minute)s' % d
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
            urlRegex = re.compile(
                r'\[(?:https\:)?//tools\.wmflabs\.org/(%s)\?(.+?) .+?\]'
                % SB_TOOL)
            result = urlRegex.findall(text)[0]
        return result


class CheckBot(object):
    # Edit summary message that should be used.
    msg = {
        'de': 'Bot: Stimmberechtigung geprüft',
        'en': 'Robot: Votings checked',
    }

    def __init__(self, generator, template, dry, always, blockinfo):
        """
        Constructor. Parameters:
            * generator - The page generator that determines on which pages
                          to work on.
            * dry       - If True, doesn't do any real changes, but only shows
                          what would have been changed.
        """
        self.generator = generator
        self.dry = dry
        self.always = always
        self.blockinfo = blockinfo
        self.template = template
        # Set the edit summary message
        self.site = pywikibot.Site()
        self.summary = pywikibot.translate(self.site, self.msg)
        self.url = None
        self.parts = None
        self.info = None

    def run(self):
        # cc ausschalten
        config.cosmetic_changes = False
        for page in self.generator:
            self.parts = None
            self.info = None
            self.treat(page)

    def treat(self, page):
        """Load the given page, does some changes, and save it."""
        text = self.load(page)
        if text is None:
            return
        if not text:
            pywikibot.output('Page %s has no content, skipping.' % page)
            return

        global ww
        if not ww:
            urlPath = getDateString(page, self.template)
            if urlPath is None:
                pywikibot.output('Could not retrieve urlPath for Timestamp')
                return
        #regex = re.compile(ur"^#[^#:]*?\[\[Benutzer:(?P<user>[^/]+?)[\||\]]", re.MULTILINE)
        #regex = re.compile(ur"^#[^#:]*?\[\[(?:[b|B]enutzer|[u|U]ser):(?P<user>[^/]+?)[\||\]].*?(?P<hour>\d\d):(?P<min>\d\d), (?P<day>\d\d?)\. (?P<month>\w+)\.? (?P<year>\d\d\d\d) \(CES?T\)",
##        regex = re.compile(ur"^#[^#:]*?(?:\[http:.+?\])?[^#:]*?(?:<.+?>)?\[\[(?:[bB]enutzer(?:in)?|[uU]ser|BD|Spezial)(?P<talk>[_ ]Diskussion|[_ ]talk)?:(?:Beiträge/)?(?P<user>[^/#]+?)(?:/[^\\\]])?[\||\]].*?(?P<hour>\d\d):(?P<min>\d\d), (?P<day>\d\d?)\. (?P<month>\w+)\.? (?P<year>\d\d\d\d) \(CES?T\)",
##                           re.MULTILINE|re.UNICODE)
        regex = re.compile(r'^#(?!:).*?(?:\[http:.+?\])?[^#:]*?(?:<.+?>)?\[\[(?:[bB]enutzer(?:in)?|[uU]ser|BD|Spezial)(?P<talk>[_ ]Diskussion|[_ ]talk)?:(?:Beiträge/)?(?P<user>[^/#]+?) *(?:/[^\\\]])?[\||\]].*?(?P<hour>\d\d):(?P<min>\d\d), (?P<day>\d\d?)\. (?P<month>\w+)\.? (?P<year>\d\d\d\d) \(CES?T\)',
                           re.MULTILINE | re.UNICODE)
        i = 0
        pywikibot.output('\nCheck votings for %s' % page.title(asLink=True))
        self.summary = pywikibot.translate(self.site, self.msg)
        delimiter = ', entferne'
        userlist = set()
        userpath = {}
        global sg
        # Lösung suchen für:
        # Baird&#39;s Tapir
        # S1 ist umbenannt
        # ✓ : Tool findet da nichts
        # Umbenannte entfernt
        problems = {
            'TotalUseless':  'Tous4821',  # umbenannt aber hat edits
            'Dr. Brahmavihara': 'Brahmavihara',  # umbenannt aber hat edits
            'G. Hampel': 'Rittendorfer',  # umbenannt, wird auf ww nicht gelöscht
            'Fiona Baine': 'Fiona B.',  # umbenannt aber hat edits
        }
        seen = set()
        comment = u''
        last = u''
        pos = text.find('== Abstimmung ==')
        if pos > 0:
            print 'splitting text'
            head = text[:pos]
            text = text[pos:]
        else:
            head = u''
        for sig in regex.findall(text):
            username = sig[1]
            if i == 10:
                pywikibot.output(u'.', newline=False)
                i = 0
            else:
                i += 1
            if username in problems:
                target_username = problems[username]
            else:
                target_username = username
            if username in seen and last != username:
                pywikibot.output('%s already seen on this page' % username)
                continue
            seen.add(username)
            last = username
            loop = True
            user = pywikibot.User(self.site, username)
            if not user.isRegistered():
                continue
            target_user = user
            while not target_user.exists() or not target_user.editCount():
                if target_user.getUserPage().isRedirectPage():
                    target_username = user.getUserPage().getRedirectTarget().title(withNamespace=False)
                    if target_username in seen and last != target_username:
                        pywikibot.output('%s already seen on this page' % target_username)
                        break
                    seen.add(target_username)
                    target_user = pywikibot.User(self.site, target_username)
                else:
                    # must be renamed. ignore it for now
                    break
            else:
                loop = False
            if loop:
                continue  # continue for loop
            userpage = pywikibot.Page(self.site, target_username)
            isBot = False
            if ww:
                import time
                months = {u'Jan': '01',
                          u'Feb': '02',
                          u'Mär': '03',
                          u'Apr': '04',
                          u'Mai': '05',
                          u'Jun': '06',
                          u'Jul': '07',
                          u'Aug': '08',
                          u'Sep': '09',
                          u'Okt': '10',
                          u'Nov': '11',
                          u'Dez': '12'}
                month = months[sig[5]]
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
                ### Problem: was ist 31. August + 6 Monate? 28. Februar oder Anfang März
                #iMonth = int(month)
                #if iMonth > 6:
                #    month = '0'+str(iMonth-6)
                #    dates['year'] = str(int(dates['year']) + 1)
                #else:
                #    month = str(iMonth+6)
                #dates['mon'] = month
                #mwExpired = '%(year)s%(mon)s%(day)s%(hour)s%(min)s' \
                #            % dates
                #print mwExpired
                sigDate = pywikibot.Timestamp.fromtimestampformat(mwTimestamp)
                curDate = pywikibot.Timestamp.now()
                #expDate = pywikibot.Timestamp.fromtimestampformat(mwExpired)
                #delta = curDate-expDate
                #if delta.days > 0:
                #    print username, mwExpired, 'ist seit', delta.days, u'Tagen abgelaufen bei genauer Zählung.'
                #delta = curDate-sigDate
                regUsername = username.replace('(', '\(').replace(')', '\)').replace('$', '\$')
                day = min(curDate.day, 28 if curDate.month in (2, 8) else 30)  # Jan/Feb 1-3 Tage zu spät
                if curDate.month > 6:
                    oldDate = curDate.replace(month=curDate.month - 6,
                                              day=day)
                else:
                    oldDate = curDate.replace(month=curDate.month + 6,
                                              year=curDate.year - 1, day=day)
                if sigDate < oldDate:
                    delta = oldDate - sigDate
                    pywikibot.output('%s %s ist seit %d Tagen abgelaufen.'
                                     % (username, mwTimestamp, delta.days))
                    #print username, mwTimestamp, 'ist seit', delta.days-183, 'Tagen abgelaufen.'
                    ### TODO: 1 Eintrag wird nicht erkannt
                    if text.count('\n#') == 1:
                        #print 1
                        old = text
                        text = pywikibot.replaceExcept(
                            text,
                            r'\r?\n#(?!:).*?(?:\[http:.+?\])?[^#:]*?(?:<.+?>)?\[\[(?:[B|b]enutzer(?:in)?:|[U|u]ser:|BD:|Spezial:Beiträge/)%s *(?:/[^/\]])?[\||\]][^\r\n]*(?:[\r]*\n)?'
                            % regUsername,
                            r'\n', [])
                        if old == text:
                            text = pywikibot.replaceExcept(
                                text,
                                r'\r?\n#(?!:).*?(?:<.+?>)?\[\[(?:[B|b]enutzer(?:in)?[ _]Diskussion:|[U|u]ser[ _]talk:|BD:|Spezial:Beiträge/)%s *(?:/[^/\]])?[\||\]][^\r\n]*(?:[\r]*\n)?' % regUsername,
                                r'\n', [])
                    else:
                        old = text
                        text = pywikibot.replaceExcept(
                            text,
                            r'\r?\n#(?!:).*?(?:\[http:.+?\])?[^#:]*?(?:<.+?>)?\[\[(?:[B|b]enutzer(?:in)?:|[U|u]ser:|BD:|Spezial:Beiträge/)%s(?:/[^/\]])?[\||\]][^\r\n]*?(?:[\r]*\n#[#:]+.*?)*[\r]*\n#([^#:]+?)'
                            % regUsername,
                            r'\n#\1', [])
                        if old == text:
                            text = pywikibot.replaceExcept(
                                text,
                                r'\r?\n#(?!:).*?(?:\[http:.+?\])?[^#:]*?(?:<.+?>)?\[\[(?:[B|b]enutzer(?:in)?[ _]Diskussion|[U|u]ser[ _]talk):%s[\||\]][^\r\n]*?(?:[\r]*\n#[#:]+.*?)*[\r]*\n#([^#:]+?)'
                                % regUsername,
                                r'\n#\1', [])

                        """
                        text = pywikibot.replaceExcept(
                            text,
                            r'\r?\n#([^#:]*?\[\[Benutzer:%s[\||\]][^\r\n]*?)[\r]*\n' % username,
                            r'', [])
                        """
                    comment = ', abgelaufene Stimmen entfernt.'
                    continue  # Eintrag kann gelöscht werden
                path = 'https://tools.wmflabs.org/%s?user=%s&%s' \
                       % (SB_TOOL_NEW, userpage.title(asUrl=True).replace('_', '+'),
                          query)
            else:
                path = 'https://tools.wmflabs.org/%s?user=%s&%s' \
                       % (SB_TOOL_NEW, userpage.title(asUrl=True).replace('_', '+'),
                          urlPath[1].replace(u'user=', ''))
            try:
                data = self.site.getUrl(path, no_hostname=True)
            except KeyboardInterrupt:
                return
            except:
                pywikibot.output('ERROR retrieving %s' % username)
                continue
            if sg:
                R = re.compile(r'>Schiedsgerichtswahl: (.+?)</div>')
            else:
                R = re.compile(r'>Allgemeine Stimmberechtigung <.+?>\((?:alt|neu)\)</a>: (.+?)</div>')
            result = R.findall(data)
            if self.blockinfo:  # write blocking info
                try:
                    if user.isBlocked():
                        self.getInfo(user)
                        if self.parts['duration'] == u'inifinite':
                            pywikibot.output(
                                '\nUser:%(user)s is blocked til/for '
                                '%(duration)s since %(time)s (%(comment)s)'
                                % self.parts)
                        else:
                            pywikibot.output(
                                '\nUser:%(user)s is blocked til/for '
                                '%(duration)s since %(time)s'
                                % self.parts)
                except:
                    pywikibot.output('HTTP-Error 403 with Benutzer:%s.'
                                     % username)
                    raise
            # 'Klar&amp;Frisch' macht Probleme
            try:
                groups = user.groups()
            except pywikibot.PageNotFound:
                pass
            except KeyError:
                print 'KeyError bei Benutzer:', user
            else:
                if groups and 'bot' in groups:
                    isBot = True
                    pywikibot.output('\nUser:%s is a Bot' % username)
            try:
                if 'nicht' in result[0] or config.verbose_output:
                    pywikibot.output('\nBenutzer:%s ist %s'
                                     % (username, result[0]))
            except IndexError:
                pywikibot.output('%s not found' % username)
                print result
                raise
                # continue
            # Ändere Eintrag
            # gesperrte noch prüfen!
            if 'nicht' in result[0] or isBot:
                userlist.add(username)
                userpath[username] = path.strip()
                self.summary += '%s [[Benutzer:%s]]' % (delimiter, username)
                delimiter = ','
                text = pywikibot.replaceExcept(
                    text + u'\n',  # für Ende-Erkennung
                    r'\r?\n#([^#:]*?\[\[Benutzer(?:in)?:%s[\||\]][^\r\n]*?)[\r]*\n'
                    % username,
                    r'\n#:<s>\1</s> <small>%s --~~~~</small>\n' % result[0], [])

        text = head + text
        if self.save(text, page, self.summary + comment):
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
                    title = page.title(withNamespace=False).split('/')[1]
                    if not '== Stimmberechtigung ==' in talk:
                        talk += ('\n\n== Stimmberechtigung ==\n\nDeine '
                                 'Abstimmung bei [[%s|%s]] wurde gestrichen. '
                                 'Du warst [%s nicht stimmberechtigt]. --~~~~'
                                 % (page.title(), title, userpath[username]))
                    else:
                        sectionR = re.compile(
                            r'\r?\n== *Stimmberechtigung *==\r?\n')
                        match = sectionR.search(talk)
                        if match:
                            talk = (talk[:match.end()] +
                                    '\nDeine Abstimmung bei [[%s|%s]] wurde '
                                    'gestrichen. Du warst [%s nicht '
                                    'stimmberechtigt]. --~~~~\n'
                                    % (page.title(), title,
                                       userpath[username]) +
                                    talk[match.end():])
                    self.save(talk, talkpage,
                              '[[WP:Bot]]: Mitteilung zu %s'
                              % page.title(asLink=True),
                              minorEdit=False)

    def getInfo(self, user):
        if not self.info:
            self.info = self.site.logpages(1, mode='block',
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

    def load(self, page):
        """Load the given page, does some changes, and save it."""
        try:
            # Load the page
            text = page.get()
        except pywikibot.NoPage:
            pywikibot.output('\nPage %s does not exist; skipping.'
                             % page.title(asLink=True))
        except pywikibot.IsRedirectPage:
            pywikibot.output('\nPage %s is a redirect; skipping.'
                             % page.title(asLink=True))
        else:
            restrictions = page.getRestrictions() and False  # für prüfung nicht
            if restrictions:
                if 'edit' in restrictions and restrictions['edit']:
                    if 'sysop' in restrictions['edit']:
                        pywikibot.output('\nPage %s is locked; skipping.'
                                         % page.title(asLink=True))
                    else:
                        return text
                else:
                    return text
            else:
                return text

    def save(self, text, page, comment, minorEdit=True, botflag=True):
        # only save if something was changed
        try:
            old = page.get()
        except pywikibot.NoPage:
            old = ''
        if text != old:
            # Show the title of the page we're working on.
            # Highlight the title in purple.
            pywikibot.output('\n\n>>> \03{lightpurple}%s\03{default} <<<'
                             % page.title())
            # show what was changed
            pywikibot.showDiff(old, text)
            pywikibot.output('Comment: %s' % comment)
            if not self.dry:
                if not self.always:
                    choice = pywikibot.inputChoice(
                        u'Do you want to accept these changes?',
                        ['Yes', 'No', 'All', 'Quit'], ['y', 'N', 'a', 'q'], 'N')
                    if choice == 'a':
                        self.always = True
                    elif choice == 'q':
                        import sys
                        sys.exit()
                if self.always or choice == 'y':
                    try:
                        # Save the page
                        page.put(text, comment=comment,
                                 minorEdit=minorEdit, botflag=botflag)
                    except pywikibot.LockedPage:
                        pywikibot.output('Page %s is locked; skipping.'
                                         % page.title(asLink=True))
                    except pywikibot.EditConflict:
                        pywikibot.output(
                            'Skipping %s because of edit conflict'
                            % (page.title()))
                    except pywikibot.SpamfilterError, error:
                        pywikibot.output(
                            'Cannot change %s because of spam blacklist entry %s'
                            % (page.title(), error.url))
                    else:
                        return True


def main():
    # This factory is responsible for processing command line arguments
    # that are also used by other scripts and that determine on which pages
    # to work on.
    genFactory = pagegenerators.GeneratorFactory()
    # The generator gives the pages that should be worked upon.
    gen = None
    # This temporary array is used to read the page title if one single
    # page to work on is specified by the arguments.
    pageTitleParts = []
    # If dry is True, doesn't do any real changes, but only show
    # what would have been changed.
    dry = False
    always = False
    blockinfo = False
    template = False  # fetch date from template
    global url, sg, ww, votepage
    url = None
    sg = False
    ww = False
    votepage = u''

    # Parse command line arguments
    for arg in pywikibot.handleArgs():
        if arg == "-dry":
            dry = True
        elif arg == "-always":
            always = True
        elif arg == "-blockinfo":
            blockinfo = True
        elif arg.startswith("-admin"):
            votepage = arg[7:]
            gen = AdminPageGenerator()
        elif arg.startswith("-crats"):
            votepage = arg[7:]
            gen = CratsPageGenerator()
        elif arg.startswith("-oversight"):
            votepage = arg[11:]
            gen = OversightPageGenerator()
        elif arg.startswith("-os"):
            votepage = arg[4:]
            gen = OversightPageGenerator()
        elif arg.startswith("-cu"):
            votepage = arg[4:]
            gen = CheckuserPageGenerator()
        elif arg.startswith("-voting"):
            votepage = arg[8:]
            gen = VotingPageGenerator()
            template = True
        elif arg.startswith("-sg"):
            votepage = arg[4:]
            gen = SgPageGenerator()
            sg = True
        elif arg.startswith("-ww"):
            votepage = arg[4:]
            gen = WwPageGenerator()
            ww = True
        elif arg.startswith("-blockuser"):
            votepage = arg[4:]
            gen = BlockUserPageGenerator()
            template = True
        else:
            # check if a standard argument like
            # -start:XYZ or -ref:Asdf was given.
            if not genFactory.handleArg(arg):
                pageTitleParts.append(arg)

    if pageTitleParts != []:
        # We will only work on a single page.
        pageTitle = ' '.join(pageTitleParts)
        page = pywikibot.Page(pywikibot.Site(), pageTitle)
        template = u'Meinungsbild' in pageTitle or \
                   'Benutzersperrung' in pageTitle
        gen = iter([page])

    if not gen:
        gen = genFactory.getCombinedGenerator()
    if gen:
        # The preloading generator is responsible for downloading multiple
        # pages from the wiki simultaneously.
        gen = pagegenerators.PreloadingGenerator(gen)
        bot = CheckBot(gen, template, dry, always, blockinfo)
        bot.run()
    else:
        pywikibot.showHelp()

if __name__ == "__main__":
    main()
