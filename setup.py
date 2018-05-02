#!/usr/bin/env python3
"""Install the Open edX census tool."""

from setuptools import setup

setup(
    name='openedx-census',
    version='0.1.0',
    license='Apache 2',
    description='Open edX census tool',
    author='Ned Batchelder',
    author_email='ned@edx.org',
    url='https://open.edx.org',
    packages=['census'],
    zip_safe=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
    install_requires=[
        'affine',
        'click',
    ],
    entry_points='''
        [console_scripts]
        census=census.census:cli
    ''',
)
