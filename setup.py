"""
SimCraft package setup.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="simcraft",
    version="1.0.0",
    author="Bulent Soykan",
    author_email="",
    description="A discrete event simulation framework for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bulentsoykan/simcraft",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "sortedcontainers>=2.4.0",
        "numpy>=1.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
        "visualization": [
            "matplotlib>=3.5.0",
            "pandas>=1.4.0",
        ],
        "rl": [
            "torch>=2.0.0",
        ],
        "all": [
            "matplotlib>=3.5.0",
            "pandas>=1.4.0",
            "torch>=2.0.0",
            "pyyaml>=6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "simcraft-examples=simcraft.examples:run_examples",
        ],
    },
    keywords=[
        "simulation",
        "discrete-event",
        "DES",
        "modeling",
        "optimization",
        "reinforcement-learning",
        "manufacturing",
        "logistics",
    ],
    project_urls={
        "Bug Tracker": "https://github.com/bulentsoykan/simcraft/issues",
        "Documentation": "https://simcraft.readthedocs.io/",
        "Source Code": "https://github.com/bulentsoykan/simcraft",
    },
)
