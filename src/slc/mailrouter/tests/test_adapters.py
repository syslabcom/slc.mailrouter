from slc.mailrouter.interfaces import IEmailToUser
from slc.mailrouter.testing import MAILROUTER_INTEGRATION_TESTING
from slc.mailrouter.utils import get_user_by_email
from zope.component import adapter
from zope.component import getGlobalSiteManager
from zope.interface import implementer
from zope.interface import Interface

import unittest


@implementer(IEmailToUser)
@adapter(Interface)
class FooAdapter:
    order = 1

    def __init__(self, context):
        pass

    def __call__(self, email):
        return 1


class TestAdapters(unittest.TestCase):
    """Tests the mail folder router"""

    layer = MAILROUTER_INTEGRATION_TESTING

    def test_get_user_by_email(self):
        # If email cannot be resolved return None
        self.assertIsNone(get_user_by_email(None))
        self.assertIsNone(get_user_by_email(""))
        self.assertIsNone(get_user_by_email("foo"))
        self.assertIsNone(get_user_by_email("foo@example.com"))

        # Check that it picks the proper user
        self.assertEqual(
            get_user_by_email("allowed@mailrouter.com").getUserId(),
            "allowed@mailrouter.com",
        )

        # Check that we can register adapter to override the default behavior
        sm = getGlobalSiteManager()
        sm.registerAdapter(factory=FooAdapter, name="foo")
        self.assertEqual(get_user_by_email("allowed@mailrouter.com"), 1)
        # Clean up
        sm.unregisterAdapter(factory=FooAdapter, name="foo")
