from setuptools import setup, find_packages

setup(
    name="gaudi-connection",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "numpy",
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "pytest-cov>=4.1.0",
        ],
    },
    python_requires=">=3.6",
)