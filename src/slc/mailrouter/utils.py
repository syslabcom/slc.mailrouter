import re
import email
from datetime import datetime
from zope.component import queryUtility
from zope.interface import implements
from plone.i18n.normalizer.interfaces import IFileNameNormalizer
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import IFolderish
from slc.mailrouter.interfaces import IFriendlyNameStorage
from slc.mailrouter.interfaces import IMailRouter

UIDRE = re.compile('^[0-9a-f-]+$')

class MailToFolderRouter(object):
    implements(IMailRouter)

    def __call__(self, site, msg):
        sender = msg.get('From')
        local_part = msg.get('To').split('@')[0]
        local_part = email.Utils.parseaddr(local_part)[1]

        assert len(local_part) <= 50, "local_part must have a reasonable length"

        # Find the right context. Do that by looking up local_part
        # in our local friendly-name storage, and if not found, check
        # if it looks like a uid. Then look up the uid in the uid_catalog.
        storage = queryUtility(IFriendlyNameStorage)
        uid = storage.get(local_part, None)
        if uid is None and UIDRE.match(local_part) is not None:
            uid = local_part
        
        uidcat = getToolByName(site, 'uid_catalog')
        brains = uidcat(UID=uid)
        if not brains:
            raise ValueError("No such UID")

        context = brains[0].getObject()
        if not IFolderish.providedBy(context):
            raise ValueError("Target is not a folder")

        idnormalizer = queryUtility(IFileNameNormalizer)
        registry = getToolByName(site, 'content_type_registry')

        # Extract the various parts
        for part in msg.walk():
            if part.is_multipart():
                # Ignore the multipart container, we will eventually walk
                # through all of its contents.
                continue

            file_name = part.get_filename()
            if file_name is None:
                # This is probably inline, ignore it
                continue

            content_type = part.get_content_type()
            payload = part.get_payload(decode=1)
            type_name = registry.findTypeName(file_name, content_type, payload)

            # Normalise file_name into a safe id
            name = idnormalizer.normalize(file_name)

            # Check that the name is safe to use, else add a date to it
            if name in context.objectIds():
                parts = name.split('.')
                parts[0] += datetime.now().strftime('-%Y-%m-%d-%H-%M-%S')
                name = '.'.join(parts)

            context.invokeFactory(type_name, name)
            obj = context._getOb(name)
            obj.getPrimaryField().getMutator(obj)(payload)
            obj.setTitle(file_name)
            obj.reindexObject(idxs='Title')
            return True
        return False

    def priority(self):
        return 50
