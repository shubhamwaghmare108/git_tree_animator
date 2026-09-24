"""
Setup configuration for Git Tree Animator.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="git-tree-animator",
    version="0.1.0",
    author="Git Educator",
    description="Interactive Git visualization and simulation tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/shubhamwaghmare108/git_tree_animator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Topic :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "streamlit>=1.28.0",
        "plotly>=5.18.0",
        "pydantic>=2.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-mock>=3.12.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "git-tree-animator=run:main",
        ],
    },
)
