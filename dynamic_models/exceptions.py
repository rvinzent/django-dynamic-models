"""Provide exceptions to be raised by the `dynamic_models` app.

All exceptions inherit from a `DynamicModelError` base class.
"""
class DynamicModelError(Exception):
    """Base exception for use in dynamic models."""


class ModelDoesNotExistError(DynamicModelError):
    """Raised when model is not found in the app registry."""


class OutdatedModelError(DynamicModelError):
    """Raised when a model's schema is outdated on save."""


class NullFieldChangedError(DynamicModelError):
    """Raised when a field is attempted to be change from NULL to NOT NULL."""
