# -*- coding: utf-8 -*-

import os
import sys
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

requirements = ['requests', 'prettytable', 'python-dateutil']
        
with open('README.rst') as readme_file:
    readme = readme_file.read()

exec(open('esmcheckds2/version.py').read())
        
setup(
    name='esmcheckds2',
    version=__version__,
    description="McAfee ESM Data Source Reporting",
    author="Andy Walden",
    author_email='aw@krakencodes.com',
    url='https://github.com/andywalden/esmcheckds2',
    packages=['esmcheckds2'],
    package_dir={'esmcheckds2': 'esmcheckds2'},
    entry_points = {'console_scripts': ['esmcheckds2=esmcheckds2.console:main']},
    include_package_data=True,
    install_requires=requirements,
    license="ISC",
    keywords='esmcheckds2',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only'],
    python_requires='>=3')
