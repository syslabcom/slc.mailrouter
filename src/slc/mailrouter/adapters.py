from datetime import datetime
from zope.component import adapts, queryUtility
from plone.i18n.normalizer.interfaces import IFileNameNormalizer
from plone.rfc822.interfaces import IPrimaryFieldInfo
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import IFolderish


class FolderAdapter(object):
    adapts(IFolderish)

    def __init__(self, context):
        self.context = context
        self.normalizer = queryUtility(IFileNameNormalizer)
        self.registry = getToolByName(context, 'content_type_registry')

    def add(self, message):
        # Extract the various parts
        for part in message.walk():
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
            type_name = self.registry.findTypeName(
                file_name,
                content_type,
                payload)

            # Normalise file_name into a safe id
            name = self.normalizer.normalize(file_name)

            # Check that the name is safe to use, else add a date to it
            if name in self.context.objectIds():
                parts = name.split('.')
                parts[0] += datetime.now().strftime('-%Y-%m-%d-%H-%M-%S')
                name = '.'.join(parts)

            self.context.invokeFactory(type_name, name)
            obj = self.context._getOb(name)
            info = IPrimaryFieldInfo(obj, None)
            if info is not None:
                info.field.set(obj, payload)
            else:
                if hasattr(obj, 'getPrimaryField'):
                    obj.getPrimaryField().getMutator(obj)(payload)
                else:
                    raise AttributeError('Could not get primary field')
            obj.setTitle(file_name)
            obj.reindexObject(idxs='Title')
            return True
