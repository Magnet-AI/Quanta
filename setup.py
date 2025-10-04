"""
Setup script for PDF Layout Analysis Engine
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
    name="pdf-layout-engine",
    version="1.0.0",
    author="PDF Layout Analysis Team",
    author_email="team@pdf-layout-engine.org",
    description="Advanced PDF layout analysis using computer vision and machine learning",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/pdf-layout-engine",
    project_urls={
        "Bug Reports": "https://github.com/your-org/pdf-layout-engine/issues",
        "Source": "https://github.com/your-org/pdf-layout-engine",
        "Documentation": "https://github.com/your-org/pdf-layout-engine/wiki",
    },
    packages=find_packages(),
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
        "Topic :: Scientific/Engineering :: Image Processing",
        "Topic :: Text Processing :: Markup",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Office/Business",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
            "pre-commit>=2.0",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=1.0",
            "myst-parser>=0.15",
        ],
        "jupyter": [
            "jupyter>=1.0",
            "ipywidgets>=7.0",
            "matplotlib>=3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pdf-layout-engine=src.cli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "pdf_layout_engine": [
            "data/*.json",
            "data/*.yaml",
            "templates/*.html",
        ],
    },
    keywords=[
        "pdf", "layout", "analysis", "computer-vision", "ocr", 
        "document-processing", "text-extraction", "figure-detection",
        "table-recognition", "machine-learning"
    ],
    zip_safe=False,
)
