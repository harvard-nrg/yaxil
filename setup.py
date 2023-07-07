import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

requires = [
    'requests',
    'pydicom',
    'natsort',
    'arrow',
    'pyaml',
    'lxml',
    'six',
    'jsonpath-ng'
]

test_requirements = [
    'pytest',
    'vcrpy'
]

about = dict()
with open(os.path.join(here, 'yaxil', '__version__.py'), 'r') as f:
    exec(f.read(), about)

setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__description__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    url=about['__url__'],
    packages=find_packages(),
    scripts=[
        'scripts/ArcGet.py',
        'scripts/xnat_auth'
    ],
    install_requires=requires,
    tests_require=test_requirements
)
