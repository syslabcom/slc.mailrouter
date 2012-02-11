from persistent import Persistent
from zope.interface import implements
from BTrees.OOBTree import OOBTree, OOSet
from slc.mailrouter.interfaces import IFriendlyNameStorage

class FriendlyNameStorage(Persistent):
    implements(IFriendlyNameStorage)

    def __init__(self):
        self._forward = OOBTree() # name -> uid
        self._reverse = OOBTree() # uid -> name

    def add(self, uid, name):
        """ Map name -> uid. """
        self._forward[name] = uid
        self._reverse[uid] = name

    def remove(self, uid):
        """ Remove mapping. This will be called when a folder is deleted,
            therefore we use the uid. """
        marker = object()
        name = self._reverse.get(uid, marker)
        if name is not marker:
            del(self._reverse[uid])
            try:
                del(self._forward[name])
            except KeyError:
                # If it isn't there, good, that is the outcome we wanted,
                # right?
                pass

    def get(self, name, _marker=None):
        """ Look up name, map uid to an object and return it. """
        return self._forward.get(name, _marker)

    def __getitem__(self, key):
        return self._forward.items()[key]

    def __len__(self):
        return len(self._forward)
