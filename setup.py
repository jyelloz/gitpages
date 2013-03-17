from setuptools import setup

setup(
    name='GitPages',
    version='0.1-dev',
    license='MIT',
    url='https://jordan.yelloz.me/projects/gitpages/',
    author='Jordan Yelloz',
    author_email='jordan@yelloz.me',
    description='Git-backed web publishing code',
    long_description='Git-backed web publishing code',
    platforms='any',
    packages=[
        'gitpages',
        'gitpages.web',
        'gitpages.storage',
    ],
    install_requires=[
        'docutils',
        'dulwich',
        'Flask',
        'Flask-Failsafe',
        'Flask-Script',
        'Pygments',
        'python-dateutil',
        'pytz',
        'titlecase',
        'typogrify',
        'Unidecode',
        'Whoosh',
    ],
)
