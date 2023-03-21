#!/usr/bin/python
"""
@note: Pywikibot framework is needed.

These command line parameters can be used to specify how to work:
...

"""
#
# (C) xqt, 2016-2023
#
from __future__ import annotations

import re

from datetime import timedelta
from time import time

import pywikibot
from pywikibot import Timestamp, textlib
from pywikibot.backports import Tuple
from pywikibot.bot import SingleSiteBot
from pywikibot.comms.eventstreams import site_rc_listener

vmHeadlineRegEx = (r'(==\ *?(?:(?:Artikel|Seite)[: ])?\[*?\:?'
                   r'%s(?:\|[^]]+)?\ *\]*?)\ *?==\ *')
vmErlRegEx = r'(?:\(erl\.?\)|\(erledigt\)|\(gesperrt\)|\(in Bearbeitung\))'

VM_PAGES = {
    'wikipedia:de': {
        'VM': ['Wikipedia:Vandalismusmeldung', 'erl.'],
        'test': ['user:xqt/Test', 'erl.'],
    },
    'wiktionary:de': {
        'VM': ['Wiktionary:Vandalismusmeldung', 'erl.']
    },
}


def isIn(text: str, regex):  # noqa: N802
    """Search regex in text."""
    return re.search(regex, text)


def divide_into_slices(rawText: str) -> Tuple[str, list, list]:  # noqa: N803
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


class vmBot(SingleSiteBot):  # noqa: N801

    """VM Bot Class."""

    total = 50

    def __init__(self, **kwargs):
        """Only accept options defined in availableOptions."""
        self.available_options.update({
            'projectpage': 'VM'
        })
        super().__init__(**kwargs)
        sitename = self.site.sitename
        self.reset_timestamp()
        self.prefix = 'Benutzer:Xqbot/'
        self.vmPageName = VM_PAGES[sitename][self.opt.projectpage][0]
        self.vmHeadNote = VM_PAGES[sitename][self.opt.projectpage][1]
        pywikibot.info('Project page is ' + self.vmPageName)

    def reset_timestamp(self):
        """Reset current timestamp."""
        self.nexttimestamp = '20201023012345'

    def load_events(self, logtype):
        """Load blocking events.

        return:
        [(title, byadmin, timestamp, blocklength, reason)]
        """
        # TODO: prüfen, ob immer noch geschützt ist oder
        # der Schutz zwischenzeitlich aufgehoben wurde
        newNexttimestamp = None
        events = []
        for block in self.site.logevents(logtype=logtype,
                                         end=self.nexttimestamp,
                                         total=self.total):
            if block.action() != 'protect':
                continue
            try:
                title = block.page().title()
            except KeyError:  # hidden user by OS action
                continue
            # Verschiebeschutz erst mal raus
            details = block._params['details']
            for detail in details:
                if detail['type'] == 'edit':
                    break
            else:
                continue
            # Falls Benutzerseite gesperrt wird, nicht bearbeiten
            # TODO: Doch, wenn Artikel davor steht!
            if block.page().namespace() == 2:
                continue
            byadmin = block.user()
            timeBlk = block.timestamp()
            reason = block.comment() or '<keine angegeben>'
            blocklength = block._params.get(
                'description').strip('\u200e').replace('\u200e', ' ')

            # use the latest block only
            if newNexttimestamp is None:
                newNexttimestamp = timeBlk

            el = (title, byadmin, timeBlk.totimestampformat(), blocklength,
                  reason)
            events.append(el)

        if newNexttimestamp:
            self.nexttimestamp = (newNexttimestamp + timedelta(
                seconds=1)).totimestampformat()
            pywikibot.info(f'\nNew timestamp: {self.nexttimestamp}\n')
        return events

    def markBlockedusers(self, blockedUsers):  # noqa: N802, N803
        """
        Write a message to project page.

        blockedUsers is a tuple of
        (title, byadmin, timestamp, blocklength, reason)
        """
        if not blockedUsers:
            return

        userOnVMpageFound = 0
        editSummary = ''
        oldRawVMText = ''

        try:
            vmPage = pywikibot.Page(pywikibot.Site(), self.vmPageName)
            oldRawVMText = vmPage.text
            rev_id = vmPage.latest_revision_id
        except pywikibot.exceptions.NoPageError:
            pywikibot.info('could not open or write to project page')
            return

        # read the VM page
        intro, vmHeads, vmBodies = divide_into_slices(oldRawVMText)

        # add info messages
        for el in blockedUsers:
            title, byadmin, timestamp, blocklength, reason = el
            pywikibot.info(
                'blocked page: %s blocked by %s,\n'
                'time: %s length: <<lightyellow>>%s<<default>>,\n'
                'reason: %s\n' % el)
            # escape chars in the username to make the regex working
            regExUserName = re.escape(title)

            # check if title was reported on VM
            for i, header in enumerate(vmHeads):
                if title in vmHeads:
                    print('salvage found', title)  # noqa: T201
                    raise
                if isIn(header, vmHeadlineRegEx % regExUserName):
                    try:
                        print('found', regExUserName)  # noqa: T201
                    except UnicodeEncodeError:
                        pass
                if isIn(header,
                        vmHeadlineRegEx
                        % regExUserName) and not isIn(header, vmErlRegEx):
                    userOnVMpageFound += 1
                    if isIn(title, '\d+\.\d+\.\d+\.\d+'):
                        editSummary += ', [[%s|%s]]' \
                                       % (title, title)
                    else:
                        editSummary += ', [[%s|]]' % title
                    reasonWithoutPipe = textlib.replaceExcept(
                        reason, '\|', '{{subst:!}}', [])
                    newLine = (
                        '{{subst:%sVM-erledigt|Gemeldeter=%s|Admin=%s|'
                        'Zeit=%s|Begründung=%s|subst=subst:|'
                        'Aktion=geschützt}}'
                        % (self.prefix, title, byadmin, blocklength,
                           reasonWithoutPipe))

                    # change headline and add a line at the end
                    # ignore some variants from closing
                    if True:
                        vmHeads[i] = textlib.replaceExcept(
                            header, vmHeadlineRegEx % regExUserName,
                            '\\1 ({}) =='.format(self.vmHeadNote),
                            ['comment', 'nowiki', 'source'])  # for headline
                    vmBodies[i] += newLine + '\n'

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
            pywikibot.info('markiere: ' + editSummary)

            # sanity check
            if vmPage.latest_revision.revid != rev_id:
                raise pywikibot.exceptions.EditConflictError(
                    'Revision ID changed')

            vmPage.put(newRawText,
                       'Bot: Abschnitt{} erledigt: {}'
                       .format(('', 'e')[bool(userOnVMpageFound - 1)],
                               editSummary + openSections),
                       watch='unwatch', minor=True, force=True)
        else:
            pywikibot.info(f'auf {self.opt.projectpage} ist nichts zu tun')

    def run(self):
        """Run the bot."""
        starttime = time()
        rc_listener = site_rc_listener(self.site)
        rc_listener.register_filter(type=('log', 'edit'))
        while True:
            pywikibot.info(Timestamp.now().strftime('>> %H:%M:%S: '))
            try:
                self.markBlockedusers(self.load_events('protect'))
            except pywikibot.exceptions.EditConflictError:
                pywikibot.info('Edit conflict found, try again.')
                continue  # try again and skip waittime
            except pywikibot.exceptions.PageSaveRelatedError:
                pywikibot.info('Page not saved, try again.')
                continue  # try again and skip waittime

            # wait for new block entry
            print()  # noqa: T001, T201

            pywikibot.stopme()
            for i, entry in enumerate(rc_listener):
                if i % 25 == 0:
                    print('\r', ' ' * 50,  # noqa: T001, T201
                          '\rWaiting for events', end='')
                if entry['type'] == 'log' and \
                   entry['log_type'] == 'protect' and \
                   entry['log_action'] == 'protect':
                    pywikibot.info('\nFound a new protect event '
                                   'by user "{}" for page "{}"'
                                   .format(entry['user'], entry['title']))
                    break
                if entry['type'] == 'edit' and \
                   not entry['bot'] and \
                   entry['title'] == self.vmPageName:
                    pywikibot.info('\nFound a new edit by user "{}"'
                                   .format(entry['user']))
                    break
                if not entry['bot']:
                    print('.', end='', flush=True)  # noqa: T001, T201
            print('\n')  # noqa: T001, T201

            # read older entries again after ~4 minutes
            if time() - starttime > 250:
                starttime = time()
                self.reset_timestamp()
            self.total = 15  # 10 is too low, see 20190226


def main(*args):
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    @param args: command line arguments
    @type args: list of str
    """
    # read arguments
    options = {}
    for arg in pywikibot.handle_args(args):
        opt, _, value = arg.partition(':')
        if not opt.startswith('-'):
            continue
        opt = opt[1:]
        if value:
            options[opt] = value
        else:
            options[opt] = True

    bot = vmBot(**options)
    try:
        bot.run()
    except KeyboardInterrupt:
        pywikibot.info('Script terminated by KeyboardInterrupt.')


if __name__ == '__main__':
    main()
