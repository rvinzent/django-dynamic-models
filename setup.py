import os
from setuptools import setup

README = os.path.join(os.path.dirname(__file__), "README.md")
with open(README, "r") as f:
    LONG_DESCRIPTION = f.read()

setup(
    name="django-dynamic-model",
    version="0.4.0",
    url="http://github.com/rvinzent/django-dynamic-models",
    author="Ryan Vinzent",
    author_email="ryan.vinzent@gmail.com",
    description="Allow dynamic creation and updates to database schema at runtime.",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    license="MIT",
    packages=["dynamic_models", "dynamic_models.migrations"],
    install_requires=[
        "Django>=2.1",
    ],
    tests_require=[
        "tox",
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Framework :: Django",
    ],
)
