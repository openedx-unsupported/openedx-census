#!/usr/bin/env python3
"""Install the Open edX census tool."""

from setuptools import setup


def load_requirements(*requirements_paths):
    """
    Load all requirements from the specified requirements files.
    Returns a list of requirement strings.
    """
    requirements = set()
    for path in requirements_paths:
        with open(path) as reqs:
            requirements.update(
                line.split('#')[0].strip() for line in reqs
                if is_requirement(line.strip())
            )
    return list(requirements)


def is_requirement(line):
    """
    Return True if the requirement line is a package requirement;
    that is, it is not blank, a comment, a URL, or an included file.
    """
    return line and not line.startswith(('-r', '#', '-e', 'git+', '-c'))


setup(
    name='openedx-census',
    version='0.2.1',
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
        'Programming Language :: Python :: 3.8',

    ],
    install_requires=load_requirements('requirements/base.in'),
    tests_require=load_requirements('requirements/test.in'),
    entry_points='''
        [console_scripts]
        census=census.census:cli
    ''',
)
