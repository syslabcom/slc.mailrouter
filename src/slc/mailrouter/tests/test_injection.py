import unittest
from mock import Mock
from Testing.makerequest import makerequest
from zope.component.hooks import getSiteManager
from zope.publisher.http import HTTPResponse
from StringIO import StringIO
from logging import getLogger, StreamHandler, INFO
from Products.CMFPlone.utils import safe_unicode

from slc.mailrouter.testing import (
    MAILROUTER_INTEGRATION_TESTING,
    open_mailfile,
)
from slc.mailrouter.interfaces import IMailRouter
from slc.mailrouter.exceptions import PermanentError


class TestInjection(unittest.TestCase):
    """ Tests the mail router injection view """
    layer = MAILROUTER_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.log = StringIO()
        browser_logger = getLogger('slc.mailrouter.browser')
        browser_logger.setLevel(INFO)
        browser_logger.addHandler(StreamHandler(self.log))

    def register_error_mail_router(self, error_class):
        sm = getSiteManager()
        MockMailRouter = Mock(
            return_value=False,
            side_effect=error_class('An error happened!'))
        MockMailRouter.getPhysicalPath = Mock(
            return_value='/plone/mockmailrouter')
        sm.registerUtility(
            name='mockmail',
            provided=IMailRouter,
            component=MockMailRouter)

    def do_inject(self, encoding=None):
        inject = self.portal.restrictedTraverse('@@mailrouter-inject')
        inject.request = makerequest(self.portal)
        inject.request.response = HTTPResponse()
        mailfile = open_mailfile('mail_plain.txt')
        mail = mailfile.read()
        mailfile.close()
        if encoding is not None:
            mail = safe_unicode(mail).encode(encoding)
        inject.request.stdin = StringIO(mail)
        return inject()

    def test_permanent_error(self):
        self.register_error_mail_router(PermanentError)
        result = self.do_inject()

        self.log.flush()
        self.assertTrue(result.startswith("Fail:"),
                        msg="Inject should have failed but didn't")
        self.assertTrue('PermanentError' in result)
        self.assertTrue('Dumped mail' in self.log.getvalue())

    def test_key_error(self):
        self.register_error_mail_router(KeyError)
        result = self.do_inject()

        self.log.flush()
        self.assertTrue(result.startswith("Fail:"),
                        msg="Inject should have failed but didn't")
        self.assertTrue('KeyError' in result)
        self.assertTrue('Dumped mail' in self.log.getvalue())

    def test_not_accepted(self):
        result = self.do_inject()
        self.assertTrue(result.startswith("FAIL:"),
                        msg="Inject should have failed but didn't")
        self.assertTrue('Dumped mail' not in self.log.getvalue())
        self.assertTrue('not found' in self.log.getvalue())

    def test_iso_8859_11_encoding_permanent_error(self):
        self.register_error_mail_router(PermanentError)
        result = self.do_inject(encoding='iso-8859-11')

        self.log.flush()
        self.assertTrue(result.startswith("Fail:"),
                        msg="Inject should have failed but didn't")
        self.assertTrue('PermanentError' in result)
        self.assertTrue('Dumped mail' in self.log.getvalue())
