from persistent import Persistent
from zope.interface import implements
from BTrees.OOBTree import OOBTree, OOSet
from Products.CMFCore.utils import getToolByName
from slc.mailrouter.interfaces import IFriendlyNameStorage, IGroupAliasStorage

class FriendlyNameStorage(Persistent):
    implements(IFriendlyNameStorage)

    def __init__(self):
        self._forward = OOBTree() # name -> uid
        self._reverse = OOBTree() # uid -> name

    def add(self, uid, name):
        """ Map name -> uid. """
        if name in self._forward:
            raise ValueError("%s already mapped" % name)
        if uid in self._reverse:
            raise ValueError("%s already has a friendly name" % uid)
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

    def lookup(self, uid, _marker=None):
        """ Look up uid, return name. """
        return self._reverse.get(uid, _marker)

    def __getitem__(self, key):
        return self._forward.items()[key]

    def __len__(self):
        return len(self._forward)


class GroupAliasStorage(Persistent):
    implements(IGroupAliasStorage)

    def __init__(self):
        pass

    def _groupdict(self):
        """ Returns a dict that maps group ids to aliases """
        groups_tool = getToolByName(self, 'portal_groups')
        mapped_groups = filter(lambda g: g.getProperty('email'), map(lambda g: groups_tool.getGroupById(g), groups_tool.getGroupIds()))
        items = [(g.getProperty('email'), g.getProperty('id')) for g in mapped_groups]
        return dict(items)

    def add(self, groupid, alias):
        """ Map alias -> groupid. """
        groups_tool = getToolByName(self, 'portal_groups')
        group = groups_tool.getGroupById(groupid)
        if not group:
            raise KeyError('No such group: %s' % groupid)
        if group.getProperty('email'):
            raise ValueError('%s already has an alias' % groupid)
        if alias.split('@')[0] in map(lambda a: a.split('@')[0], self._groupdict().values()):
            raise ValueError('Alias %s already mapped' % alias)
        group.setProperties(dict(email=alias))
            
    def remove(self, groupid):
        """ Remove mapping. """
        groups_tool = getToolByName(self, 'portal_groups')
        group = groups_tool.getGroupById(groupid)
        if not group:
            # nogroup, no alias
            return
        group.setProperties(dict(email=''))
        
    def lookup(self, groupid, _marker=None):
        """ Look up groupid, return alias. """
        return self._groupdict().get(groupid, _marker)

    def get(self, alias, _marker=None):
        """ Look up alias, return groupid(s). """
        candidates = filter(lambda item: item[0].split('@')[0] == alias.split('@')[0], self._groupdict())
        if not candidates:
            return _marker
        elif len(candidates) == 1:
            return candidates[0][1]
        else:
            return map(lambda g: g[0], candidates)

    def __getitem__(self, key):
        return self._groupdict().items()[key]

    def __len__(self):
        return len(self._groupdict())


