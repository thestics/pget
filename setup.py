#!/usr/bin/env python3
# -*-encoding: utf-8-*-
# Author: Danil Kovalenko


from setuptools import find_packages, setup

setup(
    name='pyget',
    packages=find_packages(),
    install_requires=['requests', 'tqdm'],
    version='0.1.0',
    description='Download files from the web',
    author='Danylo Kovalenko danil130999@gmail.com',
    license='MIT',
    entry_points={"console_scripts": ["pget=pyget.main:main"]}
)
