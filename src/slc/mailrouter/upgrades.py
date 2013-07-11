from zope.component import queryUtility
import logging

from slc.mailrouter.interfaces import IFriendlyNameStorage

logger = logging.getLogger(__name__)


def convert_storage_entries_to_lower_case(context):
    storage = queryUtility(IFriendlyNameStorage)
    if not storage:
        logger.info('No storage found, nothing done')
        return
    count = 0
    for entry in storage:
        if entry[0] != entry[0].lower():
            storage.remove(entry[1])
            storage.add(entry[1], entry[0].lower())
            count += 1
    logger.info('Converted {0} of {1} storage entries'.format(
        count, len(storage)))
