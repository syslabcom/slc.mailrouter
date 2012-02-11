from zope.schema import TextLine
from zope.interface import Interface
from slc.mailrouter import MessageFactory as _

class IMailRouterLayer(Interface):
    """Marker Interface used by as BrowserLayer
    """
