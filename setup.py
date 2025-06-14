#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="gaudi-connection",
    version="1.0.0",
    description="Framework for testing connectivity between Gaudi devices",
    author="Habana Labs",
    packages=find_packages(),
    scripts=["bin/gaudi-connection-test"],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
