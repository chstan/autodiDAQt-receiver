"""
Implements generic rescanning over a masked area with increased resolution.

Masked edges are smoothed by flood filling.
"""

import itertools
import numpy as np
import xarray as xr

__all__ = [
    "coordinates_for_mask",
    "increase_resolution", 
    "flood_fill",
]

def coordinates_for_mask(mask, resolution_increase=2):
    mask = increase_resolution(mask * 1., [], resolution_increase)
    mask = (mask > 0.5) * 1 # handle the fact that we used interpolation
    mask_values = flood_fill(mask.values, resolution_increase)

    dims = mask.dims
    coords = [mask.coords[d].values for d in dims]
    coords_len = [len(c) for c in coords]

    for ci in itertools.product(*[range(ln) for ln in coords_len]):
        value = mask_values[ci]
        if not value:
            continue

        cs = [c[i] for c, i in zip(coords, ci)]
        yield {cname: c for cname, c in zip(dims, cs)}


def increase_resolution(arr: xr.DataArray, skip_coords=None, stride=2) -> xr.DataArray:
    """Increase the effective resolution of the array by interpolation."""
    if skip_coords is None:
        skip_coords = []

    resize_coords = [d for d in arr.dims if d not in skip_coords]
    resized = {}

    for cname in resize_coords:
        c = arr.coords[cname].values
        c0, dc, n = c[0], c[1] - c[0], len(c)

        cs = c0 + (dc / stride) * np.arange(n * stride)
        resized[cname] = cs

    return arr.interp(**resized)


def flood_fill(arr, n=1):
    """Performs a simple iterative floodfill."""
    im, jm = arr.shape

    for _ in range(n):
        output = np.copy(arr)
        for i in range(im):
            for j in range(jm):
                if arr[max(i - 1, 0), j] or arr[i, max(j-1, 0)] \
                    or arr[min(i + 1, im - 1), j] or arr[i, min(j+1, jm - 1)]:
                    output[i, j] = True
        
        arr = output
                
    return arr
