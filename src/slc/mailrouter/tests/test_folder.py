import unittest

from slc.mailrouter.utils import MailToFolderRouter
from slc.mailrouter.testing import (
    MAILROUTER_INTEGRATION_TESTING,
    load_mail,
    msginfo_privileged,
    msginfo_unprivileged,
    msginfo_unknown,
    msginfo_upper_case,
)
from slc.mailrouter.exceptions import PermissionError


class TestFolderRouter(unittest.TestCase):
    """ Tests the mail folder router """
    layer = MAILROUTER_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.folder = self.portal.get('mailtest')
        # XXX Stupid workaround for a conflict with
        # PloneintranetuserprofileLayer
        self.portal.portal_catalog.indexObject(self.folder)
        self.mailrouter = MailToFolderRouter()

    def send(self, tmpl_file, msginfo):
        msg = load_mail(tmpl_file, msginfo)
        return self.mailrouter(self.portal, msg)

    def test_privileged_plain(self):
        result = self.send('mail_plain.txt', msginfo_privileged)
        self.assertTrue(result, msg="Mail not accepted")
        self.assertTrue('pixel.gif' in self.folder.objectIds(),
                        msg="Attachment not created")

    def test_privileged_html(self):
        result = self.send('mail_html.txt', msginfo_privileged)
        self.assertTrue(result, msg="Mail not accepted")
        self.assertTrue('pink_grad.gif' in self.folder.objectIds(),
                        msg="Attachment not created")

    def test_privileged_mixed(self):
        result = self.send('mail_mixed.txt', msginfo_privileged)
        self.assertTrue(result, msg="Mail not accepted")
        self.assertTrue('pixel.gif' in self.folder.objectIds(),
                        msg="Attachment not created")

    def test_unprivileged(self):
        self.assertRaises(PermissionError,
                          self.send, 'mail_plain.txt', msginfo_unprivileged)

    def test_unknown(self):
        self.assertRaises(PermissionError,
                          self.send, 'mail_plain.txt', msginfo_unknown)

    def test_local_part_case_insensitive(self):
        result = self.send('mail_plain.txt', msginfo_upper_case)
        self.assertTrue(result, msg="Mail not accepted")
