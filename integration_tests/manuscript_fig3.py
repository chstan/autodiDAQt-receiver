import argparse
import time
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import warnings
from pathlib import Path

from autodidaqt.core import CommandLineConfig
from autodidaqt_common.remote.config import RemoteConfiguration

from integration_tests.common import Builder
from integration_tests.common.increase_resolution import coordinates_for_mask, increase_resolution

def simple_plot(arr, name):
    SAVE_FIGURES = Path.home() / "autodidaqt_manuscript_example_figures".upper()
    SAVE_FIGURES.mkdir(exist_ok=True)

    _, ax = plt.subplots()
    arr.plot(ax=ax)
    plt.savefig(str(SAVE_FIGURES / name), dpi=200)

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser()
    parser.add_argument("--ui", action="store_true", help="Whether to use a UI.")
    args = parser.parse_args()

    remote_config = RemoteConfiguration("tcp://127.0.0.1:13133")
    config = CommandLineConfig(headless=not args.ui, remote_config=remote_config)
    process, receiver = Builder("manuscript_fig3_suite").build(config, remote_config)

    # for interactive tests, people don't need to see xarray noise
    ORIGINAL_SIZE, UPSCALE = 9, 3
    receiver.scan("NanoXPS Scan",
        start_x=0.085, stop_x=0.105, n_x=ORIGINAL_SIZE, 
        start_y=0.07, stop_y=0.095, n_y=ORIGINAL_SIZE, 
    )

    while len(receiver.history) == 0:
        _ = receiver.data
        print("Waiting for low resolution data from testbench.")
        time.sleep(0.1)

    print("Saving plot of the first scan.")
    lowres_data = receiver.history[0].data
    spectral_axis = lowres_data["spectrum-dim_0"]
    summed = lowres_data.spectrum.sum("spectrum-dim_0")
    simple_plot(summed, "lowres.png")

    print("Scanning at higher resolution.")
    mask = summed.values > np.percentile(summed.values, 80)
    mask_arr = xr.DataArray(mask, coords=summed.coords, dims=summed.dims)
    simple_plot(mask_arr, "mask.png")

    # prep an array so we can plot the output data from the example
    result_data = increase_resolution(mask_arr * 1., [], UPSCALE)
    result_data = xr.DataArray(
        np.zeros((ORIGINAL_SIZE * UPSCALE, ORIGINAL_SIZE * UPSCALE, len(spectral_axis))),
        coords={
            **result_data.coords,
            "spectrum-dim_0": spectral_axis,
        },
        dims=["x", "y", "spectrum-dim_0"]
    )

    # =========== DAQ STARTS HERE ========================
    # run a manual scan over just a small portion of the sample
    receiver.manual_scan()
    cs = list(coordinates_for_mask(mask_arr, UPSCALE))
    for i, c in enumerate(cs):
        # be explicit to show command expectation
        # move motors before reading
        receiver.point()
        receiver.step(
            writes=[
                ("lab.x", c["x"],),
                ("lab.y", c["y"],),
            ],
        )
        receiver.step(reads=["lab.spectrum"])

    receiver.finish_scan()
    # =============== DAQ ENDS HERE ========================

    while receiver.data is not None:
        print("Waiting for scan to finish")
        time.sleep(0.5)

    # put the data back together manually to show how to do this
    last_run = receiver.history[-1]
    result_data = result_data * np.nan
    for i, c in enumerate(cs):
        result_data.loc[c] = last_run.daq_values[("lab", "spectrum")][i]["data"]

    # Print the partially sampled results
    simple_plot(result_data.sum("spectrum-dim_0"), "sampled_highres.png")

    # cleanup
    process.kill()
    process.join()
