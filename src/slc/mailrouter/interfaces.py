from zope.schema import TextLine
from zope.interface import Interface
from slc.mailrouter import MessageFactory as _

class IMailRouterLayer(Interface):
    """Marker Interface used by as BrowserLayer
    """

class IMappingStorage(Interface):
    """ Stores mappings from names to targets. """

    def add(uid, name):
        """ Map name -> uid. """

    def remove(uid):
        """ Remove mapping. """

    def get(name):
        """ Look up name, return the uid. """

    def lookup(uid):
        """ Look up uid, return name. """

    def __getitem__(key):
        """ Return item corresponding to key. """

    def __len__():
        """ Return the number of items in storage. """

class IFriendlyNameStorage(IMappingStorage):
    """ A place to store the mapping of friendly names to uids, allowing
        a user to email friendlyname@ourdomain instead of uid@ourdomain. """

class IGroupAliasStorage(IMappingStorage):
    """ Stores aliases for groups for use by mail routers """

class IMailRouter(Interface):
    """ Utilities that act as mail routers implement this interface. """

    def __call__(self, site, message):
        """ Calling the utility handles ``message``, return True if it was
            handled, false otherwise. ``site`` is the plone site.
        """

    def priority(self):
        """ Return priority to determine the order in which routers are called.
        """
