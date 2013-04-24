import email
import os
import unittest
from zope.component import queryUtility

from slc.mailrouter.interfaces import IMailRouter
from slc.mailrouter.testing import (
    PRIVILEGED_USER, UNPRIVILEGED_USER, UNKNOWN_USER,
    MAILROUTER_INTEGRATION_TESTING
)
from slc.mailrouter.exceptions import PermissionError

msginfo_privileged = {'FROM': PRIVILEGED_USER,
                      'FOLDERADDR': 'mailtest@mailrouter.com',
                      }

msginfo_unprivileged = {'FROM': UNPRIVILEGED_USER,
                        'FOLDERADDR': 'mailtest@mailrouter.com',
                        }

msginfo_unknown = {'FROM': UNKNOWN_USER,
                   'FOLDERADDR': 'mailtest@mailrouter.com',
                   }


class TestFolderRouter(unittest.TestCase):
    """ Tests the mail folder router """
    layer = MAILROUTER_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.folder = self.portal.get('mailtest')
        self.mailrouter = queryUtility(IMailRouter, name="mail")

    def send(self, tmpl_file, msginfo):
        path = os.path.join(os.path.split(__file__)[0], tmpl_file)
        fd = open(path)
        tmpl = fd.read()
        mail = tmpl % msginfo
        msg = email.message_from_string(mail)
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
