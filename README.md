# django-dynamic-models [![Build Status](https://travis-ci.com/rvinzent/django-dynamic-models.svg?branch=master)](https://travis-ci.com/rvinzent/django-dynamic-models)


## Overview

Dynamic Django models allow users to define, edit, and populate their own database tables and apply runtime schema changes to the database. `django-dynamic-models` is loosely based on the [runtime dynamic models](https://dynamic-models.readthedocs.io/en/latest/) talk from DjangoCon 2011. The basic concept involves around dynamic class declaration using the built-in `type` function. We use `type` to dynamically declare new Django models at runtime, and it is the goal of this project to provide a simple API to allow developers to get started with runtime dynamic models quickly.

This package provides abstract models to help Django developers quickly implement dynamic runtime models for their specific use case while the runtime schema changes and Django's model registry are handled automatically. The schema changes are applied in pure Django, *without* the migrations framework, so none of your dynamic models will affect your migrations files at all.

## Documentation

See the [wiki](https://github.com/rvinzent/django-dynamic-models/wiki/Introduction) for documentation.
