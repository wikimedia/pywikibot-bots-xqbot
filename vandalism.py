#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@note: Pywikibot framework is needed.

These command line parameters can be used to specify how to work:
...

authors: Euku, xqt
"""
#
# (C) Euku, 2009-2013
# (C) xqt, 2013-2019
#
from __future__ import annotations

from datetime import timedelta
import re
from time import time

import pywikibot
from pywikibot import Timestamp, textlib
from pywikibot.bot import SingleSiteBot
from pywikibot.comms.eventstreams import site_rc_listener
from pywikibot.tools.formatter import color_format

vmHeadlineRegEx = (r'(==\ *?\[*?(?:[Bb]enutzer(?:in)?:\W?|[Uu]ser:|'
                   r'Spezial\:Beiträge\/|Special:Contributions\/)?'
                   r'%s(?:\|[^]]+)?\ *\]*?)\ *?==\ *')
vmHeadlineUserRegEx = (r'(?:==\ *\[+(?:[Bb]enutzer(?:in)?:\W?|[Uu]ser:|'
                       r'Spezial\:Beiträge\/|Special:Contributions\/)'
                       r'(?P<username>[^]\|=]+?)\ *\]+).*==\ *')
vmErlRegEx = r'(?:\(erl\.?\)|\(erledigt\)|\(gesperrt\)|\(in Bearbeitung\))'

VM_PAGES = {
    'wikipedia:de': {
        'VM': ['Wikipedia:Vandalismusmeldung', 'erl.'],
        'KM': ['Wikipedia:Konfliktmeldung', 'in Bearbeitung'],
        'test': ['user:xqt/Test', 'erl.'],
    },
    'wiktionary:de': {
        'VM': ['Wiktionary:Vandalensperrung', 'erl.']
    },
}
# globals
optOutListReceiverName = 'Opt-out: VM-Nachrichtenempfänger'
optOutListAccuserName = 'Opt-out: VM-Steller'
wpOptOutListRegEx = (r'\[\[(?:[uU]ser|[bB]enutzer(?:in)?)\:'
                     r'(?P<username>[^\|\]]+)(?:\|[^\]]+)?\]\]')

vmMessageTemplate = 'Botvorlage: Info zur VM-Meldung'


def isIn(text, regex):
    """Search regex in text."""
    # re.IGNORECASE to enable lowercased IP
    return re.search(regex, text, re.UNICODE | re.IGNORECASE)


def search(text, regex):
    """Find regex in text."""
    m = re.search(regex, text, re.UNICODE)
    return m.groups()[0] if m else ''


def divideIntoSlices(rawText):
    """
    Analyze text.

    Analyze the whole text to get the intro, the headlines and the
    corresponding bodies.
    """
    textLines = rawText.split('\n')

    # flow: intro -> head <-> body
    textPart = 'intro'

    intro = ''
    vmHeads = []
    vmBodies = []
    for line in textLines:
        isHeadline = (line.strip().startswith('==')
                      and line.strip().endswith('=='))
        if isHeadline and textPart == 'intro':
            textPart = 'head'
            vmHeads.append(line + '\n')
            vmBodies.append('')
        elif not isHeadline and textPart == 'intro':
            intro += line + '\n'
        elif isHeadline and textPart == 'head':
            vmHeads.append(line + '\n')
            vmBodies.append('')  # two headlines in sequence
        elif not isHeadline and textPart == 'head':
            textPart = 'body'
            vmBodies[len(vmHeads) - 1] += line + '\n'
        elif isHeadline and textPart == 'body':
            textPart = 'head'
            vmHeads.append(line + '\n')
            vmBodies.append('')
        elif not isHeadline and textPart == 'body':
            vmBodies[len(vmHeads) - 1] += line + '\n'
        else:
            pywikibot.error(
                "textPart: {}, line.startswith('=='): {}, "
                "line.endswith('=='): {}"
                .format(textPart, line.startswith('=='), line.endswith('==')))
    return intro, vmHeads, vmBodies


def getAccuser(rawText):
    """Return a username and a timestamp."""
    sigRegEx = (
        '\[\[(?:[Bb]enutzer(?:in)?(?:[ _]Diskussion)?\:|'
        '[Uu]ser(?:[ _]talk)?\:|Spezial\:Beiträge\/|'
        'Special:Contributions\/)(?P<username>[^|\]]+)\|.*?\]\].{1,30}')
    sigRegEx += ('(?P<hh>[0-9]{2})\:(?P<mm>[0-9]{2}),\ (?P<dd>[0-9]{1,2})\.?\ '
                 '(?P<MM>[a-zA-Zä]{3,10})\.?\ '
                 '(?P<yyyy>[0-9]{4})\ \((?:CE[S]?T|ME[S]?Z|UTC)\)')
    p1 = re.compile(sigRegEx, re.UNICODE)
    # we assume: the first timestamp was made by the accuser
    match1 = p1.search(rawText)
    if match1 is None:
        return '', ''
    username = match1.group('username')
    hh1 = match1.group('hh')
    mm1 = match1.group('mm')
    dd1 = match1.group('dd')
    MM1 = match1.group('MM')
    yy1 = match1.group('yyyy')
    return username, ' '.join((yy1, MM1, dd1, '{}:{}'.format(hh1, mm1)))


class vmEntry(object):

    """An object representing a vandalism thread on project page."""

    # NOTE: This class isn't used yet

    def __init__(self, defendant, accuser, timestamp):
        """Initializer."""
        self.defendant = defendant
        self.accuser = accuser
        self.timestamp = timestamp
        self.involved = {defendant, accuser}


class vmBot(SingleSiteBot):

    """VM Bot Class."""

    total = 50
    optOutMaxAge = 60 * 60 * 6  # 6h
    useredits = 25  # min edits for experienced users

    def __init__(self, **kwargs):
        """Only accept options defined in availableOptions."""
        self.availableOptions.update({
            'force': False,
            'projectpage': 'VM'
        })
        super(vmBot, self).__init__(**kwargs)
        self.forceWrite = self.getOption('force')
        self.optOutListAge = self.optOutMaxAge + 1  # initial
        self.optOutListReceiver = set()
        self.optOutListAccuser = set()
        self.alreadySeenReceiver = []
        self.start = True  # bootmode
        sitename = self.site.sitename
        self.reset_timestamp()
        if sitename == 'wikipedia:de':
            self.prefix = 'Benutzer:Euku/'
        else:
            self.prefix = 'Benutzer:Xqbot/'
        self.vm = self.getOption('projectpage')
        self.vmPageName = VM_PAGES[sitename][self.vm][0]
        self.vmHeadNote = VM_PAGES[sitename][self.vm][1]
        pywikibot.output('Project page is ' + self.vmPageName)

    def reset_timestamp(self):
        """Reset current timestamp."""
        self.nexttimestamp = '20190718012345'

    def optOutUsersToCheck(self, pageName):
        """Read opt-in list."""
        result = set()
        ignorePage = pywikibot.Page(self.site, pageName)
        for page in ignorePage.linkedPages():
            if page.namespace() in (2, 3):
                result.add(page.title(with_ns=False,
                                      with_section=False).split('/')[0])
        return result

    def userIsExperienced(self, username):
        """
        Check whether is this user is experienced.

        user is experienced if edits >= 50

        changed to 25 // 20150309
        """
        try:
            user = pywikibot.User(self.site, username)
        except pywikibot.InvalidTitle:
            pywikibot.exception()
            return False
        except ValueError:
            pywikibot.exception()
            # TODO: convert to a valid User.
            # In this case I found a user talk page
            return False
        return user.editCount() >= self.useredits

    def translate(self, string):
        """Translate expiry time string into german."""
        table = {
            'gmt': 'UTC',
            'mon': 'Montag',
            'sat': 'Samstag',
            'sun': 'Sonntag',
            'second': 'Sekunde',
            'seconds': 'Sekunden',
            'min': 'Min.',
            'minute': 'Minute',
            'minutes': 'Minuten',
            'hour': 'Stunde',
            'hours': 'Stunden',
            'day': 'Tag',
            'days': 'Tage',
            'week': 'Woche',
            'weeks': 'Wochen',
            'month': 'Monat',
            'months': 'Monate',
            'year': 'Jahr',
            'years': 'Jahre',
            'infinite': 'unbeschränkt',
            'indefinite': 'unbestimmte Zeit',
        }
        for pattern in re.findall('([DHIMSWYa-z]+)', string):
            try:
                string = string.replace(pattern, table[pattern.lower()])
            except KeyError:
                pywikibot.error('{} not found for translation in {}.'
                                .format(pattern, string))
        return string

    def calc_blocklength(self, blocked, expiry):
        """Calculate the block length and return a duration string."""
        if not expiry:
            return 'unbekannte Zeit'

        t = {}
        delta = expiry - blocked
        t['days'] = delta.days
        t['minutes'], t['seconds'] = delta.seconds // 60, delta.seconds % 60
        t['hours'], t['minutes'] = t['minutes'] // 60, t['minutes'] % 60
        t['years'], t['days'] = t['days'] // 365, t['days'] % 365
        t['weeks'], t['days'] = t['days'] // 7, t['days'] % 7
        parts = []
        for key in ['years', 'weeks', 'days', 'hours', 'minutes', 'seconds']:
            if not t[key]:
                continue
            translated = (self.translate(key)
                          if t[key] > 1 else self.translate(key[:-1]))
            parts.append('{} {}'.format(t[key], translated))
        return ', '.join(parts)

    def loadBlockedUsers(self):
        """
        Load blocked users.

        return:
        [(blockedusername, byadmin, timestamp, blocklength, reason)]
        """
        newNexttimestamp = None
        newBlockedUsers = []
        for block in self.site.logevents(logtype='block',
                                         end=self.nexttimestamp,
                                         total=self.total):
            if block.action() not in ['block', 'reblock']:
                continue
            try:
                blockedusername = block.page().title(with_ns=False)
            except KeyError:  # hidden user by OS action
                continue
            byadmin = block.user()
            timeBlk = block.timestamp()
            reason = block.comment() or '<keine angegeben>'
            duration = block._params.get('duration', '')
            if duration.endswith('GMT'):  # timestamp - use expiry instead
                blocklength = self.calc_blocklength(timeBlk, block.expiry())
            else:
                blocklength = self.translate(duration)
            restrictions = block._params.get('restrictions')

            # use the latest block only
            if newNexttimestamp is None:
                newNexttimestamp = timeBlk

            el = (blockedusername, byadmin, timeBlk, blocklength, reason,
                  restrictions)
            newBlockedUsers.append(el)

        if newNexttimestamp:
            self.nexttimestamp = (newNexttimestamp + timedelta(
                seconds=1)).totimestampformat()
            pywikibot.output('\nNew timestamp: %s\n' % self.nexttimestamp)
        return newBlockedUsers

    def restrictions_format(self, restrictions):
        """Take restrictions dict and convert it to a string."""
        if not restrictions:
            return ''
        result = 'für '
        where = []
        if 'pages' in restrictions:
            pages = restrictions['pages']
            string = 'die Seite{} [[{}]]'.format(
                'n' if len(pages) > 1 else '',
                ']], [['.join(p['page_title'] for p in pages))
            where.append(string)
        if 'namespaces' in restrictions:
            namespaces = restrictions['namespaces']
            string = '{} {}'.format(
                'die Namensräume' if len(namespaces) > 1 else 'den Namensraum',
                ', '.join(namespaces))
            where.append(string)
        return result + ' und '.join(where)

    def markBlockedusers(self, blockedUsers):
        """
        Write a message to project page.

        blockedUsers is a tuple of
        (blockedusername, byadmin, timestamp, blocklength, reason,
        restrictions)
        """
        if len(blockedUsers) == 0:
            return

        userOnVMpageFound = 0
        editSummary = ''
        oldRawVMText = ''

        try:
            vmPage = pywikibot.Page(pywikibot.Site(), self.vmPageName)
            oldRawVMText = vmPage.text
            rev_id = vmPage.latest_revision_id
        except pywikibot.NoPage:
            pywikibot.output('could not open or write to project page')
            return

        # read the VM page
        intro, vmHeads, vmBodies = divideIntoSlices(oldRawVMText)

        # add info messages
        for el in blockedUsers:
            blockedusername, byadmin, timestamp, blocklength, reason, rest = el
            # escape chars in the username to make the regex working
            regExUserName = re.escape(blockedusername)
            # normalize title
            blocked_user = pywikibot.User(
                self.site, pywikibot.Link(blockedusername).title)

            # check whether user is still blocked.
            # Otherwise the blockedUsers list entry is old
            if not blocked_user.isBlocked():
                continue

            rest_string = self.restrictions_format(rest)
            pywikibot.output(color_format(
                'blocked user: %s blocked by %s,\n'
                'time: %s length: {lightyellow}%s{default},\n'
                'reason: %s' % el[:-1]))
            pywikibot.output(color_format(
                'restrictions: {{lightred}}{}{{default}}\n'.format(
                    rest_string or 'None')))

            # check if user was reported on VM
            for i, header in enumerate(vmHeads):
                if isIn(header,
                        vmHeadlineRegEx
                        % regExUserName) and not isIn(header, vmErlRegEx):
                    userOnVMpageFound += 1
                    param = {'name': blocked_user.title(with_ns=False)}
                    if blocked_user.isAnonymous():
                        editSummary += (
                            ', [[Spezial:Beiträge/%(name)s|%(name)s]]' %
                            param)
                    else:
                        editSummary += (', [[User:%(name)s|%(name)s]]' % param)

                    reasonWithoutPipe = textlib.replaceExcept(
                        reason, '\|', '{{subst:!}}', [])
                    newLine = (
                        '{{subst:Benutzer:Xqbot/VM-erledigt|'
                        'Gemeldeter=%(user)s|Admin=%(admin)s|'
                        'Zeit=%(duration)s|Begründung=%(reason)s|'
                        'subst=subst:|Teilsperre=%(part)s}}\n'
                    ) % {'user': blockedusername,
                         'admin': byadmin,
                         'duration': blocklength,
                         'part': rest_string,
                         'reason': reasonWithoutPipe}

                    # change headline and add a line at the end
                    # ignore some variants from closing
                    if 'Sperrung auf eigenen Wunsch' not in reason:
                        # write back indexed header
                        vmHeads[i] = textlib.replaceExcept(
                            header, vmHeadlineRegEx % regExUserName,
                            '\\1 ({}) =='.format(self.vmHeadNote),
                            ['comment', 'nowiki', 'source'],  # for headline
                            caseInsensitive=True)
                    vmBodies[i] += newLine

        # was something changed?
        if userOnVMpageFound:  # new version of VM
            # we count how many sections are still not cleared
            headlinesWithOpenStatus = 0
            oldestHeadlineWithOpenStatus = ''
            for header in vmHeads:
                # count any user
                if isIn(header,
                        vmHeadlineRegEx % '.+') and not isIn(header,
                                                             vmErlRegEx):
                    headlinesWithOpenStatus += 1
                    if not oldestHeadlineWithOpenStatus:
                        oldestHeadlineWithOpenStatus = textlib.replaceExcept(
                            header, '(?:==\ *|\ *==)', '',
                            ['comment', 'nowiki', 'source'])

            openSections = ''
            if headlinesWithOpenStatus == 1:
                openSections = ('; {} scheint noch offen zu sein'
                                .format(oldestHeadlineWithOpenStatus))
            elif headlinesWithOpenStatus > 1:
                openSections = ('; {} Abschnitte scheinen noch offen zu sein'
                                ', der älteste zu {}'
                                .format(headlinesWithOpenStatus,
                                        oldestHeadlineWithOpenStatus))

            newRawText = intro
            for i, header in enumerate(vmHeads):
                newRawText += header + vmBodies[i]

            # compare them
            pywikibot.showDiff(oldRawVMText, newRawText)
            editSummary = editSummary[2:]  # remove ', ' at the begining
            pywikibot.output('markiere: ' + editSummary)

            # sanity check
            if vmPage.latest_revision.revid != rev_id:
                print('Revision ID changed')
                raise pywikibot.EditConflict
            vmPage.put(newRawText,
                       'Bot: Abschnitt{} erledigt: {}'
                       .format(('', 'e')[bool(userOnVMpageFound - 1)],
                               editSummary + openSections),
                       False, minor=True, force=True)
        else:
            pywikibot.output('auf {} ist nichts zu tun'.format(self.vm))

    def contactDefendants(self, bootmode=False):
        """
        Contact user.

        http://de.pywikibot.org/w/index.php?title=Benutzer_Diskussion:Euku&oldid=85204681#Kann_SpBot_die_auf_VM_gemeldeten_Benutzer_benachrichtigen.3F
        bootmode: mo messages are written on the first run, just
        'alreadySeenReceiver' is filled with the current defendants. Otherwise
        the bot will always write a messge at startup
        """
        vmPage = pywikibot.Page(self.site, self.vmPageName)
        try:
            rawVMText = vmPage.text
        except pywikibot.NoPage:
            pywikibot.output('could not open or write to project page')
            return
        # read the VM page
        intro, vmHeads, vmBodies = divideIntoSlices(rawVMText)
        # print vmHeads
        for i, header in enumerate(vmHeads):
            # there are several thing to check...
            # is this a user account or a article?
            defendant = search(header, vmHeadlineUserRegEx).strip()
            if not defendant:
                continue
            # convert the first letter to upper case
            defendant = defendant[0].upper() + defendant[1:]
            # is this one an IP address?
            if (isIn(header,
                     r'(?:1?\d?\d|2[0-5]\d)\.(?:1?\d?\d|2[0-5]\d)\.'
                     r'(?:1?\d?\d|2[0-5]\d)\.(?:1?\d?\d|2[0-5]\d)')):
                continue
            # already cleared headline?
            if (isIn(header, vmErlRegEx)):
                continue
            # check if this user has opted out
            if defendant in self.optOutListReceiver:
                pywikibot.output('Ignoring opted out defendant '
                                 + defendant)
                continue

            # get timestamp and accuser
            accuser, timestamp = getAccuser(vmBodies[i])
            pywikibot.output('defendant: %(defendant)s, accuser: %(accuser)s, '
                             'time: %(timestamp)s' % locals())  # noqa: H501
            if accuser == '':
                pywikibot.output('Melder nicht gefunden bei {}, weiter...'
                                 .format(defendant))
                continue

            # is this an old section? maybe the user already got a message
            if (defendant, timestamp) in self.alreadySeenReceiver:
                continue

            # check if the accuser has opted-out
            if accuser in self.optOutListAccuser:
                pywikibot.output(
                    accuser
                    + ' will selber benachrichtigen (Opt-out), weiter...')
                self.alreadySeenReceiver.append((defendant, timestamp))
                continue

            # check if the user has enough edits?
            if not self.userIsExperienced(defendant):
                # print defendant, " ist ein n00b... nächster"
                self.alreadySeenReceiver.append((defendant, timestamp))
                continue
            pywikibot.output('Gemeldeten zum Anschreiben gefunden: '
                             + defendant)

            # write a message to the talk page
            if bootmode:
                pywikibot.output(
                    'Überspringe das Anschreiben, weil es der erste Lauf ist.')
                self.alreadySeenReceiver.append((defendant, timestamp))
                continue

            userTalk = pywikibot.Page(pywikibot.Site(),
                                      'User talk:' + defendant)
            try:
                userTalkRawText = userTalk.text
            except pywikibot.NoPage:
                userTalkRawText = ''

            sectionHeadClear = textlib.replaceExcept(header,
                                                     '==+\ *\[?\[?', '', [])
            sectionHeadClear = textlib.replaceExcept(sectionHeadClear,
                                                     '\]\].*', '', []).strip()

            # memo that this user has already been contacted
            self.alreadySeenReceiver.append((defendant, timestamp))
            while len(self.alreadySeenReceiver) > 50:
                # clean up the list
                pywikibot.output('remove %s out of the list of seen Receiver'
                                 % self.alreadySeenReceiver[0][0])
                self.alreadySeenReceiver.remove(self.alreadySeenReceiver[0])

            # is the accuser an IP?
            if (isIn(accuser,
                     r'(?:1?\d?\d|2[0-5]\d)\.(?:1?\d?\d|2[0-5]\d)\.'
                     r'(?:1?\d?\d|2[0-5]\d)\.(?:1?\d?\d|2[0-5]\d)')):
                accuserLink = 'Spezial:Beiträge/%(user)s{{subst:!}}%(user)s' \
                              % {'user': accuser}
            else:
                accuserLink = 'Benutzer:%(user)s{{subst:!}}%(user)s' \
                              % {'user': accuser}
            # save WP talk page
            Seite = '' if self.vm == 'VM' else '|Seite=Konfliktmeldung'
            addText = ('\n{{subst:%s%s|Melder=%s|Abschnitt=%s%s}}'
                       % (self.prefix, vmMessageTemplate, accuserLink,
                          sectionHeadClear, Seite))
            newUserTalkRawText = userTalkRawText + addText
            pywikibot.output('schreibe: ' + addText)
            pywikibot.showDiff(userTalkRawText, newUserTalkRawText)
            userTalk.put(newUserTalkRawText,
                         'Bot: Benachrichtigung zu [[{}:{}#{}]]'
                         .format(self.site.family.name.title(), self.vm,
                                 sectionHeadClear),
                         False, minorEdit=False)

    def read_lists(self):
        """Read opt-out-lists."""
        if self.optOutListAge > self.optOutMaxAge:
            pywikibot.output('Lese Opt-Out-Listen...')
            self.optOutListReceiver = self.optOutUsersToCheck(
                self.prefix + optOutListReceiverName)
            self.optOutListAccuser = self.optOutUsersToCheck(
                self.prefix + optOutListAccuserName)
            pywikibot.output('optOutListReceiver: {}\n'
                             'optOutListAccuser: {}\n'
                             .format(len(self.optOutListReceiver),
                                     len(self.optOutListAccuser)))
            # leere Liste - immer lesen
            if not self.optOutListReceiver:
                self.optOutListAge = self.optOutMaxAge + 1
            else:
                self.optOutListAge = 0

    def run(self):
        """Run the bot."""
        starttime = time()
        rc_listener = site_rc_listener(self.site)
        rc_listener.register_filter(type=('log', 'edit'))
        while True:
            pywikibot.output(Timestamp.now().strftime('>> %H:%M:%S: '))
            self.read_lists()
            try:
                self.markBlockedusers(self.loadBlockedUsers())
                self.contactDefendants(bootmode=self.start)
            except pywikibot.EditConflict:
                pywikibot.output('Edit conflict found, try again.')
                continue  # try again and skip waittime
            except pywikibot.PageNotSaved:
                pywikibot.output('Page not saved, try again.')
                continue  # try again and skip waittime

            # wait for new block entry
            print()
            now = time()
            pywikibot.stopme()
            for i, entry in enumerate(rc_listener):
                if i % 25 == 0:
                    print('\r', ' ' * 50, '\rWaiting for events', end='')
                if entry['type'] == 'log' and \
                   entry['log_type'] == 'block' and \
                   entry['log_action'] in ('block', 'reblock'):
                    pywikibot.output('\nFound a new blocking event '
                                     'by user "%s" for user "%s"'
                                     % (entry['user'], entry['title']))
                    break
                if entry['type'] == 'edit' and \
                   not entry['bot'] and \
                   entry['title'] == self.vmPageName:
                    pywikibot.output('\nFound a new edit by user "%s"'
                                     % entry['user'])
                    break
                if not entry['bot']:
                    print('.', end='', flush=True)
            print('\n')

            self.optOutListAge += time() - now

            # read older entries again after ~4 minutes
            if time() - starttime > 250:
                starttime = time()
                self.reset_timestamp()
            self.start = False
            self.total = 15  # 10 is too low, see 20190226


def main(*args):
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    @param args: command line arguments
    @type args: list of unicode
    """
    # read arguments
    options = {}
    for arg in pywikibot.handle_args(args):
        if arg.startswith('-projectpage:'):
            options[arg[1:12]] = arg[13:]
        else:
            options[arg[1:].lower()] = True

    bot = vmBot(**options)
    bot.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pywikibot.output('Script terminated by KeyboardInterrupt.')
