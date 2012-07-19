import re
import email
from AccessControl.SecurityManagement import newSecurityManager, \
    noSecurityManager, getSecurityManager
from zope.component import queryUtility
from zope.interface import implements
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import IFolderish
from Products.CMFCore.permissions import AddPortalContent
from plone.dexterity.interfaces import IDexterityContainer
from slc.mailrouter.interfaces import IFriendlyNameStorage
from slc.mailrouter.interfaces import IMailRouter, IMailImportAdapter
from slc.mailrouter.exceptions import PermissionError, NotFoundError, ConfigurationError
from slc.mailrouter.exceptions import ConfigurationError
from slc.mailrouter import MessageFactory as _
from logging import getLogger

logger = getLogger('slc.mailrouter.utils')

UIDRE = re.compile('^[0-9a-f-]+$')

class MailToFolderRouter(object):
    implements(IMailRouter)

    def __call__(self, site, msg):
        sender = msg.get('From')
        sender = email.Utils.parseaddr(sender)[1]
        if 'X-Original-To' in msg:
            header = 'X-Original-To'
        else:
            header = 'To'
        local_part = email.Utils.parseaddr(msg.get(header))[1]
        logger.info('MailToFolderRouter called with mail from %s to %s' % (sender, local_part))
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
            raise NotFoundError(_("Target %s is not a folder" % context.getId()))

        result = False

        # Drop privileges to the right user
        pm = getToolByName(site, 'portal_membership')

        # WARNING: Assuming login happens through email
        # Todo: Check / amend this
        try:
            #user_id = pm.searchMembers('email', sender)[0]['username']
            user = pm.getMemberById(sender).getUser()
        except (IndexError, AttributeError):
            raise PermissionError(_("%s is not a permitted sender address" % sender))
        #user = pm.getMemberById(user_id).getUser()

        self.acl_users = getToolByName(site, 'acl_users')
        newSecurityManager(None, user.__of__(self.acl_users))

        # Check permissions
        if not getSecurityManager().checkPermission('Add portal content', context):
            raise PermissionError(_("%s has insufficient privileges on %s" % (sender, context.getId())))

        # Defer actual work to an adapter
        result = IMailImportAdapter(context).add(msg)

        return result

    def priority(self):
        return 50

class MailToGroupRouter(object):
    implements(IMailRouter)

    def _findGroup(self, site, recipient):
        local_part = recipient.split('@')[0]

        assert len(local_part) <= 50, "local_part must have a reasonable length"

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
        self.acl_users = getToolByName(site, 'acl_users')

        sender = msg.get('From')
        sender = email.Utils.parseaddr(sender)[1]
        if 'X-Original-To' in msg:
            header = 'X-Original-To'
        else:
            header = 'To'
        recipient = email.Utils.parseaddr(msg.get(header))[1]
        logger.info('MailToGroupRouter called with mail from %s to %s' % (sender, recipient))

        # Find the group
        group = self._findGroup(site, recipient)
        if not group:
            # recipient not a group, we're not handlig this msg
            return False

        # Drop privileges to the right user
        pm = getToolByName(site, 'portal_membership')
        
        # WARNING: Assuming login happens through email
        # Todo: Check / amend this
        try:
            #user_id = pm.searchMembers('email', sender)[0]['username']
            user = pm.getMemberById(sender).getUser()
        except (IndexError, AttributeError):
            raise PermissionError(_("%s is not a permitted sender address" % sender))
            
        # get members and send messages
        members = group.getGroupMembers()
        
        bcc = ', '.join([mmbr.getProperty('email') for mmbr in members])
        msg.add_header('BCC', bcc)
            
        for mmbr in members:
            site.MailHost.send(msg, mto=mmbr.getProperty('email'))

        return True

    def priority(self):
        return 30
