#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# PYTHON_ARGCOMPLETE_OK

from distutils.core import setup
try:
    # 3.x
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    # 2.x
    from distutils.command.build_py import build_py

try:
    import os
    import argparse
    import argcomplete
except ImportError, e:
    raise Exception("{}. You must install the missed python module to use kathy_tools module.".format(e))

cmdclass = {'build_py': build_py}
command_options = {}

setup(
    name='odoo t2d tools',
    version='0.0.1',
    author='Katherine Zaoral',
    author_email='kathy@vauxoo.com',
    packages=['odoo_tools'],
    scripts=[
        'bin/odoo-instance',
        'bin/odoo-i18n-export',
        'bin/odoo-description',
    ],
    #~ license='LICENSE.txt',
    description='Multiple tools for day use.',
    #~ keywords= define keywords,
    long_description=open('README').read(),
    #~ install_requires=[],
    cmdclass=cmdclass,
    command_options=command_options,
)
