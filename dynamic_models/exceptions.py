class DynamicModelError(Exception):
    """
    Base exception for use in dynamic models
    """
    pass


class InvalidConfigurationError(DynamicModelError):
    """
    Raised when the settings for the app are not configured correctly.
    """
    pass


class OutdatedModelError(DynamicModelError):
    """
    Raised when a model's schema is outdated.
    """
    def __init__(self, model):
        self.message = '{} has changed since loading from the database'\
            .format(model)


class InvalidFieldError(DynamicModelError):
    """
    Raised when a model field is deemed invalid.
    """
    def __init__(self, field, reason=None):
        self.message = '{} is invalid'.format(field)
        if reason:
            self.message = '{}: {}'.format(self.message, reason)


class NullFieldChangedError(DynamicModelError):
    """
    Raised when a field is attempted to be change from NULL to NOT NULL without
    a default value to fill into the columns.
    """
    def __init__(self, field):
        self.message = '{} cannot be changed from NULL to NOT NULL'.format(field)