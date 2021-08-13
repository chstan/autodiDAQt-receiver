from typing import Optional

import importlib
from io import StringIO
from multiprocessing import Process
from pathlib import Path

import integration_tests.common
from autodidaqt_receiver.receiver import RemoteConfiguration

__all__ = [
    "run_from_daq_suite",
]

INTEGRATION_TEST_ROOT = (Path(__file__).parent / "..").resolve().absolute()
DAQ_SUITES = INTEGRATION_TEST_ROOT / "daq_suites"


def run_from_daq_suite(
    app_name: str, remote_config: Optional[RemoteConfiguration] = None, redirect_output: bool = True
) -> Process:
    """Runs an autodiDAQt application with the script name ``app_name``."""
    target = DAQ_SUITES / f"{app_name}.py"

    if not target.exists():
        all_options = "\n".join(
            [f"\t{p.stem}" for p in DAQ_SUITES.glob("*.py") if p.stem != "__init__"]
        )
        raise ValueError(
            f"Could not find DAQ application `{app_name}`.\nAvailable options are:\n\n{all_options}"
        )

    daq_app = importlib.import_module(
        f"integration_tests.daq_suites.{app_name}", integration_tests.common
    )

    if redirect_output:
        # redirect the client output, we get logs via the comms anyway
        stdout, stderr = StringIO(), StringIO()
    else:
        stdout, stderr = None, None

    daq_process = Process(target=daq_app.main, args=(remote_config, stdout, stderr), daemon=False)
    daq_process.start()

    return daq_process
