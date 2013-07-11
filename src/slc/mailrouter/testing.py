from Products.CMFCore.utils import getToolByName
from plone.app.testing import applyProfile
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing.helpers import login, logout
import email
import os
from plone.uuid.interfaces import IUUID
from zope.component import queryUtility
from zope.component.hooks import getSiteManager

from slc.mailrouter.interfaces import IFriendlyNameStorage

PRIVILEGED_USER = "allowed@mailrouter.com"
UNPRIVILEGED_USER = "forbidden@mailrouter.com"
UNKNOWN_USER = "unknown@mailrouter.com"
PASSWORD = "password"


msginfo_privileged = {'FROM': PRIVILEGED_USER,
                      'FOLDERADDR': 'mailtest@mailrouter.com',
                      }

msginfo_unprivileged = {'FROM': UNPRIVILEGED_USER,
                        'FOLDERADDR': 'mailtest@mailrouter.com',
                        }

msginfo_unknown = {'FROM': UNKNOWN_USER,
                   'FOLDERADDR': 'mailtest@mailrouter.com',
                   }

msginfo_upper_case = {'FROM': PRIVILEGED_USER,
                      'FOLDERADDR': 'MAILTEST@mailrouter.com',
                      }


def load_mail(tmpl_file, msginfo):
    fd = open_mailfile(tmpl_file)
    tmpl = fd.read()
    mail = tmpl % msginfo
    msg = email.message_from_string(mail)
    return msg


def open_mailfile(tmpl_file):
    testfolder = os.path.join(os.path.split(__file__)[0], 'tests')
    path = os.path.join(testfolder, tmpl_file)
    fd = open(path)
    return fd


class MailRouterLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import slc.mailrouter
        self.loadZCML(
            'configure.zcml',
            package=slc.mailrouter,
        )
        gsm = getSiteManager()
        from Products.CMFCore.interfaces import IFolderish
        from slc.mailrouter.interfaces import IMailImportAdapter
        from slc.mailrouter.adapters import FolderAdapter
        gsm.registerAdapter(
            FolderAdapter,
            required=(IFolderish, ),
            provided=IMailImportAdapter)

    def _createUsers(self, portal):
        acl_users = getToolByName(portal, 'acl_users')
        acl_users.userFolderAddUser(
            PRIVILEGED_USER,
            PASSWORD,
            ['Contributor', ],
            [],
        )
        acl_users.userFolderAddUser(
            UNPRIVILEGED_USER,
            PASSWORD,
            [],
            [],
        )

    def _createContent(self, portal):
        login(portal, PRIVILEGED_USER)
        portal.invokeFactory('Folder', 'mailtest')
        storage = queryUtility(IFriendlyNameStorage)
        target = IUUID(portal.get('mailtest'))
        storage.add(target, 'mailtest')
        logout

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'slc.mailrouter:default')
        self._createUsers(portal)
        self._createContent(portal)

MAILROUTER_FIXTURE = MailRouterLayer()
MAILROUTER_INTEGRATION_TESTING = IntegrationTesting(
    bases=(MAILROUTER_FIXTURE, ), name="SlcMailrouter:Integration")
