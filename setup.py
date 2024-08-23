"""A setuptools based setup module."""

from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="python3-cyberfusion-file-support",
    version="1.1.1.1",
    description="Library for idempotent writing to files.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Cyberfusion",
    author_email="support@cyberfusion.io",
    url="https://github.com/CyberfusionIO/python3-cyberfusion-file-support",
    platforms=["linux"],
    packages=["cyberfusion.FileSupport"],
    package_dir={"": "src"},
    data_files=[],
    install_requires=[
        "python3-cyberfusion-common~=2.0",
        "python3-cyberfusion-queue-support~=1.1",
    ],
)
