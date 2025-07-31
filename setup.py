#!/usr/bin/env python3
"""
Setup script for E-commerce Analytics Pipeline
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ecommerce-analytics-pipeline",
    version="1.0.0",
    author="Data Engineering Team",
    author_email="data-engineering@example.com",
    description="A comprehensive e-commerce analytics pipeline with real-time streaming and batch processing",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/ecommerce-analytics-pipeline",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ecommerce-simulator=src.event_simulator.main:main",
            "ecommerce-streaming=src.spark_jobs.streaming_job:main",
            "ecommerce-data-quality=src.data_quality.validations:main",
            "ecommerce-db-setup=src.utils.setup_database:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yml", "*.yaml", "*.sql", "*.json"],
    },
) 