from Products.CMFCore.utils import getToolByName
from plone.app.testing import applyProfile
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing.helpers import login, logout
from plone.uuid.interfaces import IUUID
from zope.component import queryUtility

from slc.mailrouter.interfaces import IFriendlyNameStorage

PRIVILEGED_USER = "allowed@mailrouter.com"
UNPRIVILEGED_USER = "forbidden@mailrouter.com"
UNKNOWN_USER = "unknown@mailrouter.com"
PASSWORD = "password"


class MailRouterLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import slc.mailrouter
        self.loadZCML(
            'configure.zcml',
            package=slc.mailrouter,
        )

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
