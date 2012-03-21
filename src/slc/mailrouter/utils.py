import re
import email
from datetime import datetime
from AccessControl.SecurityManagement import newSecurityManager, \
    noSecurityManager
from zope.component import queryUtility
from zope.interface import implements
from plone.i18n.normalizer.interfaces import IFileNameNormalizer
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import IFolderish
from Products.CMFCore.permissions import AddPortalContent
from slc.mailrouter.interfaces import IFriendlyNameStorage
from slc.mailrouter.interfaces import IMailRouter
from slc.mailrouter.exceptions import PermissionError, NotFoundError, ConfigurationError
from slc.mailrouter.exceptions import ConfigurationError
from slc.mailrouter import MessageFactory as _

UIDRE = re.compile('^[0-9a-f-]+$')

class MailToFolderRouter(object):
    implements(IMailRouter)

    def __call__(self, site, msg):
        sender = msg.get('From')
        sender = email.Utils.parseaddr(sender)[1]
        local_part = email.Utils.parseaddr(msg.get('To'))[1]
        local_part = local_part.split('@')[0]

        assert len(local_part) <= 50, "local_part must have a reasonable length"

        # Find the right context. Do that by looking up local_part
        # in our local friendly-name storage, and if not found, check
        # if it looks like a uid. Then look up the uid in the uid_catalog.
        storage = queryUtility(IFriendlyNameStorage)
        uid = storage.get(local_part, None)
        if uid is None and UIDRE.match(local_part) is not None:
            uid = local_part

        if uid is None:
            # local_part is not a uid and is not mapped onto a folder,
            # this is not something we can handle.
            return False
        
        uidcat = getToolByName(site, 'uid_catalog')
        brains = uidcat(UID=uid)
        if not brains:
            raise NotFoundError(_("Folder not found"))

        context = brains[0].getObject()
        if not IFolderish.providedBy(context):
            raise NotFoundError(_("Target is not a folder"))

        idnormalizer = queryUtility(IFileNameNormalizer)
        registry = getToolByName(site, 'content_type_registry')

        result = False

        # Drop privileges to the right user
        pm = getToolByName(site, 'portal_membership')
        try:
            user_id = pm.searchMembers('email', sender)[0]['username']
        except IndexError:
            raise NotFoundError(_("Sender is not a valid user"))

        acl_users = getToolByName(site, 'acl_users')
        user = acl_users.getUser(user_id)
        newSecurityManager(None, user.__of__(acl_users))

        # Check permissions
        if not user.has_permission(AddPortalContent, context):
            raise PermissionError(_("Insufficient privileges"))

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
            result = True

        noSecurityManager()
        return result

    def priority(self):
        return 50

class MailToGroupRouter(object):
    implements(IMailRouter)

    def _findGroup(self, site, local_part):
        groups_tool = getToolByName(site, 'portal_groups')
        group = groups_tool.getGroupById(local_part)
        if not group:
            pat = re.compile('^%s$' % local_part, re.I) # ignore case
            candidates = filter(lambda g: pat.match(g), groups_tool.getGroupIds())
            if len(candidates) > 1:
                raise ConfigurationError('Group name "%s" is not unique' % local_part)
        if not group and not candidates:
            return None

        if not group and candidates:
            group = groups_tool.getGroupById(candidates[0])
        return group


    def __call__(self, site, msg):
        sender = msg.get('From')
        sender = email.Utils.parseaddr(sender)[1]
        local_part = email.Utils.parseaddr(msg.get('To'))[1]
        local_part = local_part.split('@')[0]

        assert len(local_part) <= 50, "local_part must have a reasonable length"

        # Find the group
        group = self._findGroup(site, local_part)
        if not group:
            # local_part not a group, we're not handlig this msg
            return False

        # Drop privileges to the right user
        pm = getToolByName(site, 'portal_membership')
        try:
            user_id = pm.searchMembers('email', sender)[0]['username']
        except IndexError:
            raise NotFoundError(_("Sender is not a valid user"))

        acl_users = getToolByName(site, 'acl_users')
        user = acl_users.getUser(user_id)
        newSecurityManager(None, user.__of__(acl_users))

        # get members and send messages
        members = group.getGroupMembers()
        
        bcc = ', '.join([mmbr.getProperty('email') for mmbr in members])
        msg.add_header('BCC', bcc)
            
        for mmbr in members:
            site.MailHost.send(msg, mto=mmbr.getProperty('email'))

        return True

    def priority(self):
        return 30
