import os
from setuptools import setup

readme_file = os.path.join(os.path.dirname(__file__), 'README.md')
with open(readme_file, 'r') as f:
    long_description = f.read()

setup(
    name='django-dynamic-model',
    version='0.1.0',
    url='http://github.com/rvinzent/django-dynamic-models',
    author='Ryan Vinzent',
    author_email='rvinzent217@hotmail.com',
    description='Allow dynamic creation and updates to database schema at runtime.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    packages=['dynamic_models'],
    install_requires=[
        'Django>=2.0',
    ],
    tests_require=[
        'tox',
        'pytest',
        'pytest-django',
        'pytest-cov',
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Framework :: Django'
    ]
)
