from importlib.metadata import entry_points
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pydecibel",
    version="0.1.0",
    author="Johan Jatko",
    author_email="armedguy@ludd.ltu.se",
    description="Turn your infrastructure up to eleven!",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ArmedGuy/decibel",
    packages=setuptools.find_packages(
        where='src'
    ),
    package_dir={"": "src"},
    entry_points= {
        "console_scripts": ["decibel=decibel.cli:main"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=[
        "PyYAML>=5.3.1"
    ]
)