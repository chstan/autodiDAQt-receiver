# autodidaqt-receiver

<div align="center">

[![Build status](https://github.com/chstan/autodidaqt-receiver/workflows/build/badge.svg?branch=master&event=push)](https://github.com/chstan/autodidaqt-receiver/actions?query=workflow%3Abuild)
[![Python Version](https://img.shields.io/pypi/pyversions/autodidaqt-receiver.svg)](https://pypi.org/project/autodidaqt-receiver/)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/github/license/chstan/autodidaqt-receiver)](https://github.com/chstan/autodidaqt-receiver/blob/master/LICENSE)

Analysis-side bridge for AutodiDAQt.

</div>

## Installation

```bash
pip install -U autodidaqt-receiver
```

or install with `Poetry`

```bash
poetry add autodidaqt-receiver
```

## Installation from Source

1. Clone this repository
2. Install `make` if you are on a Windows system
3. Install `poetry` (the alternative Python package manager)
4. Run `make install` from the directory containing this README

## Building and releasing

Building a new version of the application contains steps:

- Bump the version of your package `poetry version <version>`. You can pass the new version explicitly, or a rule such as `major`, `minor`, or `patch`. For more details, refer to the [Semantic Versions](https://semver.org/) standard.
- Make a commit to `GitHub`.
- Create a `GitHub release`.
- Publish `poetry publish --build`
