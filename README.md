# django-dynamic-models

**NOTE: WORK IN PROGRESS**

This is a work in progress. All code is subject to change and is not guaranteed to work properly. Check out the `develop` branch to view progress. Suggestions and feedback are encouraged in the meantime!


## Overview

Dynamic Django models allow users to define, edit, and populate their own database tables and apply runtime schema changes to the database. `django-dynamic-models` provides a customizable implementation of the [runtime dynamic models](https://dynamic-models.readthedocs.io/en/latest/) DjangoCon talk given in 2011. The basic concept revolves around dynamic class declaration using the built-in `type` function. The `type` function is used to declare new Django models at runtime.

This package provides abstract models to help Django developers quickly implement dynamic runtime models for their specific use without the need to worry about schema changes. Use cases for runtime dynamic models involve any application where the database tables might not be known ahead of time. The dynamic models can be updated at runtime, without the need for server downtime or schema migrations.

## Support
Official version support will be tested and defined pre-release.

#### Databases:
Only databases that have the `can_rollback_ddl` feature are officially supported. Because Django wraps each test case in a transaction, testing schema changing functions does not work with backends such as MySQL and SQLite3. *Use these at your own risk*.