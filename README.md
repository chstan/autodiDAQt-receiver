# autodidaqt-receiver

<div align="center">

[![Build status](https://github.com/chstan/autodidaqt-receiver/workflows/build/badge.svg?branch=master&event=push)](https://github.com/chstan/autodidaqt-receiver/actions?query=workflow%3Abuild)
[![Python Version](https://img.shields.io/pypi/pyversions/autodidaqt-receiver.svg)](https://pypi.org/project/autodidaqt-receiver/)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/github/license/chstan/autodidaqt-receiver)](https://github.com/chstan/autodidaqt-receiver/blob/master/LICENSE)

Analyis-side bridge for autodiDAQt.

</div>

## Installation

```bash
pip install -U autodidaqt-receiver
```

or install with `Poetry`

```bash
poetry add autodidaqt-receiver
```

## Building and releasing

Building a new version of the application contains steps:

- Bump the version of your package `poetry version <version>`. You can pass the new version explicitly, or a rule such as `major`, `minor`, or `patch`. For more details, refer to the [Semantic Versions](https://semver.org/) standard.
- Make a commit to `GitHub`.
- Create a `GitHub release`.
- Publish `poetry publish --build`
