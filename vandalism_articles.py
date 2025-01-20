#!/usr/bin/python
"""
@note: Pywikibot framework is needed.

These command line parameters can be used to specify how to work:
...

"""
#
# (C) xqt, 2016-2025
#
from __future__ import annotations

import re
from datetime import timedelta

import pywikibot
from pywikibot import Timestamp, textlib
from pywikibot.bot import SingleSiteBot
from pywikibot.comms.eventstreams import site_rc_listener
from pywikibot.textlib import extract_sections

vmHeadlineRegEx = (r'(==\ *?(?:(?:Artikel|Seite)[: ])?\[*?\:?'
                   r'%s(?:\|[^]]+)?\ *\]*?)\ *?==\ *')
VM_ERL_R = r'\( *((nicht +)?erl(\.?|edigt)|gesperrt|in Bearbeitung) *\)'
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
        self.nexttimestamp = '20250120012345'
        self.prefix = 'Benutzer:Xqbot/'
        self.vmPageName = VM_PAGES[sitename][self.opt.projectpage][0]
        self.vmHeadNote = VM_PAGES[sitename][self.opt.projectpage][1]
        pywikibot.info('Project page is ' + self.vmPageName)

    def divide_into_slices(self, text: str) -> tuple[str, list, list]:
        """Analyze text.

        Analyze the whole text to get the intro, the headlines and the
        corresponding bodies.
        """
        sections = extract_sections(text, self.site)
        vmHeads = []
        vmBodies = []
        for head, body in sections.sections:
            vmHeads.append(head)
            vmBodies.append(body)
        return sections.header, vmHeads, vmBodies

    def load_events(self, logtype, actions):
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
            if block.action() not in actions:
                continue
            try:
                title = block.page().title()
            except KeyError:  # hidden user by OS action
                continue
            # Verschiebeschutz erst mal raus
            details = block.params['details']
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
            blocklength = block.params.get(
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

        vmPage = pywikibot.Page(pywikibot.Site(), self.vmPageName)
        try:
            old_text = vmPage.text
            rev_id = vmPage.latest_revision_id
        except pywikibot.exceptions.NoPageError:
            pywikibot.info('could not open or write to project page')
            return

        # read the VM page
        intro, vmHeads, vmBodies = self.divide_into_slices(old_text)

        # add info messages
        for el in blockedUsers:
            title, byadmin, timestamp, blocklength, reason = el
            # escape chars in the username to make the regex working
            regExUserName = re.escape(title)
            pywikibot.info(
                'blocked page: %s blocked by %s,\n'
                'time: %s length: <<lightyellow>>%s<<default>>,\n'
                'reason: %s\n' % el)

            # check if title was reported on VM
            for i, header in enumerate(vmHeads):
                if isIn(header, VM_ERL_R):  # erledigt
                    continue

                if not isIn(header, vmHeadlineRegEx % regExUserName):
                    continue

                userOnVMpageFound += 1
                if isIn(title, '\d+\.\d+\.\d+\.\d+'):
                    editSummary += ', [[%s|%s]]' \
                                   % (title, title)
                else:
                    editSummary += ', [[%s|]]' % title
                reasonWithoutPipe = textlib.replaceExcept(
                    reason, '\|', '{{subst:!}}', [])
                newLine = (
                    '{{subst:%(prefix)sVM-erledigt|Gemeldeter=%(title)s|'
                    'Admin=%(admin)s|Zeit=%(duration)s|'
                    'Begründung=%(reason)s|subst=subst:|'
                    'Aktion=geschützt}}\n'
                ) % {'prefix': self.prefix,
                     'title': title,
                     'admin': byadmin,
                     'duration': blocklength,
                     'reason': reasonWithoutPipe}

                # change headline and add a line at the end
                # ignore some variants from closing
                if True:
                    # write back indexed header
                    vmHeads[i] = re.sub('== *$', '(erl.) ==', header)
                vmBodies[i] += newLine

        # was something changed?
        if userOnVMpageFound:  # new version of VM
            # we count how many sections are still not cleared
            headlinesWithOpenStatus = 0
            oldestHeadlineWithOpenStatus = ''
            for header in vmHeads:
                # count any user
                if isIn(header,
                        vmHeadlineRegEx % '.+') and not isIn(header, VM_ERL_R):
                    headlinesWithOpenStatus += 1
                    if not oldestHeadlineWithOpenStatus:
                        oldestHeadlineWithOpenStatus = textlib.replaceExcept(
                            header, '(?:==\ *|\ *==)', '',
                            ['comment', 'nowiki', 'source'])

            openSections = ''
            if headlinesWithOpenStatus == 1:
                openSections = (f'; Abschnitt {oldestHeadlineWithOpenStatus}'
                                f' scheint noch offen zu sein')
            elif headlinesWithOpenStatus > 1:
                openSections = (f'; {headlinesWithOpenStatus} Abschnitte '
                                f'scheinen noch offen zu sein, der älteste zu '
                                f'{oldestHeadlineWithOpenStatus}')

            newRawText = intro
            for i, header in enumerate(vmHeads):
                newRawText += header + vmBodies[i]

            # compare them
            pywikibot.showDiff(old_text, newRawText)
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
        rc_listener = site_rc_listener(self.site)
        rc_listener.register_filter(type=('log', 'edit'))
        while True:
            pywikibot.info(Timestamp.now().strftime('>> %H:%M:%S: '))
            try:
                self.markBlockedusers(self.load_events('protect', ['protect']))
            except pywikibot.exceptions.EditConflictError:
                pywikibot.info('Edit conflict found, try again.')
                continue  # try again and skip waittime
            except pywikibot.exceptions.PageSaveRelatedError:
                pywikibot.info('Page not saved, try again.')
                continue  # try again and skip waittime

            # wait for new block entry
            pywikibot.info()
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

            pywikibot.info('\n')
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
