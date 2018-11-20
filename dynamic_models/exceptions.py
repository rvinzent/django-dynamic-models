class DynamicModelError(Exception):
    """
    Base exception for use in dynamic models
    """


class InvalidConfigurationError(DynamicModelError):
    """
    Raised when the settings for the app are not configured correctly.
    """


class OutdatedModelError(DynamicModelError):
    """
    Raised when a model's schema is outdated.
    """
    def __init__(self, model):
        super().__init__()
        self.message = '{} has changed since loading from the database'\
            .format(model)


class InvalidFieldError(DynamicModelError):
    """
    Raised when a model field is deemed invalid.
    """
    def __init__(self, field, reason=None):
        super().__init__()
        self.message = '{} is invalid'.format(field)
        if reason:
            self.message += ': {}'.format(reason)


class NullFieldChangedError(DynamicModelError):
    """
    Raised when a field is attempted to be change from NULL to NOT NULL without
    a default value to fill into the columns.
    """
    def __init__(self, field):
        super().__init__()
        self.message = '{} cannot be changed from NULL to NOT NULL'.format(field)