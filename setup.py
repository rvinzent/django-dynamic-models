from distutils.core import setup

setup(
    name='django-dynamic-models',
    version='0.1dev1',
    url='http://github.com/rvinzent/django-dynamic-models',
    author='Ryan Vinzent',
    license='MIT',
    packages=['dynamic_models'],
    install_requires=['django', 'django-model-utils'],
    extras_require={
        'dev': [
            'tox',
            'pytest',
            'pytest-django',
            'pytest-cov'
        ]
    },
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ]
)