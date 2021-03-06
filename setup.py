#!/usr/bin/env python

from setuptools import setup

setup(
    name='GitPages',
    version='0.3',
    license='GPLv2',
    url='https://jordan.yelloz.me',
    author='Jordan Yelloz',
    author_email='jordan@yelloz.me',
    description='Git-backed web publishing code',
    long_description='Git-backed web publishing code',
    platforms='any',
    packages=[
        'gitpages',
        'gitpages.util',
        'gitpages.web',
        'gitpages.storage',
    ],
    include_package_data=True,
    install_requires=[
        'docutils',
        'dulwich',
        'Flask',
        'Flask-Failsafe',
        'Pygments',
        'python-dateutil',
        'pytz',
        'cachelib',
        'feedgen',
        'typogrify',
        'Unidecode',
        'Whoosh',
        'click',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-cov'],
)
