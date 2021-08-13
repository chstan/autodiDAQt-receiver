# type: ignore[attr-defined]
"""Analyis-side bridge for autodiDAQt."""

import sys

from .receiver import *

if sys.version_info >= (3, 8):
    from importlib import metadata as importlib_metadata
else:
    import importlib_metadata


def get_version() -> str:
    try:
        return importlib_metadata.version(__name__)
    except importlib_metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"


version: str = get_version()
VERSION: str = version
__version__: str = version
