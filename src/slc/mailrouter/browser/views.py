import email
from Acquisition import aq_inner
from zope.component import queryUtility, getAllUtilitiesRegisteredFor
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFPlone.PloneBatch import Batch
from slc.mailrouter.interfaces import IFriendlyNameStorage
from slc.mailrouter.interfaces import IMailRouter

class InjectionView(BrowserView):
    def __call__(self):
        self.request.stdin.seek(0)
        msg = email.message_from_file(self.request.stdin)

        # Get all registered mail routers. Sort by priority, then
        # call them until it is handled
        routers = getAllUtilitiesRegisteredFor(IMailRouter)
        routers.sort(lambda x,y: cmp(x.priority(), y.priority()))
        for router in routers:
            if router(aq_inner(self.context), msg):
                return 'OK'

        return 'FAIL'

class FriendlyNameStorageView(BrowserView):
    def update(self):
        """ Called from the template, it deletes any mappings
            specified on the request. """
        remove = self.request.get('remove', ())
        storage = queryUtility(IFriendlyNameStorage)
        for item in remove:
            storage.remove(item)

    def mappings(self):
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
            target = self.request.get('target', '')
            if not name:
                errors.update(
                    {'name': _(u'You must provide a friendly name.')})
            if not target:
                errors.update({'target': _(u'You must provide a target.')})
            if not errors:
                if storage.get(name):
                    errors.update(
                        {'name': _(u'This name is already in use.')})
                else:
                    storage.add(target, name)
                    self.request.response.redirect(
                        '%s/@@manage-mailrouter' % self.context.absolute_url())
                    return ''

        self.request['errors'] = errors
        return self.addtemplate()
