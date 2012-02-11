from zope.schema import TextLine
from zope.interface import Interface
from slc.mailrouter import MessageFactory as _

class IMailRouterLayer(Interface):
    """Marker Interface used by as BrowserLayer
    """

class IFriendlyNameStorage(Interface):
    """ A place to store the mapping of friendly names to uids, allowing
        a user to email friendlyname@ourdomain instead of uid@ourdomain. """

    def add(uid, name):
        """ Map name -> uid. """

    def remove(uid):
        """ Remove mapping. """

    def get(name):
        """ Look up name, return the uid. """

    def __getitem__(key):
        """ Return item corresponding to key. """

    def __len__():
        """ Return the number of items in storage. """
