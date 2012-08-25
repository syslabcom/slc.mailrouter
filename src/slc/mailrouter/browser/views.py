import email
from Acquisition import aq_inner
from zope.component import queryUtility, getAllUtilitiesRegisteredFor
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFPlone.PloneBatch import Batch
from Products.statusmessages.interfaces import IStatusMessage
from Products.CMFCore.interfaces import IFolderish
from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.permissions import AddPortalContent
from plone.uuid.interfaces import IUUID
from slc.mailrouter.interfaces import IFriendlyNameStorage
from slc.mailrouter.interfaces import IMailRouter
from slc.mailrouter.exceptions import PermanentError, TemporaryError
from slc.mailrouter import MessageFactory as _
from tempfile import NamedTemporaryFile
from logging import getLogger

logger = getLogger('slc.mailrouter.browser')

class InjectionView(BrowserView):
    def __call__(self):
        self.request.stdin.seek(0)
        msg = email.message_from_file(self.request.stdin)

        # Get all registered mail routers. Sort by priority, then
        # call them until it is handled
        routers = getAllUtilitiesRegisteredFor(IMailRouter)
        routers.sort(lambda x,y: cmp(x.priority(), y.priority()))
        for router in routers:
            try:
                if router(aq_inner(self.context), msg):
                    return 'OK: Message accepted'
            except (PermanentError, TemporaryError), e:
                self.request.response.setStatus(e.status)
                self.dump_mail()
                logger.warn(','.join(e.args))
                return 'Fail: %s' % ','.join(e.args)
            except Exception, e:
                #raise
                self.request.response.setStatus(500, reason=','.join(e.args))
                self.dump_mail()
                logger.error(','.join(e.args))
                return 'Fail: %s' % ','.join(e.args)

        self.request.response.setStatus(404)
        logger.warn('FAIL: Recipient address %s not found' % \
                (msg.get('X-Original-To') or msg.get('To')))
        return 'FAIL: Recipient address %s not found' % \
                (msg.get('X-Original-To') or msg.get('To'))

    def dump_mail(self):
        tmpfile = NamedTemporaryFile(prefix='mailrouter-dump', delete=False)
        self.request.stdin.seek(0)
        tmpfile.write(self.request.stdin.read())
        logger.info('Dumped mail to %s' % tmpfile.name)
        tmpfile.close()

class FriendlyNameStorageView(BrowserView):
    def update(self):
        """ Called from the template, it deletes any mappings
            specified on the request. """
        remove = self.request.get('remove', ())
        storages = [queryUtility(IFriendlyNameStorage),
                   ]
        for item in remove:
            for storage in storages:
                storage.remove(item)

    def folder_mappings(self):
        storage = queryUtility(IFriendlyNameStorage)
        b_size = int(self.request.get('b_size', 50))
        b_start = int(self.request.get('b_start', 0))
        return Batch(storage, b_size, b_start)

class FriendlyNameAddView(BrowserView):
    addtemplate = ViewPageTemplateFile("add.pt")

    def __call__(self):
        errors = {}
        storage = queryUtility(IFriendlyNameStorage)
        if self.request.get('form.submitted', None) is not None:
            name = self.request.get('name', '')
            target = IUUID(self.context)
            if not name:
                errors.update(
                    {'name': _(u'You must provide a friendly name.')})
            if not errors:
                existing = storage.get(name)
                if existing and not existing == target:
                    errors.update(
                        {'name': _(u'This name is already in use.')})
                else:
                    storage.remove(target) # No effect if target isn't mapped
                    storage.add(target, name)
                    IStatusMessage(self.request).add(_(u"Mail route enabled."))

        self.request['errors'] = errors
        if not errors and self.request.has_key('redirect'):
            return self.request.RESPONSE.redirect(self.request['redirect'])
        return self.addtemplate()

    def friendlyname(self):
        storage = queryUtility(IFriendlyNameStorage)
        return storage.lookup(IUUID(self.context))

    def displayMailTab(self):
        # Cannot mail into the portal root
        if self.context.restrictedTraverse(
            '@@plone_context_state').is_portal_root():
            return False
        return IFolderish.providedBy(self.context) and \
            _checkPermission(AddPortalContent, self.context)
