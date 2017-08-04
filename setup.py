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
requirements = ['requests', 'click']
        
setup(
    name='esmcheckds2',
    version='0.0.1',
    description="Queries McAfee ESM v9.x or v10.x for inactive data sources.",
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
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only'],
    #test_suite='tests',
    #tests_require=test_requirements,
    python_requires='>=3')
