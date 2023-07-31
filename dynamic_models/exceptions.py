"""Provide exceptions to be raised by the `dynamic_models` app.

All exceptions inherit from a `DynamicModelError` base class.
"""


class DynamicModelError(Exception):
    """Base exception for use in dynamic models."""


class NullFieldChangedError(DynamicModelError):
    """Raised when a field is attempted to be change from NULL to NOT NULL."""


class InvalidFieldNameError(DynamicModelError):
    """Raised when a field name is invalid."""


class UnsavedSchemaError(DynamicModelError):
    """
    Raised when a model schema has not been saved to the db and a dynamic model
    is attempted to be created.
    """
