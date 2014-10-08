#!/usr/bin/python

import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import docw

if sys.version_info[0] != 3:
    print("Error: python 3 is required.")
    exit()

setup(
    # Application name:
    name='docwutils',

    # Version number:
    version=docw.__version__,

    # Application author details:
    author="Dongjin Lee",
    author_email="dongjin.lee.kr@gmail.com",

    # Packages
    packages=["docw"],

    # Details
    url="https://github.com/dongjinleekr/docw",

    #
    license=docw.__license__,
    description="python scripts for docw.",

    long_description=
"""\
python scripts for docw, available in Python 3.0+.
""",

    # Dependent packages (distributions)
    install_requires=[
        'psutil >= 2.1.3',
        'dopy >= 0.2.5',
    ],
    
    entry_points={
        'console_scripts': [
            'docw-gettmp = docw.gettmp:main',
        ],
    },
)
