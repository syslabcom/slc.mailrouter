Introduction
============

slc.mailrouter bridges the gap between zope and email. It is based on the same
idea as products such as mailboxer: a script is invoked by your mail transfer
agent (postfix, exim) and the body of the email is passed to this script on
stdin. This is then communicated to zope using an http post, where it is parsed
and handled.

slc.mailrouter implements a component model for the handling of emails. By
itself it allows the user to send an email to a folder and have all attachments
on the email stored in that folder. The folder can be addressed either by
its UID, or by assigning a friendly alias to the folder in the plone control
panel.

The MailToFolder router is implemented using an adapter pattern. If you want
to change the way this works, Implement an adapter that adapts IFolderish
and implements slc.mailrouter.interfaces.IMailImportAdapter. The add() method
on this adapter receives the message as an argument and is responsible for
persisting the contents of the message to the folder.

Additional mail routes can be implemented by other products by creating a
utility and registering it under the interface
slc.mailrouter.interfaces.IMailRouter. Such mail router utilities are called
one after the other until one of them reports that the message was successfully
delivered. In this way it mirrors the way exim's routers work.


Credits
-------

Izak Burger <isburger@gmail.com> 
Manuel Reinhardt <reinhardt@syslab.com>

