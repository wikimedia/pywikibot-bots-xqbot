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
# (C) xqt, 2013-2017
#
from __future__ import absolute_import, print_function, unicode_literals

import re
from datetime import timedelta
from time import time

import pywikibot
from pywikibot import Timestamp, textlib
from pywikibot.comms.eventstreams import site_rc_listener
from pywikibot.tools.formatter import color_format

vmHeadlineRegEx = (r"(==\ *?\[*?(?:[Bb]enutzer(?:in)?:\W?|[Uu]ser:|"
                   r"Spezial\:Beiträge\/|Special:Contributions\/)?"
                   r"%s(?:\|[^]]+)?\ *\]*?)\ *?==\ *")
vmHeadlineUserRegEx = (r"(?:==\ *\[+(?:[Bb]enutzer(?:in)?:\W?|[Uu]ser:|"
                       r"Spezial\:Beiträge\/|Special:Contributions\/)"
                       r"(?P<username>[^]\|=]+?)\ *\]+).*==\ *")
vmErlRegEx = r"(?:\(erl\.?\)|\(erledigt\)|\(gesperrt\)|\(in Bearbeitung\))"

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
optOutListReceiverName = "Opt-out: VM-Nachrichtenempfänger"
optOutListAccuserName = "Opt-out: VM-Steller"
wpOptOutListRegEx = (r"\[\[(?:[uU]ser|[bB]enutzer(?:in)?)\:"
                     r"(?P<username>[^\|\]]+)(?:\|[^\]]+)?\]\]")

vmMessageTemplate = "Botvorlage: Info zur VM-Meldung"


def isIn(text, regex):
    """Search regex in text."""
    # re.IGNORECASE to enable lowercased IP
    return re.search(regex, text, re.UNICODE | re.IGNORECASE)


def search(text, regex):
    """Find regex in text."""
    m = re.search(regex, text, re.UNICODE)
    return m.groups()[0] if m else ""


def divideIntoSlices(rawText):
    """
    Analyze text.

    Analyze the whole text to get the intro, the headlines and the
    corresponding bodies.
    """
    textLines = rawText.split("\n")

    # flow: intro -> head <-> body
    textPart = "intro"

    intro = ""
    vmHeads = []
    vmBodies = []
    for line in textLines:
        isHeadline = (line.strip().startswith("==") and
                      line.strip().endswith("=="))
        if isHeadline and textPart == "intro":
            textPart = "head"
            vmHeads.append(line + "\n")
            vmBodies.append("")
        elif not isHeadline and textPart == "intro":
            intro += line + "\n"
        elif isHeadline and textPart == "head":
            vmHeads.append(line + "\n")
            vmBodies.append("")  # two headlines in sequence
        elif not isHeadline and textPart == "head":
            textPart = "body"
            vmBodies[len(vmHeads) - 1] += line + "\n"
        elif isHeadline and textPart == "body":
            textPart = "head"
            vmHeads.append(line + "\n")
            vmBodies.append("")
        elif not isHeadline and textPart == "body":
            vmBodies[len(vmHeads) - 1] += line + "\n"
        else:
            pywikibot.output(
                "ERROR! textPart: %s, line.startswith('=='): %s, "
                "line.endswith('=='): %s"
                % (textPart, line.startswith("=="), line.endswith("==")))
    return intro, vmHeads, vmBodies


def getAccuser(rawText):
    """Return a username and a timestamp."""
    sigRegEx = ("\[\[(?:[Bb]enutzer(?:in)?(?:[ _]Diskussion)?\:|"
                "[Uu]ser(?:[ _]talk)?\:|Spezial\:Beiträge\/|"
                "Special:Contributions\/)(?P<username>[^|\]]+)\|.*?\]\].{1,30}")
    sigRegEx += ("(?P<hh>[0-9]{2})\:(?P<mm>[0-9]{2}),\ (?P<dd>[0-9]{1,2})\.?\ "
                 "(?P<MM>[a-zA-Zä]{3,10})\.?\ "
                 "(?P<yyyy>[0-9]{4})\ \((?:CE[S]?T|ME[S]?Z|UTC)\)")
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
    return username, ' '.join((yy1, MM1, dd1, '{0}:{1}'.format(hh1, mm1)))


class vmEntry(object):

    """An object representing a vandalism thread on project page."""

    # NOTE: This class isn't used yet

    def __init__(self, defendant, accuser, timestamp):
        """Constructor."""
        self.defendant = defendant
        self.accuser = accuser
        self.timestamp = timestamp
        self.involved = set((defendant, accuser))


class vmBot(pywikibot.bot.SingleSiteBot):

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
        self.nexttimestamp = "20160501123456"

    def optOutUsersToCheck(self, pageName):
        """Read opt-in list."""
        result = set()
        ignorePage = pywikibot.Page(self.site, pageName)
        for page in ignorePage.linkedPages():
            if page.namespace() in (2, 3):
                result.add(page.title(withNamespace=False,
                                      withSection=False).split('/')[0])
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
            'indefinite': 'unbestimmt',
        }
        for pattern in re.findall('([DHIMSWYa-z]+)', string):
            try:
                string = string.replace(pattern, table[pattern.lower()])
            except KeyError:
                pywikibot.error(pattern + ' not found for translation.')
        return string

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
                blockedusername = block.page().title(withNamespace=False)
            except KeyError:  # hidden user by OS action
                continue
            byadmin = block.user()
            timeBlk = block.timestamp()
            reason = block.comment() or '<keine angegeben>'
            blocklength = self.translate(block._params.get('duration'))

            # use the latest block only
            if newNexttimestamp is None:
                newNexttimestamp = timeBlk

            el = (blockedusername, byadmin, timeBlk, blocklength, reason)
            newBlockedUsers.append(el)

        if newNexttimestamp:
            self.nexttimestamp = (newNexttimestamp + timedelta(
                seconds=1)).totimestampformat()
            pywikibot.output('\nNew timestamp: %s\n' % self.nexttimestamp)
        return newBlockedUsers

    def markBlockedusers(self, blockedUsers):
        """
        Write a message to project page.

        blockedUsers is an array of
        (blockedusername, byadmin, timestamp, blocklength, reason)
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
            pywikibot.output("could not open or write to project page")
            return

        # read the VM page
        intro, vmHeads, vmBodies = divideIntoSlices(oldRawVMText)

        # add info messages
        for el in blockedUsers:
            blockedusername, byadmin, timestamp, blocklength, reason = el
            # escape chars in the username to make the regex working
            regExUserName = re.escape(blockedusername)
            # normalize title
            blocked_user = pywikibot.User(
                self.site, pywikibot.Link(blockedusername).title)

            # check whether user is still blocked.
            # Otherwise the blockedUsers list entry is old
            if not blocked_user.isBlocked():
                continue

            pywikibot.output(color_format(
                "blocked user: %s blocked by %s,\n"
                "time: %s length: {lightyellow}%s{default},\n"
                "reason: %s\n" % el))

            # check if user was reported on VM
            for i in range(0, len(vmHeads)):
                if isIn(vmHeads[i],
                        vmHeadlineRegEx
                        % regExUserName) and not isIn(vmHeads[i], vmErlRegEx):
                    userOnVMpageFound += 1
                    param = {'name': blocked_user.title(withNamespace=False)}
                    if blocked_user.isAnonymous():
                        editSummary += (
                            ', [[Spezial:Beiträge/%(name)s|%(name)s]]' %
                            param)
                    else:
                        editSummary += (', [[User:%(name)s|%(name)s]]' % param)

                    reasonWithoutPipe = textlib.replaceExcept(reason, "\|",
                                                              "{{subst:!}}",
                                                              [])
                    newLine = (
                        '{{subst:%sVorlage:VM-erl|Gemeldeter=%s|Admin=%s|'
                        'Zeit=%s|Begründung=%s|subst=subst:}}'
                        % (self.prefix, blockedusername, byadmin, blocklength,
                           reasonWithoutPipe))

                    # change headline and add a line at the end
                    # ignore some variants from closing
                    if 'Sperrung auf eigenen Wunsch' not in reason:
                        vmHeads[i] = textlib.replaceExcept(
                            vmHeads[i], vmHeadlineRegEx % regExUserName,
                            "\\1 (%s) ==" % self.vmHeadNote,
                            ['comment', 'nowiki', 'source'],  # for the headline
                            caseInsensitive=True)
                    vmBodies[i] += newLine + "\n"

        # was something changed?
        if userOnVMpageFound:  # new version of VM
            # we count how many sections are still not cleared
            headlinesWithOpenStatus = 0
            oldestHeadlineWithOpenStatus = ""
            for i in range(0, len(vmHeads)):
                # count any user
                if isIn(vmHeads[i],
                        vmHeadlineRegEx % ".+") and not isIn(vmHeads[i],
                                                             vmErlRegEx):
                    headlinesWithOpenStatus += 1
                    if oldestHeadlineWithOpenStatus == "":
                        oldestHeadlineWithOpenStatus = textlib.replaceExcept(
                            vmHeads[i], "(?:==\ *|\ *==)", "",
                            ['comment', 'nowiki', 'source'])

            if oldestHeadlineWithOpenStatus != "":
                oldestHeadlineWithOpenStatus = ", der älteste zu " + \
                                               oldestHeadlineWithOpenStatus

            openSections = ""
            if (headlinesWithOpenStatus == 1):
                openSections = "; 1 Abschnitt scheint noch offen zu sein"
            elif (headlinesWithOpenStatus > 1):
                openSections = ("; %s Abschnitte scheinen noch offen zu sein"
                                % headlinesWithOpenStatus)

            newRawText = intro
            for i in range(0, len(vmHeads)):
                newRawText += vmHeads[i] + vmBodies[i]

            # compare them
            pywikibot.showDiff(oldRawVMText, newRawText)
            editSummary = editSummary[2:]  # remove ", " at the begining
            pywikibot.output("markiere: " + editSummary)

            # sanity check
            if vmPage.latest_revision.revid != rev_id:
                print('Revision ID changed')
                raise pywikibot.EditConflict
            vmPage.put(newRawText,
                       "Bot: Abschnitt%s erledigt: %s"
                       % (('', 'e')[bool(userOnVMpageFound - 1)],
                          editSummary + openSections +
                          oldestHeadlineWithOpenStatus),
                       False, minorEdit=True, force=True)
        else:
            pywikibot.output("auf %s ist nichts zu tun" % self.vm)

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
            pywikibot.output("could not open or write to project page")
            return
        # read the VM page
        intro, vmHeads, vmBodies = divideIntoSlices(rawVMText)
        # print vmHeads
        for i in range(len(vmHeads)):
            # there are several thing to check...
            # is this a user account or a article?
            defendant = search(vmHeads[i], vmHeadlineUserRegEx).strip()
            if (len(defendant) == 0):
                continue
            # convert the first letter to upper case
            defendant = defendant[0].upper() + defendant[1:]
            # is this one an IP address?
            if (isIn(vmHeads[i],
                     r'(?:1?\d?\d|2[0-5]\d)\.(?:1?\d?\d|2[0-5]\d)\.'
                     r'(?:1?\d?\d|2[0-5]\d)\.(?:1?\d?\d|2[0-5]\d)')):
                continue
            # already cleared headline?
            if (isIn(vmHeads[i], vmErlRegEx)):
                continue
            # check if this user has opted out
            if defendant in self.optOutListReceiver:
                pywikibot.output("Ignoring opted out defendant %s"
                                 % defendant)
                continue

            # get timestamp and accuser
            accuser, timestamp = getAccuser(vmBodies[i])
            pywikibot.output("defendant: %(defendant)s, accuser: %(accuser)s, "
                             "time: %(timestamp)s" % locals())
            if accuser == "":
                pywikibot.output("Melder nicht gefunden bei %s, weiter..."
                                 % defendant)
                continue
            # TEST:
            # defendant = "Euku"
            # accuser = "Euku"
            # self.alreadySeenReceiver = [] # hack

            # is this an old section? maybe the user already got a message
            if (defendant, timestamp) in self.alreadySeenReceiver:
                continue

            # check if the accuser has opted-out
            if accuser in self.optOutListAccuser:
                pywikibot.output(
                    "%s will selber benachrichtigen (Opt-out), weiter..."
                    % accuser)
                self.alreadySeenReceiver.append((defendant, timestamp))
                continue

            # check if the user has enough edits?
            if not self.userIsExperienced(defendant):
                # print defendant, " ist ein n00b... nächster"
                self.alreadySeenReceiver.append((defendant, timestamp))
                continue
            pywikibot.output("Gemeldeten zum Anschreiben gefunden: " +
                             defendant)

            # write a message to the talk page
            if bootmode:
                pywikibot.output(
                    "überspringe das Anschreiben, weil es der erste Lauf ist")
                self.alreadySeenReceiver.append((defendant, timestamp))
                continue

            userTalk = pywikibot.Page(pywikibot.Site(),
                                      "User talk:" + defendant)
            try:
                userTalkRawText = userTalk.text
            except pywikibot.NoPage:
                userTalkRawText = ''

            sectionHeadClear = textlib.replaceExcept(vmHeads[i],
                                                     "==+\ *\[?\[?", "", [])
            sectionHeadClear = textlib.replaceExcept(sectionHeadClear,
                                                     "\]\].*", "", []).strip()

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
                accuserLink = "Spezial:Beiträge/" + accuser + "{{subst:!}}" + \
                              accuser
            else:
                accuserLink = "Benutzer:" + accuser + "{{subst:!}}" + accuser
            # save WP talk page
            Seite = "" if self.vm == 'VM' else "|Seite=Konfliktmeldung"
            addText = ("\n{{subst:%s%s|Melder=%s|Abschnitt=%s%s}}"
                       % (self.prefix, vmMessageTemplate, accuserLink,
                          sectionHeadClear, Seite))
            newUserTalkRawText = userTalkRawText + addText
            pywikibot.output("schreibe: " + addText)
            pywikibot.showDiff(userTalkRawText, newUserTalkRawText)
            userTalk.put(newUserTalkRawText,
                         "Bot: Benachrichtigung zu [[%s:%s#%s]]"
                         % (self.site.family.name.title(), self.vm,
                            sectionHeadClear),
                         False, minorEdit=False)

    def read_lists(self):
        """Read opt-out-lists."""
        if self.optOutListAge > self.optOutMaxAge:
            pywikibot.output("Lese Opt-Out-Listen...")
            self.optOutListReceiver = self.optOutUsersToCheck(
                self.prefix + optOutListReceiverName)
            self.optOutListAccuser = self.optOutUsersToCheck(
                self.prefix + optOutListAccuserName)
            pywikibot.output("optOutListReceiver: %d\n"
                             "optOutListAccuser: %d\n"
                             % (len(self.optOutListReceiver),
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
            pywikibot.output(Timestamp.now().strftime(">> %H:%M:%S: "))
            self.read_lists()
            try:
                self.markBlockedusers(self.loadBlockedUsers())
                self.contactDefendants(bootmode=self.start)
            except pywikibot.EditConflict:
                pywikibot.output("Edit conflict found, try again.")
                continue  # try again and skip waittime
            except pywikibot.PageNotSaved:
                pywikibot.output("Page not saved, try again.")
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
                    print('.', end='')
            print('\n')

            self.optOutListAge += time() - now

            # read older entries again after ~4 minutes
            if time() - starttime > 250:
                starttime = time()
                self.reset_timestamp()
            self.start = False
            self.total = 10


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


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pywikibot.output('Script terminated by KeyboardInterrupt.')
