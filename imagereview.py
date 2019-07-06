#!/usr/bin/python
# -*- coding: utf-8 -*-
#
"""
This bot script is developed for the image review processing on de-wiki.

See https://de.wikipedia.org/wiki/Wikipedia:D%C3%9CP for it

This script is run by [[de:user:xqt]].
It should not be run by other users without prior contact.

The following parameters are supported:

-always          Do not ask for writing a page, always do it

-check           Image review processing

-list            Create a list of unused files listed at
                 [[Kategorie:Wikipedia:Dateiüberprüfung/Gültige_Problemangabe]]
                 sorted by upload timestamp

-review          Look for previous usage of an image write a hint to the talk
                 page

-touch           Touch every category to update its content

-total:<number>  Only check the given number of files

"""
#
# (C) xqt, 2012-2019
#
# Distributed under the terms of the MIT license.
#
from __future__ import annotations

from contextlib import suppress
import copy
from datetime import datetime, timedelta
import re

import pywikibot
from pywikibot.bot import SingleSiteBot, suggest_help
from pywikibot import config, FilePage, pagegenerators, textlib
from pywikibot.site import Namespace

remark = {
    '1923':
        'Fehlende Nachweise bei der'
        " '''[[Wikipedia:Bildrechte#1923|1923-Regel]]''':"
        ' Die deutschsprachige Wikipedia akzeptiert Bilder, die nachweislich'
        ' vor 1923 veröffentlicht wurden. Um eine solche Datei hier'
        ' einzustellen, sind jedoch folgende Bedingungen zu erfüllen:'
        '\n** Du musst auf der Dateibeschreibungsseite nachweisen, dass das'
        " Bild vor 1923 '''veröffentlicht''' wurde und dass der Urheber oder"
        ' dessen Todesdatum auch nach gründlicher Recherche nicht'
        ' herausgefunden werden kann.'
        '\n** Du musst als Uploader eine Diskussion auf'
        ' [[Wikipedia:Dateiüberprüfung/1923]] einleiten und den Sachverhalt'
        ' und die Nachweise darlegen.',
    'Freigabe':
        "'''Freigabe:'''"
        ' Du brauchst eine Erlaubnis, wenn du eine urheberrechtlich geschützte'
        ' Datei hochlädst. Um eine solche Erlaubnis zu formulieren, bieten wir'
        ' einen Online-Assistenten unter https://wmts.dabpunkt.eu/freigabe3/'
        ' an. Er hilft Dir, die passende Formulierung zu finden, egal ob Du'
        ' selbst der Urheber bist oder die Datei von einer anderen Person'
        ' geschaffen wurde.',
    'Gezeigtes Werk':
        "'''Gezeigtes Werk:'''"
        ' Um ein Foto, das ein urheberrechtlich geschütztes Werk einer anderen'
        ' Person (z.&nbsp;B. ein Foto eines Plakats oder eine Nachzeichnung'
        ' eines Gemäldes) zeigt, hochzuladen brauchst du eine Erlaubnis. Bitte'
        ' den Urheber um eine solche Erlaubnis wie'
        ' [[WP:TV#Freigabe gezeigtes Werk|hier]] beschrieben. Das ist'
        ' nicht nötig, wenn sich das gezeigte Werk dauerhaft im öffentlichen'
        ' Verkehrsraum befindet (z.&nbsp;B. in einem öffentlichen Park), gib'
        ' dies auf der Dateibeschreibungsseite dann mit an.',
    'Lizenz':
        "'''Lizenz:'''"
        ' Eine Lizenz ist die Erlaubnis, eine Datei unter bestimmten'
        ' Bedingungen zu nutzen. In der deutschsprachigen Wikipedia werden nur'
        ' solche Dateien akzeptiert, die unter einer freien Lizenz stehen,'
        " die '''[[Wikipedia:Lizenzvorlagen für Bilder|hier]]''' gelistet"
        ' sind. Unser Online-Assistent unter'
        ' https://wmts.dabpunkt.eu/freigabe3/ hilft Dir, eine passende Lizenz'
        ' auszuwählen und den Text für Dich anzupassen. Wenn du der Urheber'
        ' der Datei oder der Inhaber der Nutzungsrechte bist, kannst Du ihn'
        ' benutzen, um den Text anschließend in die Dateibeschreibungsseite'
        ' einzufügen.',
    'Quelle':
        "'''Quelle:'''"
        ' Hier vermerkst du, wie du zu dieser Datei gekommen bist. Das kann'
        ' z.&nbsp;B. ein Weblink sein oder – wenn du das Bild selbst gemacht'
        ' hast – die Angabe „selbst fotografiert“ bzw. „selbst gezeichnet“.',
    'Urheber':
        "'''Urheber:'''"
        ' Der Schöpfer des Werks (z.&nbsp;B. der Fotograf oder der Zeichner).'
        ' Man wird aber keinesfalls zum Urheber, wenn man bspw. ein Foto von'
        ' einer Website nur herunterlädt oder ein Gemälde einfach'
        ' nachzeichnet! Wenn du tatsächlich der Urheber des Werks bist,'
        ' solltest du entweder deinen Benutzernamen oder deinen bürgerlichen'
        ' Namen als Urheber angeben. Im letzteren Fall muss allerdings'
        ' erkennbar sein, dass du (also %(user)s) auch diese Person bist.',
    'Hinweis':
        "'''Hinweis%(num)s'''"
        ' durch den [[WP:DÜP|]]-Bearbeiter: %(note)s',
}

remark_mail = {
    '1923':
        'Fehlende Nachweise bei der 1923-Regel'
        ' (https://de.wikipedia.org/wiki/Wikipedia:Bildrechte#1923):'
        ' Die deutschsprachige Wikipedia akzeptiert Bilder, die nachweislich'
        ' vor 1923 veröffentlicht wurden. Um eine solche Datei hier'
        ' einzustellen, sind jedoch folgende Bedingungen zu erfüllen:'
        '\n- Du musst auf der Dateibeschreibungsseite nachweisen, dass das'
        ' Bild vor 1923 veröffentlicht wurde und dass der Urheber oder dessen'
        ' Todesdatum auch nach gründlicher Recherche nicht herausgefunden'
        ' werden kann.'
        '\n- Du musst als Uploader eine Diskussion auf'
        ' https://de.wikipedia.org/wiki/Wikipedia:Dateiüberprüfung/1923'
        ' einleiten und den Sachverhalt und die Nachweise darlegen.',
    'Freigabe': remark['Freigabe'],
    'Gezeigtes Werk':
        'Gezeigtes Werk:'
        ' Um ein Foto, das ein urheberrechtlich geschütztes Werk einer anderen'
        ' Person (z.B. ein Foto eines Plakats oder eine Nachzeichnung eines'
        ' Gemäldes) zeigt, hochzuladen brauchst du eine Erlaubnis. Bitte den'
        ' Urheber um eine solche Erlaubnis wie auf'
        ' https://de.wikipedia.org/wiki/Wikipedia:TV#Freigabe_gezeigtes_Werk'
        ' beschrieben. Das ist nicht nötig, wenn sich das gezeigte Werk'
        ' dauerhaft im öffentlichen Verkehrsraum befindet (z.B. in einem'
        ' öffentlichen Park), gib dies auf der Dateibeschreibungsseite dann'
        ' mit an.',
    'Lizenz':
        'Lizenz:'
        ' Eine Lizenz ist die Erlaubnis, eine Datei unter bestimmten'
        ' Bedingungen zu nutzen. In der deutschsprachigen Wikipedia werden nur'
        ' solche Dateien akzeptiert, die unter einer freien Lizenz stehen, die'
        ' auf https://de.wikipedia.org/wiki/'
        'Wikipedia:Lizenzvorlagen_f%%C3%%BCr_Bilder gelistet sind.'
        ' Unser Online-Assistent unter https://wmts.dabpunkt.eu/freigabe3/'
        ' hilft Dir, eine passende Lizenz auszuwählen und den Text für Dich'
        ' anzupassen. Wenn du der Urheber der Datei oder der Inhaber der'
        ' Nutzungsrechte bist, kannst Du ihn benutzen, um den Text'
        ' anschließend in die Dateibeschreibungsseite einzufügen.',
    'Quelle':
        'Quelle:'
        ' Hier vermerkst du, wie du zu dieser Datei gekommen bist. Das kann'
        ' z.B. ein Weblink sein oder - wenn du das Bild selbst gemacht hast -'
        ' die Angabe "selbst fotografiert" bzw. "selbst gezeichnet".',
    'Urheber':
        'Urheber:'
        ' Der Schöpfer des Werks (z.B. der Fotograf oder der Zeichner). Man'
        ' wird aber keinesfalls zum Urheber, wenn man bspw. ein Foto von einer'
        ' Website nur herunterlädt oder ein Gemälde einfach nachzeichnet! Wenn'
        ' du tatsächlich der Urheber des Werks bist, solltest du entweder'
        ' deinen Benutzernamen oder deinen bürgerlichen Namen als Urheber'
        ' angeben. Im letzteren Fall muss allerdings erkennbar sein, dass du'
        ' (also %(user)s) auch diese Person bist.',
    'Hinweis':
        'Hinweis%(num)s'
        ' durch den Bearbeiter: %(note)s'
}

msg = """

== Problem{{PLURAL:count| mit Deiner Datei|e mit Deinen Dateien}} (%(date)s) ==

Hallo %(user)s,

bei %(the)s folgenden von dir hochgeladenen %(file)s gibt es noch %(1)sProblem%(e)s:

# %(list)s

* %(help)s

Durch Klicken auf „Bearbeiten“ oben auf %(the)s Dateibeschreibungsseite%(n)s kannst du die fehlenden Angaben nachtragen. Wenn %(2)s Problem%(e)s nicht innerhalb von 14 Tagen behoben %(be)s, %(must)s die %(file)s leider gelöscht werden.

Fragen beantwortet dir möglicherweise die [[Hilfe:FAQ zu Bildern|Bilder-FAQ]]. '''Du kannst aber auch gern hier in diesem Abschnitt antworten, damit dir individuell geholfen wird.'''

Vielen Dank für deine Unterstützung, [[Benutzer:Xqbot|Xqbot]] ([[WD:DÜP|Diskussion]]) ~~~~~
"""  # noqa

mail_msg = """
Hallo %(user)s,

bei %(the)s folgenden von dir hochgeladenen %(file)s gibt es noch %(1)sProblem%(e)s:

# %(list)s

* %(help)s

Durch Klicken auf „Bearbeiten“ oben auf %(the)s Dateibeschreibungsseite%(n)s kannst du die fehlenden Angaben nachtragen. Wenn %(2)s Problem%(e)s nicht innerhalb von 14 Tagen behoben %(be)s, %(must)s die %(file)s leider gelöscht werden.

Fragen beantwortet dir möglicherweise die Bilder-FAQ auf https://de.wikipedia.org/wiki/WP:FAQB . Du kannst aber auch gern auf diese Mail antworten, damit dir individuell geholfen wird.

Als Empfänger-Adresse trage bitte die des Support-Teams ein:
permissions-de@wikimedia.org .

Vielen Dank für deine Unterstützung,
dein Xqbot
--
Diese E-Mail wurde automatisch erstellt und verschickt. Xqbot wird von freiwilligen Autoren der deutschsprachigen Wikipedia betrieben.
"""  # noqa

DUP_REASONS = ['1923', 'Freigabe', 'Gezeigtes Werk', 'Lizenz', 'Quelle',
               'Urheber', 'Hinweis']

MAX_EMAIL = 20  # version 1.21wmf10


class DUP_Image(FilePage):  # noqa: N801

    """FilePage holding review informations."""

    def __init__(self, site, title, text=None, timestamp=None):
        """Initializer."""
        super(DUP_Image, self).__init__(site, title)
        self._contents = text
        # NOTE: self.templates is already used by FilePage in core
        #       but it isn't in compat.
        self.review_tpl = []  # used by informuser()
        self.reasons = set()
        self.info = False
        self.done = None
        self._editTime = timestamp
        self.remark = None
        # breaking change mit
        # https://www.mediawiki.org/wiki/Special:Code/pywikipedia/11347
        # Vorlage sind damit normalisiert!
        templ = ('DÜP', 'Düp', 'Dateiüberprüfung')
        if self._contents:
            self.done = '3=[[Benutzer:Xqbot|Xqbot]]' in self._contents
            for tpl, param in self.templatesWithParams():
                if tpl.title(with_ns=False) in templ:
                    self.review_tpl.append(tpl)
                    for r in param:
                        if r.strip():
                            self.reasons.add(r.strip())
                elif tpl.title(with_ns=False) == 'Information':
                    self.info = True

    @property
    def valid_reasons(self):
        """Validate image review reasons."""
        if not self.reasons:
            pywikibot.output(
                '\nIgnoriere {}: kein Grund angegeben'.format(self))
            return False

        for r in self.reasons.copy():
            if r.startswith('Hinweis'):
                self.reasons.remove(r)
                self.reasons.add('Hinweis')
                # r is already stripped by extract_templates_and_params
                r, sep, self.remark = r.partition('=')
            if r not in DUP_REASONS:
                pywikibot.output(
                    '\nIgnoriere {}: Grund {} wird nicht bearbeitet'
                    .format(self, r if r else '(keiner angegeben)'))
                return False
        return True

    @property
    def has_refs(self):
        """Check whether the page as any references."""
        refs = iter(self.usingPages())
        try:
            next(refs)
        except StopIteration:
            return False
        return True


class CheckImageBot(SingleSiteBot):

    """Bot to review uploaded Files."""

    def __init__(self, **options):
        """Initializer."""
        self.availableOptions.update({
            'list': False,    # list unreferenced Files
            'check': False,   # DÜP
            'total': 25,      # total images to process
            'review': False,  # check for lastUploader != firstUploader
            'touch': False,   # touch categories to actualize the time stamp
        })
        super(CheckImageBot, self).__init__(**options)

        self.source = 'Wikipedia:Dateiüberprüfung/Gültige_Problemangabe'
        self.total = self.getOption('total')
        self.mails = 0
        if self.getOption('list'):
            if self.getOption('check'):
                pywikibot.warning(
                    'You cannot use "-check" option together with "-list";\n'
                    '-check was ignored.')
            self.dest = 'Benutzer:Quedel/Datei/DÜP-Eingang'
            self.sort = 1  # timestamp
            self.summary = ('Bot: Aktualisiere unbenutzte Dateien, '
                            'sortiert nach Datum')
            self.filter = True  # List unreferences Files only
        elif self.getOption('check'):
            self.dest = 'Benutzer:xqbot/DÜP-Log'
            self.sort = 0  # uploader
            self.summary = ('Bot: Aktualisiere bearbeitete Dateien, '
                            'sortiert nach Uploader')
            self.filter = False

    @property
    def generator(self):
        """Retrieve images to be checked."""
        cat = pywikibot.Category(
            self.site,
            '{}:{}'.format(self.site.namespaces.CATEGORY.custom_name,
                           self.source))
        gen = pagegenerators.CategorizedPageGenerator(cat)
        gen = pagegenerators.NamespaceFilterPageGenerator(
            gen, self.site.namespaces.FILE.custom_name)
        if not self.filter:
            gen = pagegenerators.PreloadingGenerator(gen)
        # gen = pagegenerators.ImageGenerator(gen)
        for item in gen:
            page = DUP_Image(item.site, item.title(),
                             not self.filter and item.get() or None,
                             item.editTime())
            if self.filter and page.has_refs:
                continue
            if not self.filter and not page.valid_reasons:
                continue
            yield page

    def save(self, page, newtext, summary=None, show_diff=True, force=False):
        """Save the page to the wiki, if the user accepts the changes made."""
        done = False
        try:
            oldtext = page.get()
        except pywikibot.NoPage:
            oldtext = ''
        if oldtext == newtext:
            pywikibot.output('No changes were needed on '
                             + page.title(as_link=True))
            return

        pywikibot.output('\n\n>>> \03{lightpurple}%s\03{default} <<<'
                         % page.title())
        if show_diff:
            pywikibot.showDiff(oldtext, newtext)

        choice = 'a'
        if not self.getOption('always'):
            choice = pywikibot.input_choice(
                'Do you want to accept these changes?',
                [('Yes', 'y'), ('No', 'n'), ('Always yes', 'a')], default='n')
            if choice == 'n':
                return
            elif choice == 'a':
                self.options['always'] = True

        try:
            page.put(newtext, summary or self.summary,
                     minor=page.namespace() != 3, force=force)
        except pywikibot.EditConflict:
            pywikibot.output('Skipping %s because of edit conflict'
                             % (page.title(),))
        except pywikibot.SpamfilterError as e:
            pywikibot.output(
                'Cannot change {} because of blacklist entry {}'
                .format(page.title(), e.url))
        except pywikibot.LockedPage:
            pywikibot.output('Skipping {} (locked page)'.format(page.title()))
        else:
            done = True
        return done

    def inform_user(self, user, data):
        """
        Inform user.

        data = [[title(asLink=True),
                    [user, timestamp],
                    DUP_Image{},
                    <None|reasons>,
                    <None>  # reserved for notification info
        ], ]
        """
        # verstorbene
        ignoreUser = set()
        ignorePage = pywikibot.Page(
            self.site,
            'Wikipedia:Gedenkseite für verstorbene Wikipedianer')
        for p in ignorePage.linkedPages():
            if p.namespace() == 2:
                ignoreUser.add(p.title(with_ns=False).split('/')[0])
        where = ''
        images = []
        problems = set()
        hints = {}
        k = 0
        for a in data:
            image = copy.copy(a[2])
            images.append(image)
            reasons = image.reasons
##            a[3] = ', '.join(reasons)
##            a[3] = "%s - '''Problem%s''': %s" \
##                   % (a[0], 'e' if len(reasons) != 1 else '', a[3])
            problems.update(reasons)
            i = 0
            if image.remark:
                if image.remark in hints.values():
                    for item in hints.items():
                        if image.remark == item[1]:
                            i = item[0]
                            break
                else:
                    k += 1
                    hints[k] = image.remark
                    i = k
                reasons.remove('Hinweis')
            a[3] = (reasons, i)

        if hints:
            problems.remove('Hinweis')
        if len(hints) <= 1:
            hint_str = ', Hinweis'
        else:
            hint_str = ', Hinweis %(num)d'

        param = {}
        param['user'] = user
        param['e'], param['1'], param['2'], param['be'] = (
            'e', '', 'die', 'werden') \
            if len(problems) != 1 else ('', 'ein ', 'das', 'wird')
        param['list'] = '\n# '.join(["{} - '''Problem{}''': {}{}"
                                     .format(a[0],
                                             'e' if len(a[3][0]) != 1 else '',
                                             ', '.join(sorted(a[3][0])),
                                             hint_str % {'num': a[3][1]}
                                             if a[3][1] > 0 else '')
                                     for a in data])

        param['help'] = '\n* '.join(remark[r] % {'user': user}
                                    for r in sorted(problems))
        for num in sorted(hints):
            param['help'] += '\n* ' + remark['Hinweis'] % {'note': hints[num],
                                                           'num': ' %d' % num
                                                           if len(hints) > 1
                                                           else ''}
        param['date'] = datetime.now().strftime('%d.%m.%Y')
        param['count'] = len(data)
        if len(data) != 1:
            param['file'] = 'Dateien'
            param['the'] = 'den'
            param['n'] = 'n'
            param['must'] = 'müssen'
        else:
            param['file'] = 'Datei'
            param['the'] = 'der'
            param['n'] = ''
            param['must'] = 'muss'

        if user in ignoreUser:
            pywikibot.output('%s was ignored (inactive).' % user)
            where = 'Verstorben'
        else:
            # auf BD benachrichtigen
            use_talkpage = True
            up = pywikibot.Page(self.site, user, ns=3)
            # Weiterleitungen folgen, evtl. Namensänderung
            while up.isRedirectPage():
                try:
                    up = up.getRedirectTarget()
                except pywikibot.InterwikiRedirectPage:
                    use_talkpage = False
                    break  # use redirect page instead of redirect target
            title = up.title(with_ns=False)
            if '/' in title:
                up1 = pywikibot.Page(self.site, title.split('/', 1)[0],
                                     defaultNamespace=3)
                if up1.isRedirectPage():
                    up = up1
            if up.namespace() == 3:
                upm = pywikibot.User(self.site, up.title(with_ns=False))
                if upm.isRegistered() and use_talkpage:
                    try:
                        text = up.get()
                    except pywikibot.NoPage:
                        text = ''
                    text += pywikibot.translate('de', msg, param)
                    if self.save(
                        up, text,
                        summary='Bot: Neue Nachricht von der [[WP:DÜP|DÜP]]',
                            show_diff=False, force=True):
                        where = 'Disk'
            else:
                upm = pywikibot.User(self.site, user)

            upm = pywikibot.User(self.site, user)

            # per Mail benachrichtigen
            if upm.isRegistered() and upm.isEmailable():
                pywikibot.output('%s has mail enabled.' % user)
                param['list'] = '\r\n# '.join(
                    ['https://de.wikipedia.org/wiki/%s - Problem%s: %s%s'
                     % (a[2].title(as_url=True),
                        'e' if len(a[3][0]) != 1 else '',
                        ', '.join(sorted(a[3][0])),
                        hint_str % {'num': a[3][1]}
                        if a[3][1] > 0 else '')
                     for a in data])
                param['help'] = '\n* '.join(remark_mail[r] % {'user': user}
                                            for r in sorted(problems))
                for num in sorted(hints):
                    param['help'] += '\n* ' + remark_mail['Hinweis'] \
                                     % {'note': hints[num],
                                        'num': ' %d' % num
                                        if len(hints) > 1 else ''}

                text = mail_msg % param
                if upm.send_email(
                        subject='Bot: Neue Nachricht von der '
                        'Wikipedia-Dateiüberprüfung an {0}'.format(user),
                        text=text):
                    self.mails += 1
                    if where:
                        where += '+Mail'
                    else:
                        where = 'Mail'
            else:
                pywikibot.output('%s has mail disabled.' % user)

        if not where:
            where = 'Unbekannt' if not upm.isRegistered() else 'Gar nicht'

        for entry in data:  # add notification notes
            entry[4] = where

        # jetzt alle Dateien eines Benutzers bearbeiten
        for i in images:
            tmpl = i.review_tpl
            if not tmpl:
                pywikibot.output('template nicht gefunden für {}'
                                 .format(i.title()))
                continue
            summary = 'Bot: Benutzer %s, Vorlage umgeschrieben' \
                      % ('konnte nicht benachrichtigt werden'
                         if where in ['Gar nicht',
                                      'Verstorben',
                                      'Unbekannt'] else 'benachrichtigt')
            text = i.get()
            if self.getOption('check'):
                if i.has_refs:
                    inline = (
                        '\n{{Dateiüberprüfung/benachrichtigt (Verwendung)'
                        '|~~~~~|')
                    for ref in i.usingPages():
                        inline += ('\n{{Dateiüberprüfung/benachrichtigt '
                                   '(einzelne Verwendung)|%s}}' % ref.title())
                    inline += '\n}}'
                else:
                    inline = ''
                if not i.info:
                    summary += ', Vorlage:Information ergänzt'
                    inline += """
{{Information
| Beschreibung     =
| Quelle           =
| Urheber          =
| Datum            =
| Genehmigung      =
| Andere Versionen =
| Anmerkungen      =
}}
"""  # noqa
                firstTmpl = tmpl.pop(0)
                if 'Hinweis' in i.reasons:
                    i.reasons.remove('Hinweis')
                reasons = '|'.join(sorted(i.reasons))
                if i.remark:
                    reasons += '|7=Hinweis=%s' % i.remark
                text = re.sub(
                    '(?is)\{\{%s *\|(.*?)\}\}'
                    % firstTmpl.title(with_ns=False),
                    '{{Dateiüberprüfung/benachrichtigt (Vermerk)|%s|%s|'
                    '3=~~~~}}'
                    '\n{{subst:Dateiüberprüfung/benachrichtigt|%s}}%s'
                    % (user, where, reasons, inline), text, 1)
                if tmpl:  # verbliebene Templates löschen
                    text = re.sub(
                        '(?i)\{\{(%s)[^/\{]*?\}\}' % '|'.join(
                            t.title(with_ns=False) for t in tmpl),
                        '', text)
            self.save(i, text, summary=summary)
        return True  # returns klären!!!

    def category_text(self, cat):
        """Read current category text or fill it with default.

        @param cat: category page object
        @type cat: pywikibot.Page
        @return: current category text or the default content
        @rtype: str
        """
        try:
            cattext = cat.get()
        except pywikibot.NoPage:
            cattext = """{{Dateiüberprüfung (Abarbeitungsstatus)
|Frühzeitig abgebrochen bei=
|Unterschrift=
|Fertig geworden=
|Kategoriebezeichnung=%s
}}
__NOTOC____NOEDITSECTION__
<br style="clear:both;" />
""" % datetime.now().strftime('%Y-%m-%d')
        return cattext

    def build_table(self, *, save=True, unittest=False):
        """Build table of FilePage objects and additional informations."""
        def f(k):
            """Sorting key 'editTime' for sorting operation."""
            if k not in table:
                pywikibot.warning(f'{k} is missing')
                return 0

            try:
                r = int(table[k][0][2].editTime().totimestampformat())
            except IndexError:
                pywikibot.warning(f'IndexError occured with {k}')
                pywikibot.output(table[k][0])
            else:
                return r
            return 0

        table = {}
        informed = []
        if self.getOption('check'):
            pywikibot.output('Processing %d images...' % self.total)
        for image in self.generator:
            uploader = [image.oldest_file_info.user,
                        image.oldest_file_info.timestamp.isoformat()]

            sortkey = uploader[self.sort]
            if sortkey not in table:
                table[sortkey] = []
            table[sortkey].append([image.title(as_link=True, textlink=True),
                                  uploader, image, None, None])
        pywikibot.output('\nBuilding wiki table...')
        keys = list(table.keys())  # py3 compatibility
        if self.getOption('list'):
            keys.sort()
        else:
            # keys.sort(key=lambda k: int(table[k][2].editTime()))
            keys.sort(key=f)
        text = """
{| class="wikitable sortable"
|-
! Datei || Zeitstempel || Uploader || Benachrichtigt || Letzte Aktivität
|-
"""
        if self.getOption('check'):
            cat = pywikibot.Page(self.site, self.cat, ns=Namespace.CATEGORY)
            cattext = self.category_text(cat)

        oneDone = False
        if self.getOption('check'):
            k = 0
            for key in keys:
                length = len(table[key])

                if self.total and k + length > self.total and oneDone:
                    if length == 1:
                        pywikibot.output('Max limit %d exceeded.' % self.total)
                        break
                    continue

                if unittest:
                    continue

                if self.inform_user(key, table[key]):
                    pywikibot.output('%s done.' % key)
                    informed.append(key)
                    k += length
                else:
                    pywikibot.output('%s ignored.' % key)
                    continue

                oneDone = True
                if self.mails >= MAX_EMAIL:
                    pywikibot.output('Max mail limit {} exceeded'
                                     .format(self.mails))
                    break

            pywikibot.output(
                '{} files processed, {} mails sent'.format(k, self.mails))

            # jetzt wieder sortieren und (leider) erneuten Druchlauf
            informed.sort()
            keys = informed

        for key in keys:
            if self.getOption('check'):
                cattext = self.add_uploader_info(cattext, key, table[key])

            for filename, fileinfo, _image, _reason, notified in table[key]:
                username, timestamp = fileinfo
                lastevent = next(iter(self.site.logevents(
                    user=username, total=1))).timestamp().isoformat()
                text += (f'| {filename} || {timestamp} |'
                         f'| [[Benutzer:{username}]] || {notified} |'
                         f'| {lastevent}\n|- \n')
        text += '|}'
        if save:
            if self.getOption('check'):
                self.save(cat, cattext, summary='Bot: Neue DÜP-Einträge')
            self.save(pywikibot.Page(self.site, self.dest), text)
        return table

    def run_check(self):
        """Image review processing."""
        self.build_table(save=True)

    def run_touch(self):
        """Touch every category to update its content."""
        # Alle zukünftigen Tageskategorien touchen
        day = timedelta(days=1)
        start = datetime.now()
        for _ in range(14):
            c = pywikibot.Category(self.site,
                                   'Kategorie:Wikipedia:Dateiüberprüfung ({})'
                                   .format(start.strftime('%Y-%m-%d')))
            self.touch(c)
            start -= day

    def run_review(self):
        """Look for previous usage of an image, write a hint to talk page."""
        config.cosmetic_changes = False
        cat = pywikibot.Category(self.site, '{}:{}'.format(
            self.site.namespaces.CATEGORY.custom_name, self.cat))
        gen = cat.articles()
        gen = pagegenerators.NamespaceFilterPageGenerator(gen, 'File')
        for image in gen:
            self.review(image)

    def run(self):
        """Run the bot."""
        tasks = ['check', 'list', 'review', 'touch']
        if not any(self.getOption(task) for task in tasks):
            additional_text = 'Action must be one of "-{}".'.format(
                '", "-'.join(tasks))
            suggest_help(missing_action=True, additional_text=additional_text)
            return

        if self.getOption('review'):
            self.cat = 'Wikipedia:Dateiüberprüfung/Verwendungsreview'
            self.run_review()
        if self.getOption('touch'):
            self.cat = 'Wikipedia:Dateiüberprüfung ' \
                       '(Tageskategorien, zukünftig)'
            self.run_touch()
        if self.getOption('check') or self.getOption('list'):
            self.cat = 'Kategorie:Wikipedia:Dateiüberprüfung (%s)' \
                       % datetime.now().strftime('%Y-%m-%d')
            self.run_check()

    def touch(self, cat):
        """
        Touch a single category.

        If a file isn't listed in the table, append it.
        """
        cattext = self.category_text(cat)
        table = {}

        for image in cat.articles():
            if not image.is_filepage() or image.title() in cattext:
                continue
            pywikibot.output('File %s is not listed' % image.title())
            uploader = image.getFirstUploader()[0]
            if uploader not in table:
                table[uploader] = []
            table[uploader].append(image)

        change = False
        for key in table:
            if textlib.does_text_contain_section(cattext, '\[\[%s\]\]' % key):
                newcattext = re.sub('(== \[\[%s\]\] ==.*?)\r?\n\r?\n== \[\['
                                    % key,
                                    '\1' + '######', cattext)
                print(newcattext)
                # TODO: Ergänze bei vorhandenem Uploader
            else:
                pywikibot.output('Uploader %s is not listed' % key)
                cattext = self.add_uploader_info(cattext, key, table[key])
                change = True

        if change:
            self.save(
                cat, cattext,
                'Bot: Ergänze fehlende Dateien oder Dateien mit Aufschub')
        else:
            cat.put(cattext, 'Bot: Lege neue Tageskategorie an')

    def add_uploader_info(self, text, uploader, images):
        """Append uploader info to the table on category page."""
        text += '\n== [[Benutzer:%s|]] ==\n\n' % uploader
        for image in images:
            if isinstance(image, pywikibot.Page) and image.is_filepage():
                title = image.title()
            else:  # from buildtable
                title = image[2].title()
            text += ('{{Dateiüberprüfung (Liste)|1=%s|2=%s}}\n'
                     % (title, uploader))
        return text

    def review(self, image):
        """Check whether page was transcluded previously."""
        imageID = None
        linked = []
        found = False
        # Search for last bot action
        for items in image.getVersionHistory():
            oldid, _, username, *_ = items
            if username in ['Xqbot', 'BLUbot']:
                imageID = oldid
                break

        if imageID:
            # Looking for old links'
            info = image.getOldVersion(imageID)
            regex = re.compile(
                '\{\{Dateiüberprüfung/benachrichtigt \(einzelne Verwendung\)'
                '\|(.+?)\}\}')
            linked = regex.findall(info)

        # Removing already linked pages
        for link in image.usingPages():
            found = True
            if link.title() in linked:
                linked.remove(link.title())

        if not found and not linked:
            # No old references found
            info = image.get()
            info = re.sub(
                '\[\[(?:[Cc]ategory|[Kk]ategorie):'
                'Wikipedia:Dateiüberprüfung/Verwendungsreview([\|\]])',
                '[[Kategorie:Wikipedia:Dateiüberprüfung/Verwendungsreview '
                'nötig\\1',
                info)
            self.save(
                image, info,
                'Bot: Es konnten keine Angaben zu früheren Verwendungen '
                'gefunden werden, die Abarbeitung muss manuell stattfinden.')
            return

        done = False
        for title in linked:
            pywikibot.output('Processing [[%s]]' % title)

            # TODO erst prüfen, ob Datei schon eingebunden ist

            p = pywikibot.Page(pywikibot.Site(), title)
            if not p.exists():
                with suppress(pywikibot.NoPage):
                    p = p.getMovedTarget()
            if p.isRedirectPage():
                with suppress(pywikibot.NoPage):
                    p = p.getRedirectTarget()
            if p.exists():
                if p.namespace() != 0:
                    continue
                tp = p.toggleTalkPage()
                if tp.exists():
                    talk = tp.get()
                else:
                    talk = ''
                talk += ('\n{{subst:Dateiüberprüfung (Verwendungsreview)|%s}} '
                         '~~~~' % image.title())
                if self.save(tp, talk,
                             'Bot: Der Artikel verwendete eine mittlerweile '
                             'wiederhergestellte Datei)'):
                    done = True

        if done or not linked:
            info = image.get()
            info = re.sub(
                '(?s)\{\{#ifeq:\{\{NAMESPACE\}\}\|\{\{ns:6\}\}\|.+?\[\[[^\[]+?'
                '/Verwendungsreview[^\]]*?\]\]\r?\n\}\}\r?\n?',
                '',
                info)
            # Neues Format? Kat entfernen
            info = re.sub(
                '(?s)\[\[[^\[]+?/Verwendungsreview[^\]]*?\]\](\r?\n)*',
                '',
                info)
            if not linked:
                summary = ('Bot: Datei wird bereits verwendet, '
                           'Verwendungs-Review abgeschlossen.')
            else:
                summary = ('Bot: Auf den Diskussionsseiten ehemaliger '
                           'Verwender wurde vermerkt, dass die Datei wieder '
                           'existiert.')
            print('Summary:', summary)
            self.save(image, info, summary)
        else:  # Dateiverwendung wurde gelöscht
            print('Dateiverwendung wurde gelöscht')
            # was nun:
            # teilweise Benachrichtigung
            # manuell nacharbeiten?
            # oder erledigen


def main(*args):
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    @param args: command line arguments
    @type args: list of unicode
    """
    options = {}

    # Parse command line arguments
    for arg in pywikibot.handle_args():
        option, _, value = arg.partition(':')
        if option[0] != '-':
            continue
        option = option[1:]
        if option == 'total':
            options[option] = int(value)
        else:
            options[option] = True

    if options:
        bot = CheckImageBot(**options)
        bot.run()
    else:
        pywikibot.showHelp()


if __name__ == '__main__':
    main()
