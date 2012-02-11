import email
from zope.component import queryUtility
from plone.i18n.normalizer.interfaces import IIDNormalizer
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView

class InjectionView(BrowserView):
    def __call__(self):
        self.request.stdin.seek(0)
        msg = email.message_from_file(self.request.stdin)
        sender = msg.get('From')
        local_part = msg.get('To').split('@')[0]

        # Extract the various parts
        import pdb; pdb.set_trace()
        registry = getToolByName(self.context, 'content_type_registry')
        for part in msg.walk():
            if part.is_multipart():
                continue

            # TODO much later, take the bit after this, refactor it into
            # utilities, so we can look up utilities that handle incoming
            # mail, and pass it to each one in turn until one accepts it,
            # exim router style.

            file_name = part.get_filename()
            if file_name is None:
                # This is probably inline, ignore it
                continue

            content_type = part.get_content_type()
            payload = part.get_payload(decode=1)
            type_name = registry.findTypeName(file_name, content_type, payload)

            # Normalise file_name into a safe id
            idnormalizer = queryUtility(IIDNormalizer)
            name = idnormalizer.normalize(file_name)

            # TODO: find the right context. Do that by looking up local_part
            # in our local friendly-name storage, and if not found, then
            # in the uid catalog (if it is hexadecimal and of the right
            # length).
            self.context.invokeFactory(type_name, name)
            obj = context._getOb(name)
            obj.PUT(self.request, self.request.response)
            obj.setTitle(file_name)
            obj.reindexObject(idxs='Title')

        return sender
