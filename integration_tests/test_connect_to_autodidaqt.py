from typing import Tuple

import argparse
import time
from multiprocessing import Process

import xarray as xr
from autodidaqt.core import CommandLineConfig
from autodidaqt_common.remote.config import RemoteConfiguration

from autodidaqt_receiver import Receiver
from integration_tests.common import run_from_daq_suite

ADDRESS = "tcp://127.0.0.1:13133"


def build(config: CommandLineConfig) -> Tuple[Process, Receiver]:
    receiver = Receiver(remote_config, None)
    print(f"Start the appropriate autodiDAQt instance at {config.remote_config.ui_address}")

    process = run_from_daq_suite("slow_scalar", config, redirect_output=False)
    receiver.connect(request_driving_rights=True)
    return process, receiver


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ui", action="store_true", help="Whether to use a UI for the attached client."
    )
    args = parser.parse_args()

    remote_config = RemoteConfiguration(ADDRESS)
    config = CommandLineConfig(headless=not args.ui, remote_config=remote_config)
    process, receiver = build(config)
    receiver.cli()

    process.kill()
    process.join()


def test_async_scanning():
    remote_config = RemoteConfiguration(ADDRESS)
    config = CommandLineConfig(headless=True, remote_config=remote_config)

    receiver = Receiver(remote_config, None)
    print(f"Start the appropriate autodiDAQt instance at {ADDRESS}")

    process = run_from_daq_suite("slow_scalar", config, redirect_output=False)
    receiver.connect(request_driving_rights=True)

    receiver.scan("dx Scan Fast", n_x=9)
    time.sleep(0.5)
    assert receiver.data is not None
    time.sleep(3)
    assert receiver.data is None
    assert len(receiver.history) == 1

    run = receiver.history[0]
    data = run.data
    assert isinstance(data, xr.Dataset)
    assert sorted(list(data.dims.keys())) == ["image-dim_0", "image-dim_1", "x"]
    assert len(data.coords["x"]) == 9

    process.kill()
    process.join()
