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
from slc.mailrouter.interfaces import IFriendlyNameStorage, IGroupAliasStorage
from slc.mailrouter.interfaces import IMailRouter

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
            raise ValueError("No such UID")
            return False

        context = brains[0].getObject()
        if not IFolderish.providedBy(context):
            raise ValueError("Target is not a folder")

        idnormalizer = queryUtility(IFileNameNormalizer)
        registry = getToolByName(site, 'content_type_registry')

        result = False

        # Drop privileges to the right user
        pm = getToolByName(site, 'portal_membership')
        try:
            user_id = pm.searchMembers('email', sender)[0]['username']
        except IndexError:
            raise ValueError("Sender is not a member")

        acl_users = getToolByName(site, 'acl_users')
        user = acl_users.getUser(user_id)
        newSecurityManager(None, user.__of__(acl_users))

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

    def __call__(self, site, msg):
        sender = msg.get('From')
        sender = email.Utils.parseaddr(sender)[1]
        local_part = email.Utils.parseaddr(msg.get('To'))[1]
        local_part = local_part.split('@')[0]

        assert len(local_part) <= 50, "local_part must have a reasonable length"

        # Look up the name
        storage = queryUtility(IGroupAliasStorage)
        group_name = storage.lookup(local_part, None)
        if not group_name:
            group_name = local_part

        # Find the group
        groups_tool = getToolByName(site, 'portal_groups')
        group = groups_tool.getGroupById(group_name)
        if not group:
            pat = re.compile(group_name, re.I) # ignore case
            candidates = map(lambda g: pat.match(g), groups_tool.getGroupIds())
            candidates = filter(lambda g: g is not None, candidates)
            if len(candidates) > 1:
                raise ValueError('Group name "%s" is not unique' % group_name)
        if not group and not candidates:
            if not local_part == group_name:
                # local_part is an alias, but the group that it points to does not exist. Something is wrong
                raise ValueError('Name "%s" is an alias, but the referenced group "%s" does not exist' % (local_part, group_name))
            else:
                # local_part not a group, we're not handlig this msg
                return False

        if not group and candidates:
            group = groups_tool.getGroupById(candidates[0].group())

        # Drop privileges to the right user
        pm = getToolByName(site, 'portal_membership')
        try:
            user_id = pm.searchMembers('email', sender)[0]['username']
        except IndexError:
            raise ValueError("Sender is not a member")

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
        return 40
