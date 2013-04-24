import email
import os
import unittest
from zope.component import queryUtility

from slc.mailrouter.interfaces import IMailRouter
from slc.mailrouter.testing import (
    PRIVILEGED_USER, UNPRIVILEGED_USER, UNKNOWN_USER,
    MAILROUTER_INTEGRATION_TESTING
)


class TestFolderRouter(unittest.TestCase):
    """ Tests the mail folder router """
    layer = MAILROUTER_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.mailrouter = queryUtility(IMailRouter, name="mail")

    def send(self, tmpl_file, msginfo):
        path = os.path.join(os.path.split(__file__)[0], tmpl_file)
        fd = open(path)
        tmpl = fd.read()
        mail = tmpl % msginfo
        msg = email.message_from_string(mail)
        return self.mailrouter(self.portal, msg)

    def test_privileged_plain(self):
        msginfo = {'FROM': PRIVILEGED_USER,
                   'FOLDERADDR': 'mailtest@mailrouter.com',
                   }
        folder = self.portal.get('mailtest')
        result = self.send('mail_plain.txt', msginfo)
        self.assertTrue(result, msg="Mail not accepted")
        self.assertTrue('pixel.gif' in folder.objectIds(),
                        msg="Attachment not created")

    def test_privileged_html(self):
        msginfo = {'FROM': PRIVILEGED_USER,
                   'FOLDERADDR': 'mailtest@mailrouter.com',
                   }
        folder = self.portal.get('mailtest')
        result = self.send('mail_html.txt', msginfo)
        self.assertTrue(result, msg="Mail not accepted")
        self.assertTrue('pink_grad.gif' in folder.objectIds(),
                        msg="Attachment not created")

    def test_privileged_mixed(self):
        msginfo = {'FROM': PRIVILEGED_USER,
                   'FOLDERADDR': 'mailtest@mailrouter.com',
                   }
        folder = self.portal.get('mailtest')
        result = self.send('mail_mixed.txt', msginfo)
        self.assertTrue(result, msg="Mail not accepted")
        self.assertTrue('pixel.gif' in folder.objectIds(),
                        msg="Attachment not created")

