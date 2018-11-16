from setuptools import setup

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='django-dynamic-models',
    version='0.1dev1',
    url='http://github.com/rvinzent/django-dynamic-models',
    author='Ryan Vinzent',
    author_email='rvinzent217@hotmail.com',
    description='Allow users to create and use their own models',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    packages=['dynamic_models'],
    install_requires=[
        'Django>=2.1',
        'django-model-utils'
    ],
    tests_require=[
            'tox',
            'pytest',
            'pytest-django',
            'pytest-cov'
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System:: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Framework :: Django'
    ]
)