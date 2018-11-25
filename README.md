# django-dynamic-models

**NOTE: WORK IN PROGRESS**

This is a work in progress. All code is subject to change and is not guaranteed to work properly. Check out the `develop` branch to view progress. Suggestions and feedback are encouraged in the meantime! The package is not yet available on PyPi.


## Overview

Dynamic Django models allow users to define, edit, and populate their own database tables and apply runtime schema changes to the database. `django-dynamic-models` is based on the [runtime dynamic models](https://dynamic-models.readthedocs.io/en/latest/) DjangoCon talk from 2011. The basic concept revolves around dynamic class declaration using the built-in `type` function. The `type` function is used to declare new Django models at runtime.

This package provides abstract models to help Django developers quickly implement dynamic runtime models for their specific use without the need to worry about any schema changing code.

## Installation

Install `django-dynamic-models` from PyPi with:

```python
pip install django-dynamic-models
```

Then, add `'dynamic_models'` to `INSTALLED_APPS` and run the commands `makemigrations` and `migrate`.
> **Note**: 
> 
> Django's Content Types app is currently required.

```python
INSTALLED_APPS = [
    ...
    'dynamic_models',
    'django.contrib.conttenttypes'
]
```

## Usage

To begin, simply import and subclass the abstract models from `dynamic_models.models`. The abstract models will still work if no additional fields are provided, however, `dynamic_models` does not currently guarantee unique table names.

## Support
Official version support will be tested and defined pre-release.