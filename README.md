# django-dynamic-models

![PyPI](https://img.shields.io/pypi/v/django-dynamic-model?label=django-dynamic-model)


## Overview

Dynamic Django models allow users to define, edit, and populate their own database tables and apply runtime schema changes to the database. `django-dynamic-models` is loosely based on the [runtime dynamic models](https://dynamic-models.readthedocs.io/en/latest/) talk from DjangoCon 2011. The basic concept involves around dynamic class declaration using the built-in `type` function. `type` is used to dynamically declare new Django models at runtime, and it is the goal of this project to provide a simple API to allow developers to get started with dynamic models quickly.

This package provides models to help Django developers quickly implement dynamic models for their specific use case, while the handling the runtime schema changes and updates to Django's model registry under the hood. The schema changes are applied in pure Django, *without* the migrations framework, so none of your dynamic models will affect your migrations files at all.

> **Disclaimer**:
> 
> It is not recommended to use this project for business critical data due to the high potential for data loss. Tables can be dropped very easily, and without backups, even a small user error could be catastrophic.

## Documentation

See the [wiki](https://github.com/rvinzent/django-dynamic-models/wiki/Introduction) for documentation.
