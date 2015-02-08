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
  name='docw',

  # Version number:
  version=docw.__version__,

  # Application author details:
  author="Dongjin Lee",
  author_email="dongjin.lee.kr@gmail.com",

  # Packages
  packages=['docw'],

  # Details
  url="https://github.com/dongjinleekr/docw",

  #
  license=docw.__license__,
  description="Digitalocean(tm) Cluster Wizard.",

  long_description=
"""\
Digitalocean(tm) Cluster Wizard, available in Python 3.0+.
""",

  # Dependent packages (distributions)
  install_requires=[
    'lxml >= 3.3.3',
    'paramiko >= 1.15.2',
    'python-digitalocean >= 1.3',
    'scp',
    'pexpect >= 3.3',
  ],

  dependency_links=[
        "https://github.com/jbardin/scp.py.git"
  ],

  entry_points={
    'console_scripts': [
      'docw = docw.docw:main',
    ],
  },
)
