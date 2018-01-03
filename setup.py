# -*- coding: utf-8 -*-

import os
import sys
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
        
with open('README.rst') as readme_file:
    readme = readme_file.read()

#test_requirements = ['pytest', 'tox']
requirements = ['requests', 'prettytable']
        
setup(
    name='esmcheckds2',
    version='0.0.8',
    description="Queries McAfee ESM v9.6.x or v10.1.0+ for inactive data sources.",
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
        'Development Status :: 4 - Beta',
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
    #test_suite='tests',
    #tests_require=test_requirements,
    python_requires='>=3')
