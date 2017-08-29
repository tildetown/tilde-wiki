#!/usr/bin/env python

from setuptools import setup

setup(
    name='tildewiki',
    version='1.0.0',
    description='small utility for managing a wiki a la tilde.town',
    url='https://github.com/tildetown/tilde-wiki',
    author='vilmibm shaksfrpease',
    author_email='nks@neongrid.space',
    license='GPL',
    classifiers=[
        'Topic :: Artistic Software',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    ],
    keywords='wiki',
    packages=['tildewiki'],
    install_requires = ['Markdown==2.6.9',
                        'click==6.7',
                        'pygit2==0.24.1'], # matches current libgit2-dev version in ubuntu LTS
    entry_points = {
          'console_scripts': [
              'wiki = tildewiki.main:main'
          ]
    },
)
