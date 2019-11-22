import email
import sys
import traceback
from io import TextIOWrapper
from logging import getLogger
from tempfile import NamedTemporaryFile

from Acquisition import aq_inner
from plone.uuid.interfaces import IUUID
from Products.CMFCore.interfaces import IFolderish
from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.CMFPlone.PloneBatch import Batch
from Products.CMFPlone.utils import safe_nativestring
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from six import StringIO
from slc.mailrouter import MessageFactory as _
from slc.mailrouter.exceptions import PermanentError, PermissionError, TemporaryError
from slc.mailrouter.interfaces import IFriendlyNameStorage, IMailRouter
from slc.mailrouter.utils import store_name
from zope.component import getAllUtilitiesRegisteredFor, queryUtility
from zope.interface import alsoProvides

logger = getLogger("slc.mailrouter.browser")


def get_exception_message(e):
    return "%s: %s" % (e.__class__.__name__, str(e))


def get_exception_log_entry(e):
    exc_type, val, tb = sys.exc_info()
    tb_str = StringIO()
    traceback.print_tb(tb, file=tb_str)
    return safe_nativestring(
        "{0}: {1}\nTraceback:\n{2}{0}: {1}".format(
            e.__class__.__name__, str(e), tb_str.getvalue()
        )
    )


class InjectionView(BrowserView):
    def __call__(self):
        self.request.stdin.seek(0)
        stream = TextIOWrapper(self.request.stdin, encoding="utf-8")
        msg = email.message_from_file(stream)

        # Get all registered mail routers. Sort by priority, then
        # call them until it is handled
        routers = getAllUtilitiesRegisteredFor(IMailRouter)
        routers.sort(key=lambda x: x.priority())
        for router in routers:
            try:
                if router(aq_inner(self.context), msg):
                    try:
                        from plone.protect.interfaces import IDisableCSRFProtection
                    except ImportError:
                        pass
                    else:
                        alsoProvides(self.request, IDisableCSRFProtection)
                    return "OK: Message accepted"
            except PermissionError as e:
                errmsg = get_exception_message(e)
                self.request.response.setStatus(e.status)
                logmsg = get_exception_log_entry(e)
                logger.info(logmsg)
                return "Fail: %s" % errmsg
            except (PermanentError, TemporaryError) as e:
                errmsg = get_exception_message(e)
                self.request.response.setStatus(e.status)
                logmsg = get_exception_log_entry(e)
                logger.warn(logmsg)
                self.dump_mail()
                return "Fail: %s" % errmsg
            except Exception as e:
                # raise
                errmsg = get_exception_message(e)
                self.request.response.setStatus(500, reason=errmsg)
                logmsg = get_exception_log_entry(e)
                logger.error(logmsg)
                self.dump_mail()
                return "Fail: %s" % errmsg

        self.request.response.setStatus(404)
        recipient = safe_nativestring(msg.get("X-Original-To"))
        logger.warn("FAIL: Recipient address X-Original-To: %s not found" % (recipient))
        return "FAIL: Recipient address X-Original-To: %s not found" % (
            msg.get("X-Original-To")
        )

    def dump_mail(self):
        try:
            tmpfile = NamedTemporaryFile(prefix="mailrouter-dump", delete=False)
            self.request.stdin.seek(0)
            tmpfile.write(self.request.stdin.read())
            logger.info("Dumped mail to %s" % tmpfile.name)
            tmpfile.close()
        except Exception as e:
            logger.warn("Error while dumping mail: %s" % get_exception_log_entry(e))


class FriendlyNameStorageView(BrowserView):
    def update(self):
        """ Called from the template, it deletes any mappings
            specified on the request. """
        remove = self.request.get("remove", ())
        storages = [queryUtility(IFriendlyNameStorage)]
        for item in remove:
            for storage in storages:
                storage.remove(item)

    def folder_mappings(self):
        storage = queryUtility(IFriendlyNameStorage)
        b_size = int(self.request.get("b_size", 50))
        b_start = int(self.request.get("b_start", 0))
        return Batch(storage, b_size, b_start)


class FriendlyNameAddView(BrowserView):
    addtemplate = ViewPageTemplateFile("add.pt")

    def __call__(self):
        errors = {}
        if self.request.get("form.submitted", None) is not None:
            errors = store_name(self.context, self.request.get("name", ""))

        self.request["errors"] = errors
        if not errors and "redirect" in self.request:
            IStatusMessage(self.request).add(_(u"Mail route enabled."))
            return self.request.RESPONSE.redirect(self.request["redirect"])
        return self.addtemplate()

    def friendlyname(self):
        storage = queryUtility(IFriendlyNameStorage)
        return storage.lookup(IUUID(self.context))

    def displayMailTab(self):
        # Cannot mail into the portal root
        if self.context.restrictedTraverse("@@plone_context_state").is_portal_root():
            return False
        return IFolderish.providedBy(self.context) and _checkPermission(
            AddPortalContent, self.context
        )
