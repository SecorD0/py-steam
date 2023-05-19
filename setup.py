import os

from setuptools import setup, find_packages

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md'), encoding='utf-8') as fh:
    long_description = '\n' + fh.read()

setup(
    name='py-steam',
    version='1.2.0',
    license='Apache-2.0',
    author='SecorD',
    description='',
    long_description_content_type='text/markdown',
    long_description=long_description,
    packages=find_packages(),
    install_requires=[
        'beautifulsoup4', 'fake-useragent', 'lxml', 'pretty-utils @ git+https://github.com/SecorD0/pretty-utils@main',
        'pycryptodome', 'requests'
    ],
    keywords=['steam', 'steam trade', 'csgo', 'dota', 'dota2', 'dota 2'],
)
