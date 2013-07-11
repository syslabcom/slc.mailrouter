class PermanentError(Exception):
    """ Base class for all permanent errors. """
    status = 400


class TemporaryError(Exception):
    """ Base class for temporary errors. """
    status = 500


class PermissionError(PermanentError):
    """ Raise this if not enough permission to deliver email. """
    status = 403


class NotFoundError(PermanentError):
    """ Raise this if target cannot be found. """
    status = 404


class ConfigurationError(TemporaryError):
    """ Raise this for configuration errors. """
