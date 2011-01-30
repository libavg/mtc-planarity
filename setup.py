#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(
    name='Planarity',
    version='1.0',
    author='Martin Heistermann, Thomas Schott',
    author_email='<mh at sponc dot de>, <scotty at c-base dot org>',
    license='GPL3',
    packages=['planarity'],
    scripts=['scripts/planarity'],
    package_data={
            'planarity': ['media/*.png', 'data/levels.pickle.gz'],
    }
)
