#!/usr/bin/env python3
"""
Leonardo setup script
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = []
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="leonardo-ai",
    version="0.1.0",
    author="Leonardo Development Team",
    description="Voice-first AI assistant with comprehensive safety and learning capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/Leonardo-Y",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "gpu": ["nvidia-cublas-cu12>=12.0.0", "nvidia-cudnn-cu12>=8.9.0"],
        "dev": ["pytest>=7.4.0", "black>=23.10.0", "mypy>=1.7.0"],
    },
    entry_points={
        "console_scripts": [
            "leonardo=leonardo.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "leonardo": ["**/*.yaml", "**/*.json", "**/*.toml"],
    },
)

