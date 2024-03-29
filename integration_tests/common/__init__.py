from typing import Optional
from dataclasses import dataclass

import importlib
from io import StringIO
from multiprocessing import Process
from pathlib import Path
from typing import Tuple

import integration_tests.common
from autodidaqt_receiver.receiver import RemoteConfiguration, Receiver
from autodidaqt.core import CommandLineConfig
from autodidaqt_common.remote.config import RemoteConfiguration

__all__ = [
    "Builder",
    "run_from_daq_suite",
]

INTEGRATION_TEST_ROOT = (Path(__file__).parent / "..").resolve().absolute()
DAQ_SUITES = INTEGRATION_TEST_ROOT / "daq_suites"

@dataclass
class Builder:
    suite_name: str

    def build(self, config: CommandLineConfig, remote_config: RemoteConfiguration) -> Tuple[Process, Receiver]:
        receiver = Receiver(remote_config, None)
        print(f"Start the appropriate autodiDAQt instance at {config.remote_config.ui_address}")

        process = run_from_daq_suite(self.suite_name, config, redirect_output=False)
        receiver.connect(request_driving_rights=True)
        return process, receiver


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
