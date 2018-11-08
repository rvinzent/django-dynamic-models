class DynamicModelError(Exception):
    """
    Base exception for use in dynamic models
    """


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
            self.message += ': {}'.format(reason)