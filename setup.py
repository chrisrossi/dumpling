import os
from setuptools import setup
from setuptools import find_packages

VERSION = '0.1a1'

requires = [
    'acidfs',
    'pyyaml',
]
tests_require = requires + ['pytest', 'pytest-cov']

testing_extras = tests_require + ['tox']
doc_extras = ['Sphinx']

here = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(here, 'README.rst')).read()
    CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()
except IOError:
    README = CHANGES = ''

setup(
    name='dumpling',
    version=VERSION,
    description='Filesystem based object store using YAML and AcidFS.',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: Implementation :: CPython",
        #"Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Database",
        "License :: Repoze Public License",
    ],
    keywords='yaml persistence acidfs',
    author="Chris Rossi",
    author_email="pylons-discuss@googlegroups.com",
    url="http://pylonsproject.org",
    license="BSD-derived (http://www.repoze.org/LICENSE.txt)",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    tests_require=tests_require,
    extras_require={
        'testing': testing_extras,
        'docs': doc_extras,
    },
    test_suite="dumpling.tests",
)
