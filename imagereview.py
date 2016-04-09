#!/usr/bin/python
# -*- coding: utf-8  -*-
#
"""
This bot script is developed for the image review processing on de-wiki.

See https://de.wikipedia.org/wiki/Wikipedia:D%C3%9CP for it

This script is run by [[de:user:xqt]].
It should not be run by other users without prior contact.

The following parameters are supported:

-always           Do not ask for writing a page, always do it

-check            Image review processing

-list             Create a list of unused files listed at
                  [[Kategorie:Wikipedia:Dateiüberprüfung/Gültige_Problemangabe]]
                  sorted by upload timestamp

-review           Look for previous usage of an image write a hint to the talk
                  page

-total:<number>   Only check the given number of files

"""
from __future__ import absolute_import, print_function, unicode_literals
#
# (C) xqt, 2012-2016
#
# Distributed under the terms of the MIT license.
#
# Automatically ported from compat branch by compat2core.py script
#
__version__ = '$Id: ad511bf05dad0151d2526eb3f1b48be67e15b440 $'
#

import copy
import re
from datetime import datetime

import pywikibot
from pywikibot import pagegenerators, textlib

remark = {
    '1923':
        u'Fehlende Nachweise bei der'
        u" '''[[Wikipedia:Bildrechte#1923|1923-Regel]]''':"
        u' Die deutschsprachige Wikipedia akzeptiert Bilder, die nachweislich'
        u' vor 1923 veröffentlicht wurden. Um eine solche Datei hier'
        u' einzustellen, sind jedoch folgende Bedingungen zu erfüllen:'
        u'\n** Du musst auf der Dateibeschreibungsseite nachweisen, dass das'
        u" Bild vor 1923 '''veröffentlicht''' wurde und dass der Urheber oder"
        u' dessen Todesdatum auch nach gründlicher Recherche nicht'
        u' herausgefunden werden kann.'
        u'\n** Du musst als Uploader eine Diskussion auf'
        u' [[Wikipedia:Dateiüberprüfung/1923]] einleiten und den Sachverhalt'
        u' und die Nachweise darlegen.',
    'Freigabe':
        u"'''Freigabe:'''"
        u' Du brauchst eine Erlaubnis, wenn du eine urheberrechtlich geschützte'
        u' Datei hochlädst. Um eine solche Erlaubnis zu formulieren, bieten wir'
        u' einen Online-Assistenten unter https://wmts.dabpunkt.eu/freigabe3/'
        u' an. Er hilft Dir, die passende Formulierung zu finden, egal ob Du'
        u' selbst der Urheber bist oder die Datei von einer anderen Person'
        u' geschaffen wurde.',
    'Gezeigtes Werk':
        u"'''Gezeigtes Werk:'''"
        u' Um ein Foto, das ein urheberrechtlich geschütztes Werk einer anderen'
        u' Person (z.&nbsp;B. ein Foto eines Plakats oder eine Nachzeichnung'
        u' eines Gemäldes) zeigt, hochzuladen brauchst du eine Erlaubnis. Bitte'
        u' den Urheber um eine solche Erlaubnis wie'
        u' [[WP:TV#Freigabe gezeigtes Werk|hier]] beschrieben. Das ist'
        u' nicht nötig, wenn sich das gezeigte Werk dauerhaft im öffentlichen'
        u' Verkehrsraum befindet (z.&nbsp;B. in einem öffentlichen Park), gib'
        u' dies auf der Dateibeschreibungsseite dann mit an.',
    'Lizenz':
        u"'''Lizenz:'''"
        u' Eine Lizenz ist die Erlaubnis, eine Datei unter bestimmten'
        u' Bedingungen zu nutzen. In der deutschsprachigen Wikipedia werden nur'
        u' solche Dateien akzeptiert, die unter einer freien Lizenz stehen,'
        u" die '''[[Wikipedia:Lizenzvorlagen für Bilder|hier]]''' gelistet"
        u' sind. Unser Online-Assistent unter'
        u' https://wmts.dabpunkt.eu/freigabe3/ hilft Dir, eine passende Lizenz'
        u' auszuwählen und den Text für Dich anzupassen. Wenn du der Urheber'
        u' der Datei oder der Inhaber der Nutzungsrechte bist, kannst Du ihn'
        u' benutzen, um den Text anschließend in die Dateibeschreibungsseite'
        u' einzufügen.',
    'Quelle':
        u"'''Quelle:'''"
        u' Hier vermerkst du, wie du zu dieser Datei gekommen bist. Das kann'
        u' z.&nbsp;B. ein Weblink sein oder – wenn du das Bild selbst gemacht'
        u' hast – die Angabe „selbst fotografiert“ bzw. „selbst gezeichnet“.',
    'Urheber':
        u"'''Urheber:'''"
        u' Der Schöpfer des Werks (z.&nbsp;B. der Fotograf oder der Zeichner).'
        u' Man wird aber keinesfalls zum Urheber, wenn man bspw. ein Foto von'
        u' einer Website nur herunterlädt oder ein Gemälde einfach'
        u' nachzeichnet! Wenn du tatsächlich der Urheber des Werks bist,'
        u' solltest du entweder deinen Benutzernamen oder deinen bürgerlichen'
        u' Namen als Urheber angeben. Im letzteren Fall muss allerdings'
        u' erkennbar sein, dass du (also %(user)s) auch diese Person bist.',
    'Hinweis':
        u"'''Hinweis%(num)s'''"
        u' durch den [[WP:DÜP|]]-Bearbeiter: %(note)s',
}

remark_mail = {
    '1923':
        u'Fehlende Nachweise bei der 1923-Regel'
        u' (https://de.wikipedia.org/wiki/Wikipedia:Bildrechte#1923):'
        u' Die deutschsprachige Wikipedia akzeptiert Bilder, die nachweislich'
        u' vor 1923 veröffentlicht wurden. Um eine solche Datei hier'
        u' einzustellen, sind jedoch folgende Bedingungen zu erfüllen:'
        u'\n- Du musst auf der Dateibeschreibungsseite nachweisen, dass das'
        u' Bild vor 1923 veröffentlicht wurde und dass der Urheber oder dessen'
        u' Todesdatum auch nach gründlicher Recherche nicht herausgefunden'
        u' werden kann.'
        u'\n- Du musst als Uploader eine Diskussion auf'
        u' https://de.wikipedia.org/wiki/Wikipedia:Dateiüberprüfung/1923'
        u' einleiten und den Sachverhalt und die Nachweise darlegen.',
    'Freigabe': remark['Freigabe'],
    'Gezeigtes Werk':
        u'Gezeigtes Werk:'
        u' Um ein Foto, das ein urheberrechtlich geschütztes Werk einer anderen'
        u' Person (z.B. ein Foto eines Plakats oder eine Nachzeichnung eines'
        u' Gemäldes) zeigt, hochzuladen brauchst du eine Erlaubnis. Bitte den'
        u' Urheber um eine solche Erlaubnis wie auf'
        u' https://de.wikipedia.org/wiki/Wikipedia:TV#Freigabe_gezeigtes_Werk'
        u' beschrieben. Das ist nicht nötig, wenn sich das gezeigte Werk'
        u' dauerhaft im öffentlichen Verkehrsraum befindet (z.B. in einem'
        u' öffentlichen Park), gib dies auf der Dateibeschreibungsseite dann'
        u' mit an.',
    'Lizenz':
        u'Lizenz:'
        u' Eine Lizenz ist die Erlaubnis, eine Datei unter bestimmten'
        u' Bedingungen zu nutzen. In der deutschsprachigen Wikipedia werden nur'
        u' solche Dateien akzeptiert, die unter einer freien Lizenz stehen, die auf'
        u' https://de.wikipedia.org/wiki/Wikipedia:Lizenzvorlagen_f%%C3%%BCr_Bilder'
        u' gelistet sind.'
        u' Unser Online-Assistent unter https://wmts.dabpunkt.eu/freigabe3/'
        u' hilft Dir, eine passende Lizenz auszuwählen und den Text für Dich'
        u' anzupassen. Wenn du der Urheber der Datei oder der Inhaber der'
        u' Nutzungsrechte bist, kannst Du ihn benutzen, um den Text'
        u' anschließend in die Dateibeschreibungsseite einzufügen.',
    'Quelle':
        u'Quelle:'
        u' Hier vermerkst du, wie du zu dieser Datei gekommen bist. Das kann'
        u' z.B. ein Weblink sein oder - wenn du das Bild selbst gemacht hast -'
        u' die Angabe "selbst fotografiert" bzw. "selbst gezeichnet".',
    'Urheber':
        u'Urheber:'
        u' Der Schöpfer des Werks (z.B. der Fotograf oder der Zeichner). Man'
        u' wird aber keinesfalls zum Urheber, wenn man bspw. ein Foto von einer'
        u' Website nur herunterlädt oder ein Gemälde einfach nachzeichnet! Wenn'
        u' du tatsächlich der Urheber des Werks bist, solltest du entweder'
        u' deinen Benutzernamen oder deinen bürgerlichen Namen als Urheber'
        u' angeben. Im letzteren Fall muss allerdings erkennbar sein, dass du'
        u' (also %(user)s) auch diese Person bist.',
    'Hinweis':
        u'Hinweis%(num)s'
        u' durch den Bearbeiter: %(note)s'
}

msg = u"""

== Problem{{PLURAL:count| mit Deiner Datei|e mit Deinen Dateien}} (%(date)s) ==

Hallo %(user)s,

bei %(the)s folgenden von dir hochgeladenen %(file)s gibt es noch %(1)sProblem%(e)s:

# %(list)s

* %(help)s

Durch Klicken auf „Bearbeiten“ oben auf %(the)s Dateibeschreibungsseite%(n)s kannst du die fehlenden Angaben nachtragen. Wenn %(2)s Problem%(e)s nicht innerhalb von 14 Tagen behoben %(be)s, %(must)s die %(file)s leider gelöscht werden.

Fragen beantwortet dir möglicherweise die [[Hilfe:FAQ zu Bildern|Bilder-FAQ]]. '''Du kannst aber auch gern hier in diesem Abschnitt antworten, damit dir individuell geholfen wird.'''

Vielen Dank für deine Unterstützung, [[Benutzer:Xqbot|Xqbot]] ([[WD:DÜP|Diskussion]]) ~~~~~
"""  # noqa

mail_msg = u"""
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

DUP_REASONS = [u'1923', u'Freigabe', 'Gezeigtes Werk', 'Lizenz', u'Quelle',
               u'Urheber', u'Hinweis']

MAX_EMAIL = 20  # version 1.21wmf10


class DUP_Image(pywikibot.FilePage):

    """FilePage holding review informations."""

    def __init__(self, site, title, text=None, timestamp=None):
        """Constructor."""
        pywikibot.ImagePage.__init__(self, site, title)
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
        TEMPL = ('DÜP', 'Düp', 'Dateiüberprüfung')
        if self._contents:
            self.done = u"3=[[Benutzer:Xqbot|Xqbot]]" in self._contents
            for tpl, param in self.templatesWithParams():
                if tpl.title(withNamespace=False) in TEMPL:
                    self.review_tpl.append(tpl)
                    for r in param:
                        if r.strip():
                            self.reasons.add(r.strip())
                elif tpl.title(withNamespace=False) == 'Information':
                    self.info = True

    @property
    def validReasons(self):
        valid = True
        if self.reasons:
            for r in self.reasons.copy():
                if r.startswith('Hinweis'):
                    self.reasons.remove(r)
                    self.reasons.add('Hinweis')
                    # r is already stripped by extract_templates_and_params
                    r, sep, self.remark = r.partition('=')
                if r not in DUP_REASONS:
                    valid = False
                    pywikibot.output(u'\nIgnoriere %s: '
                                     u'Grund %s wird nicht bearbeitet'
                                     % (self, r if r else u'(keiner angegeben)'))
                    break
        else:
            valid = False
            pywikibot.output(u'\nIgnoriere %s: kein Grund angegeben' % self)
        return valid

    @property
    def hasRefs(self):
        refs = iter(self.usingPages())
        try:
            next(refs)
        except StopIteration:
            return False
        return True


class CheckImageBot(object):

    """Bot to review uploaded Files."""

    availableOptions = {
        'list': None,    # list unreferenced Files
        'check': None,   # DÜP
        'total': None,   # total images to process
        'always': None,
        'review': None,  # check for lastUploader != firstUploader
        'touch': None,   # touch categories to actualize the time stamp
    }

    def __init__(self, **options):
        self.setOptions(**options)
        self.source = u'Wikipedia:Dateiüberprüfung/Gültige_Problemangabe'
        self.site = pywikibot.Site()
        self.total = self.getOption('total')
        self.mails = 0
        if self.getOption('list'):
            self.dest = u'Benutzer:Quedel/Datei/DÜP-Eingang'
            self.sort = 1  # timestamp
            self.summary = u'Bot: Aktualisiere unbenutzte Dateien, sortiert nach Datum'
            self.filter = True  # List unreferences Files only
        elif self.getOption('check'):
            self.dest = u'Benutzer:xqbot/DÜP-Log'
            self.sort = 0  # uploader
            self.summary = u'Bot: Aktualisiere bearbeitete Dateien, sortiert nach Uploader'
            self.filter = False
        elif self.getOption('review'):
            pass
        elif self.getOption('touch'):
            pass
        else:
            raise NotImplementedError('Invalid option')

    def setOptions(self, **kwargs):
        """Set the instance options."""
        # contains the options overriden from defaults
        self.options = {}

        validOptions = set(self.availableOptions)
        receivedOptions = set(kwargs)

        for opt in receivedOptions & validOptions:
            self.options[opt] = kwargs[opt]

        for opt in receivedOptions - validOptions:
            pywikibot.output(u'%s is not a valid option. It was ignored.'
                             % opt)

    def getOption(self, option):
        """
        Get the current value of an option.

        @param option: key defined in Bot.availableOptions
        """
        try:
            return self.options.get(option, self.availableOptions[option])
        except KeyError:
            raise pywikibot.output(u'%s is not a valid bot option.' % option)

    def hasRefs(self, image):
        refs = image.usingPages()
        i = 0
        for ref in refs:
            i += 1
            break
        return i > 0

    @property
    def generator(self):
        cat = pywikibot.Category(self.site,
                                 "%s:%s"
                                 % (self.site.category_namespace(),
                                    self.source))
        gen = pagegenerators.CategorizedPageGenerator(cat)
        gen = pagegenerators.NamespaceFilterPageGenerator(
            gen, self.site.image_namespace())
        if not self.filter:
            gen = pagegenerators.PreloadingGenerator(gen)
        # gen = pagegenerators.ImageGenerator(gen)
        for item in gen:
            page = DUP_Image(item.site, item.title(),
                             not self.filter and item.get() or None,
                             item.editTime())
            if self.filter and page.hasRefs:
                continue
            if not self.filter and not page.validReasons:
                continue
            yield page

    def save(self, page, newText, summary=None):
        """Save the page to the wiki, if the user accepts the changes made."""
        done = False
        try:
            oldtext = page.get()
        except pywikibot.NoPage:
            oldtext = u''
        if oldtext == newText:
            pywikibot.output(u'No changes were needed on %s'
                             % page.title(asLink=True))
            return

        pywikibot.output(u"\n\n>>> \03{lightpurple}%s\03{default} <<<"
                         % page.title())
        pywikibot.showDiff(oldtext, newText)

        choice = 'a'
        if not self.getOption('always'):
            choice = pywikibot.inputChoice(
                u'Do you want to accept these changes?',
                ['Yes', 'No', 'Always yes'], ['y', 'N', 'a'], 'N')
            if choice == 'n':
                return
            elif choice == 'a':
                self.options['always'] = True

        try:
            page.put(newText, summary or self.summary,
                     minorEdit=page.namespace() != 3)
        except pywikibot.EditConflict:
            pywikibot.output(u'Skipping %s because of edit conflict'
                             % (page.title(),))
        except pywikibot.SpamfilterError as e:
            pywikibot.output(
                u'Cannot change %s because of blacklist entry %s'
                % (page.title(), e.url))
        except pywikibot.LockedPage:
            pywikibot.output(u'Skipping %s (locked page)' % (page.title(),))
        else:
            done = True
        return done

    def inform_user(self, user, data):
        """
        Inform user.

        data = [title(asLink=True),
                    [user, timestamp],
                    DUP_Image{},
                    <leer|reasons>,
        ]
        """
        # verstorbene
        ignoreUser = set()
        ignorePage = pywikibot.Page(
            self.site,
            'Wikipedia:Gedenkseite für verstorbene Wikipedianer')
        for p in ignorePage.linkedPages():
            if p.namespace() == 2:
                ignoreUser.add(p.title(withNamespace=False).split('/')[0])
        where = u''
        images = []
        problems = set()
        hints = {}
        k = 0
        for a in data:
            image = copy.copy(a[2])
            images.append(image)
            reasons = image.reasons
##            a[3] = u', '.join(reasons)
##            a[3] = u"%s - '''Problem%s''': %s" \
##                   % (a[0], u'e' if len(reasons) != 1 else u'', a[3])
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
            hint_str = u', Hinweis'
        else:
            hint_str = u', Hinweis %(num)d'

        param = {}
        param['user'] = user
        param['e'], param['1'], param['2'], param['be'] = (
            'e', u'', 'die', 'werden') \
            if len(problems) != 1 else (u'', u'ein ', 'das', 'wird')
        param['list'] = u'\n# '.join([u"%s - '''Problem%s''': %s%s"
                                      % (a[0],
                                         u'e' if len(a[3][0]) != 1 else u'',
                                         u', '.join(sorted(a[3][0])),
                                         hint_str % {'num': a[3][1]}
                                         if a[3][1] > 0 else u'')
                                      for a in data])

        param['help'] = u'\n* '.join(remark[r] % {'user': user}
                                     for r in sorted(problems))
        for num in sorted(hints):
            param['help'] += u'\n* ' + remark['Hinweis'] % {'note': hints[num],
                                                            'num': u' %d' % num
                                                            if len(hints) > 1
                                                            else u''}
        param['date'] = datetime.now().strftime('%d.%m.%Y')
        param['count'] = len(data)
        if len(data) != 1:
            param['file'] = u'Dateien'
            param['the'] = u'den'
            param['n'] = u'n'
            param['must'] = u'müssen'
        else:
            param['file'] = u'Datei'
            param['the'] = u'der'
            param['n'] = u''
            param['must'] = u'muss'

        if user in ignoreUser:
            pywikibot.output(u'%s was ignored (inactive).' % user)
            where = u'Verstorben'
        else:
            # auf BD benachrichtigen
            up = pywikibot.Page(self.site, user, defaultNamespace=3)
            # Weiterleitungen folgen, evtl. Namensänderung
            while up.isRedirectPage():
                up = up.getRedirectTarget()
            title = up.title(withNamespace=False)
            if '/' in title:
                up = pywikibot.Page(self.site, title.split('/', 1),
                                    defaultNamespace=3)
            if up.namespace() == 3:
                upm = pywikibot.User(self.site, up.title(withNamespace=False))
                if upm.isRegistered():
                    try:
                        text = up.get()
                    except pywikibot.NoPage:
                        text = u''
                    text += pywikibot.translate('de', msg, param)
                    if self.save(up,
                                 text,
                                 summary=u'Bot: Neue Nachricht von der [[WP:DÜP|DÜP]]'):
                        where = 'Disk'
            else:
                upm = pywikibot.User(self.site, user)

            upm = pywikibot.User(self.site, user)

            # per Mail benachrichtigen
            if upm.isRegistered() and upm.isEmailable():
                pywikibot.output(u'%s has mail enabled.' % user)
                param['list'] = u'\r\n# '.join(
                    [u"https://de.wikipedia.org/wiki/%s - Problem%s: %s%s"
                     % (a[2].title(asUrl=True), u'e' if len(a[3][0]) != 1 else u'',
                        u', '.join(sorted(a[3][0])),
                        hint_str % {'num': a[3][1]}
                        if a[3][1] > 0 else u'')
                     for a in data])
                param['help'] = u'\n* '.join(remark_mail[r] % {'user': user}
                                             for r in sorted(problems))
                for num in sorted(hints):
                    param['help'] += u'\n* ' + remark_mail['Hinweis'] \
                                     % {'note': hints[num],
                                        'num': u' %d' % num
                                        if len(hints) > 1 else u''}

                text = mail_msg % param
                # upm = pywikibot.User(self.site, u'Xqt')
                pywikibot.output(text)
                if upm.sendMail(subject=u'Bot: Neue Nachricht von der Wikipedia-Dateiüberprüfung an %s'
                                % user,
                                text=text):
                    self.mails += 1
                    if where:
                        where += u'+Mail'
                    else:
                        where = u'Mail'
            else:
                pywikibot.output(u'%s has mail disabled.' % user)

        if not where:
            where = 'Unbekannt' if not upm.isRegistered() else 'Gar nicht'

        # jetzt alle Dateien eines Benutzers bearbeiten
        for i in images:
            tmpl = i.review_tpl
            if not tmpl:
                print('template nicht gefunden für', i.title())
                continue
            summary = u'Bot: Benutzer %s, Vorlage umgeschrieben' \
                      % (u'konnte nicht benachrichtigt werden'
                         if where in ['Gar nicht',
                                      'Verstorben',
                                      'Unbekannt'] else u'benachrichtigt')
            text = i.get()
            if self.getOption('check'):
                if i.hasRefs:
                    inline = u'\n{{Dateiüberprüfung/benachrichtigt (Verwendung)|~~~~~|'
                    for ref in i.usingPages():
                        inline += u'\n{{Dateiüberprüfung/benachrichtigt (einzelne Verwendung)|%s}}' % ref.title()
                    inline += u'\n}}'
                else:
                    inline = u''
                if not i.info:
                    summary += u', Vorlage:Information ergänzt'
                    inline += """
{{Information
|Beschreibung     =
|Quelle           =
|Urheber          =
|Datum            =
|Genehmigung      =
|Andere Versionen =
|Anmerkungen      =
}}
"""  # noqa
                firstTmpl = tmpl.pop(0)
                if 'Hinweis' in i.reasons:
                    i.reasons.remove('Hinweis')
                reasons = '|'.join(sorted(i.reasons))
                if i.remark:
                    reasons += '|7=Hinweis=%s' % i.remark
                text = re.sub(u'(?is)\{\{%s *\|(.*?)\}\}' % firstTmpl,
                              u'{{Dateiüberprüfung/benachrichtigt (Vermerk)|%s|%s|3=~~~~}}\n'
                              u'{{subst:Dateiüberprüfung/benachrichtigt|%s}}%s' % (user, where, reasons, inline),
                              text)
                if tmpl:  # verbliebene Templates löschen
                    text = re.sub(u'(?i)\{\{(%s)[^/\{]*?\}\}' % u'|'.join(tmpl),
                                  u'', text)
            self.save(i, text, summary=summary)
        return True  # returns klären!!!

    def build_table(self, save=True, unittest=False):

        def f(k):
            r = 0
            if k not in table:
                print(k, 'fehlt')
                return r
            try:
                r = int(table[k][0][2].editTime().totimestampformat())
            except IndexError:
                print(k)
                print(table[k][0])
                r = 0
            return r

        table = {}
        informed = []
        if self.getOption('check'):
            pywikibot.output(u'Processing %d images...' % self.total)
        for image in self.generator:
            uploader = image.getFirstUploader()
            sortkey = uploader[self.sort]
            if sortkey not in table:
                table[sortkey] = []
            table[sortkey].append([image.title(asLink=True, textlink=True),
                                  uploader, image, u''])
        pywikibot.output(u'\nBuilding wiki table...')
        keys = list(table.keys())  # py3 compatibility
        if self.getOption('list'):
            keys.sort()
        else:
            # keys.sort(key=lambda k: int(table[k][2].editTime()))
            keys.sort(key=f)
        text = u'''
{| class="wikitable sortable"
|-
! Datei || Uploader || Zeitstempel
|-
'''
        if self.getOption('check'):
            cat = pywikibot.Page(self.site, self.cat, defaultNamespace=14)
            try:
                cattext = cat.get()
            except pywikibot.NoPage:
                cattext = u"""{{Dateiüberprüfung (Abarbeitungsstatus)
|Frühzeitig abgebrochen bei=
|Unterschrift=
|Fertig geworden=
|Kategoriebezeichnung=%s
}}
__NOTOC____NOEDITSECTION__
<br style="clear:both;" />
""" % datetime.now().strftime('%Y-%m-%d')
        oneDone = False
        if self.getOption('check'):
            k = 0
            for key in keys:
                l = len(table[key])
                if self.total and k + l > self.total and oneDone:
                    if l == 1:
                        pywikibot.output(u'Max limit %d exceeded.' % self.total)
                        break
                    continue
                if not unittest and self.inform_user(key, table[key]):
                    pywikibot.output(u'%s done.' % key)
                    informed.append(key)
                    k += l
                    # cattext += u'\n== [[Benutzer:%s|]] ==\n\n' % key
                else:
                    pywikibot.output(u'%s ignored.' % key)
                    continue
                oneDone = True
                if self.mails >= MAX_EMAIL:
                    print(self.mails, 'exceeded')
                    break
            print(k, 'files processed', self.mails, 'sent')
            # jetzt wieder sortieren und (leider) erneuten Druchlauf
            informed.sort()
            keys = informed
        for key in keys:
            if self.getOption('check'):
##                cattext += u'\n== [[Benutzer:%s|]] ==\n\n' % key
                cattext = self.add_uploader_info(cattext, key, table[key])
            for a in table[key]:
##                if self.getOption('check'):
##                    cattext += u'{{Dateiüberprüfung (Liste)|1=%s|2=%s}}\n' \
##                               % (a[2].title(), key)
                text += u'| %s || [[Benutzer:%s]] || %s \n|- \n' % (
                    a[0], a[1][0], a[1][1])
        text += u'|}'
        if save:
            if self.getOption('check'):
                self.save(cat, cattext, summary=u'Bot: Neue DÜP-Einträge')
            self.save(pywikibot.Page(self.site, self.dest), text)
        return table

    def run_check(self):
        MAX = 500
        if self.getOption('check'):
            # Anzahl der Dateien ermitteln.
            # Wert ist 500 abzgl. vorhandene, aber höchstens 30
            if not self.total:
                cat = pywikibot.Category(
                    self.site, "%s:%s"
                    % (self.site.category_namespace(),
                       u'Wikipedia:Dateiüberprüfung '
                       u'(Tageskategorien, aktuell)'))
                i = 0
                for a in cat.articles(recurse=True):
                    i += 1
                    if i > MAX:
                        break
                self.total = min(30, (max(20, MAX - i)))
        self.build_table(True)

    def run_touch(self):
        # Alle zukünftigen touchen
        cat = pywikibot.Category(self.site,
                                 "%s:%s" % (self.site.category_namespace(),
                                            self.cat))
        gen = pagegenerators.SubCategoriesPageGenerator(cat)
        gen = pagegenerators.PreloadingGenerator(gen)
        for c in gen:
            self.touch(c)

    def run_review(self):
        from pywikibot import config
        config.cosmetic_changes = False
        cat = pywikibot.Category(self.site, "%s:%s"
                                 % (self.site.category_namespace(), self.cat))
        gen = cat.articles()
        gen = pagegenerators.NamespaceFilterPageGenerator(gen, 'File')
        for image in gen:
            self.review(image)

    def run(self):
        if self.getOption('review'):
            self.cat = u'Wikipedia:Dateiüberprüfung/Verwendungsreview'
            self.run_review()
        if self.getOption('touch'):
            self.cat = u'Wikipedia:Dateiüberprüfung (Tageskategorien, zukünftig)'
            self.run_touch()
        if self.getOption('check') or self.getOption('list'):
            self.cat = u'Kategorie:Wikipedia:Dateiüberprüfung (%s)' \
                       % datetime.now().strftime('%Y-%m-%d')
            self.run_check()

    def touch(self, cat):
        cattext = cat.get()
        table = {}
        change = False
        for image in cat.articles():
            if not image.isImage() or image.title() in cattext:
                continue
            pywikibot.output(u'File %s is not listed' % image.title())
            uploader = image.getFirstUploader()[0]
            if uploader not in table:
                table[uploader] = []
            table[uploader].append(image)
        for key in table:
            if textlib.does_text_contain_section(cattext, u'\[\[%s\]\]' % key):
                newcattext = re.sub('(== \[\[%s\]\] ==.*?)\r?\n\r?\n== \[\['
                                    % key,
                                    '\1' + '######', cattext)
                print(newcattext)
                pass  # TODO: Ergänze bei vorhandenem Uploader
            else:
                pywikibot.output(u'Uploader %s is not listed' % key)
                cattext = self.add_uploader_info(cattext, key, table[key])
                change = True
        if change:
            self.save(cat, cattext, u'Bot: Ergänze Dateien mit Aufschub')
        else:
            cat.put(cattext)

    def add_uploader_info(self, text, uploader, images):
        text += u'\n== [[Benutzer:%s|]] ==\n\n' % uploader
        for image in images:
            if isinstance(image, pywikibot.Page) and image.isImage():
                title = image.title()
            else:  # from buildtable
                title = image[2].title()
            text += (u'{{Dateiüberprüfung (Liste)|1=%s|2=%s}}\n'
                     % (title, uploader))
        return text

    def review(self, image):
        """Check whether page was transcluded previously."""
        imageID = None
        linked = []
        found = False
        vh = image.getVersionHistory()
        # Search for last bot action
        for oldid, time, username, summary, size, tags in vh:
            if username in [u'Xqbot', u'BLUbot']:
                imageID = oldid
                break

        if imageID:
            # Looking for old links'
            info = image.getOldVersion(imageID)
            regex = re.compile(
                u'\{\{Dateiüberprüfung/benachrichtigt \(einzelne Verwendung\)'
                u'\|(.+?)\}\}')
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
                u'\[\[(?:[Cc]ategory|[Kk]ategorie):'
                u'Wikipedia:Dateiüberprüfung/Verwendungsreview([\|\]])',
                u'[[Kategorie:Wikipedia:Dateiüberprüfung/Verwendungsreview '
                u'nötig\\1',
                info)
            self.save(
                image, info,
                u'Bot: Es konnten keine Angaben zu früheren Verwendungen '
                u'gefunden werden, die Abarbeitung muss manuell stattfinden.')
            return

        done = False
        for title in linked:
            pywikibot.output(u'Processing [[%s]]' % title)

            # TODO erst prüfen, ob Datei schon eingebunden ist

            p = pywikibot.Page(pywikibot.Site(), title)
            if not p.exists():
                try:
                    p = p.getMovedTarget()
                except pywikibot.NoPage:
                    pass
            if p.isRedirectPage():
                try:
                    p = p.getRedirectTarget()
                except pywikibot.NoPage:
                    pass
            if p.exists():
                if p.namespace() != 0:
                    continue
                tp = p.toggleTalkPage()
                if tp.exists():
                    talk = tp.get()
                else:
                    talk = u''
                talk += u'\n{{subst:Dateiüberprüfung (Verwendungsreview)|%s}} ~~~~' % image.title()
                if self.save(tp, talk,
                             u'Bot: Der Artikel verwendete eine mittlerweile '
                             u'wiederhergestellte Datei)'):
                    done = True

        if done or not linked:
            info = image.get()
            info = re.sub(
                u'(?s)\{\{#ifeq:\{\{NAMESPACE\}\}\|\{\{ns:6\}\}\|.+?\[\[[^\[]+?/Verwendungsreview[^\]]*?\]\]\r?\n\}\}\r?\n?',
                u'',
                info)
            # Neues Format? Kat entfernen
            info = re.sub(
                u'(?s)\[\[[^\[]+?/Verwendungsreview[^\]]*?\]\](\r?\n)*',
                u'',
                info)
            if not linked:
                summary = u'Bot: Datei wird bereits verwendet, Verwendungs-Review abgeschlossen.'
            else:
                summary = u'Bot: Auf den Diskussionsseiten ehemaliger Verwender wurde vermerkt, dass die Datei wieder existiert.'
            print('Summary:', summary)
            self.save(image, info, summary)
        else:  # Dateiverwendung wurde gelöscht
            print('Dateiverwendung wurde gelöscht')
            # was nun:
            # teilweise Benachrichtigung
            # manuell nacharbeiten?
            # oder erledigen
            pass


def main(*args):
    options = {}

    # Parse command line arguments
    for arg in pywikibot.handleArgs():
        if arg.startswith('-total'):
            options['total'] = int(arg[len('-total:'):])
        else:
            options[arg[1:].lower()] = True

    if options:
        bot = CheckImageBot(**options)
        bot.run()
    else:
        pywikibot.showHelp()

if __name__ == "__main__":
    main()
