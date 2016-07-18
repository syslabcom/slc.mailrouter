import re
import email
from copy import copy
from AccessControl.SecurityManagement import newSecurityManager, \
    getSecurityManager
from zope.component import getUtility
from zope.component import queryUtility
from zope.interface import implements
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import IFolderish
from plone.registry.interfaces import IRegistry
from plone.uuid.interfaces import IUUID
from plone import api
from slc.mailrouter.interfaces import IFriendlyNameStorage
from slc.mailrouter.interfaces import IMailRouter, IMailImportAdapter
from slc.mailrouter.exceptions import (PermissionError, NotFoundError,
                                       ConfigurationError)
from slc.mailrouter import MessageFactory as _
from logging import getLogger
try:
    from plone.app.async.interfaces import IAsyncService
except ImportError:
    pass

logger = getLogger('slc.mailrouter.utils')

UIDRE = re.compile('^[0-9a-f-]+$')


def get_use_email_as_login():
    try:
        from Products.CMFPlone.interfaces import ISecuritySchema
        version = 5
    except ImportError:
        version = 4

    if version == 5:
        registry = getUtility(IRegistry)
        security_settings = registry.forInterface(
            ISecuritySchema, prefix='plone')
        use_email_as_login = security_settings.use_email_as_login
    else:
        portal_properties = api.portal.get_tool(name='portal_properties')
        site_properties = portal_properties.site_properties
        use_email_as_login = site_properties.getProperty('use_email_as_login')

    return use_email_as_login


def get_user_by_email(email, pm=None):
    if not email:
        return
    user_id = ''
    user = None
    use_email_as_login = get_use_email_as_login()
    pm = api.portal.get_tool(name='portal_membership')

    try:
        # avoid fuzzy searchMembers if we can
        if use_email_as_login:
            user = pm.getMemberById(email).getUser()
        else:
            results = pm.searchMembers('email', email)
            results = [r for r in results
                       if r['email'] == email]
            user_id = results[0]['username']
            user = pm.getMemberById(user_id).getUser()
    except (IndexError, AttributeError):
        return None
    return user


class BaseMailRouter(object):
    def __call__(self, site, msg):
        self.site = site
        self.acl_users = getToolByName(site, 'acl_users')

        sender_from = msg.get('From')
        sender_return_path = msg.get('Return-Path')

        sender_from = email.Utils.parseaddr(sender_from)[1]
        sender_return_path = email.Utils.parseaddr(sender_return_path)[1]
        recipient = email.Utils.parseaddr(msg.get('X-Original-To'))[1]

        if not recipient:
            logger.info('BaseMailRouter could not identify a recipient.' +
                        'No X-Original-To header found.'
                        )
        user = get_user_by_email(sender_return_path)
        if not user:
            user = get_user_by_email(sender_from)
        if not user:
            raise PermissionError(_("No permitted sender address: %s, %s" %
                                  (sender_return_path, sender_from)))

        return self.deliver(msg, user, recipient)


class MailToFolderRouter(BaseMailRouter):
    implements(IMailRouter)

    def deliver(self, msg, user, recipient):
        logger.info('MailToFolderRouter called with message %s from %s to %s' %
                    (msg.get('Message-ID'),
                     user.getProperty('email'),
                     recipient)
                    )
        local_part = recipient.split('@')[0].lower()

        assert len(local_part) <= 50, \
            "local_part must have a reasonable length"

        # Find the right context. Do that by looking up local_part
        # in our local friendly-name storage, and if not found, check
        # if it looks like a uid. Then look up the uid.
        storage = queryUtility(IFriendlyNameStorage)
        uid = storage.get(local_part, None)
        if uid is None and UIDRE.match(local_part) is not None:
            uid = local_part

        if uid is None:
            # local_part is not a uid and is not mapped onto a folder,
            # this is not something we can handle.
            return False

        # Drop privileges to the right user
        self.acl_users = getToolByName(self.site, 'acl_users')
        newSecurityManager(None, user.__of__(self.acl_users))
        context = api.content.get(UID=uid)
        if not context:
            raise NotFoundError(_("Folder not found"))

        if not IFolderish.providedBy(context):
            raise NotFoundError(
                _("Target %s is not a folder" % context.getId())
            )

        result = False

        # Check permissions
        if not getSecurityManager().checkPermission(
                'Add portal content',
                context):
            raise PermissionError(
                _("%s has insufficient privileges on %s" % (
                  user.getProperty('email'),
                  context.getId()
                  ))
            )

        # Defer actual work to an adapter
        result = IMailImportAdapter(context).add(msg)

        return result

    def priority(self):
        return 50


class MailToGroupRouter(BaseMailRouter):
    implements(IMailRouter)

    def _findGroup(self, site, recipient):
        local_part = recipient.split('@')[0]

        assert len(local_part) <= 50, \
            "local_part must have a reasonable length"

        groups_tool = getToolByName(site, 'portal_groups')
        group = groups_tool.getGroupById(local_part)
        if not group:
            pat = re.compile('^%s$' % local_part, re.I)  # ignore case
            candidates = filter(lambda g: pat.match(g),
                                groups_tool.getGroupIds())
            if len(candidates) > 1:
                raise ConfigurationError(
                    'Group name "%s" is not unique' % local_part
                )
        if not group and not candidates:
            return None

        if not group and candidates:
            group = groups_tool.getGroupById(candidates[0])
        return group

    def _sendMailToGroup(self, site, msg, group):
        # get members and send messages
        members = group.getGroupMembers()

        mto = [mmbr.getProperty('email') for mmbr in members]

        logger.info('Sending message with ID %s to recipients %s' %
                    (msg.get('Message-ID'), ', '.join(mto)))
        send_batched(site, msg, mto)

    def deliver(self, msg, user, recipient):
        logger.info('MailToFolderRouter called with message %s from %s to %s' %
                    (msg.get('Message-ID'),
                     user.getProperty('email'),
                     recipient)
                    )

        # Find the group
        group = self._findGroup(self.site, recipient)
        if not group:
            # recipient not a group, we're not handlig this msg
            return False

        logger.info('Resolved message with ID %s for group %s' %
                    (msg.get('Message-ID'), group.getId()))
        self._sendMailToGroup(self.site, msg, group)

        return True

    def priority(self):
        return 30


def send_batched(context, msg, mto):
    mfrom = msg.get('Return-Path')
    msg_out = copy(msg)
    del msg_out['Return-Path']
    del msg_out['X-Original-To']
    for batch in [mto[i:i + 50] for i in range(0, len(mto), 50)]:
        context.MailHost._send(mfrom, batch, msg_out.as_string())
        logger.info("Distributing group mail for '%s' to recipients %s" % (
            msg['X-Original-To'], ', '.join(batch))
        )


# for use in async
def sendMailToGroup(context, msg, groupid):
    # get members and send messages
    acl_users = getToolByName(context, 'acl_users')
    group = acl_users.getGroupById(groupid)
    members = group.getGroupMembers()

    mto = [mmbr.getProperty('email') for mmbr in members]

    send_batched(context, msg, mto)


class AsyncMailToGroupRouter(MailToGroupRouter):
    implements(IMailRouter)

    def _sendMailToGroup(self, site, msg, group):
        async = queryUtility(IAsyncService, default=None, context=self)
        async.queueJob(sendMailToGroup, site, msg, group.id)


def store_name(context, name):
    errors = {}
    storage = queryUtility(IFriendlyNameStorage)
    target = IUUID(context)
    if not name:
        errors.update(
            {'name': _(u'You must provide a friendly name.')})
    elif not re.match(r'^[a-zA-Z0-9_./-]+$', name):
        errors.update(
            {'name': _(u'Forbidden characters in friendly name. '
                       'Allowed characters: a-zA-Z0-9_./-')})
    if not errors:
        existing = storage.get(name)
        if existing and not existing == target:
            errors.update(
                {'name': _(u'This name is already in use.')})
        else:
            storage.remove(target)  # No effect if target isn't mapped
            storage.add(target, name)

    return errors
