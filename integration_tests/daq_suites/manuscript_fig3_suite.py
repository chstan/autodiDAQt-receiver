"""Integration test harness for manuscript Figure 3.

For the purposes of writing similar experiment code, you need only reproduce:
  1. The spectrometer driver, i.e. `NanoXPSLabDriver`
  2. The AutodiDAQt instrument, i.e. `NanoXPSLab`
  3. `MyExperiment` 
  4. `dx` and `dy`

However, you can also use this code to test acquisition schemes, as this
fixutre experiment will provide you with "realistic" nanoXPS data.
"""

from typing import Optional, TextIO
from dataclasses import dataclass

import asyncio
import warnings
import sys

import numpy as np
from autodidaqt import AutodiDAQt
from autodidaqt.core import CommandLineConfig
from autodidaqt.experiment import Experiment
from autodidaqt.instrument import ManagedInstrument, AxisSpecification
from autodidaqt.instrument.spec import AxisSpecification
from autodidaqt.scan import scan
from autodidaqt_common.schema import ArrayType

from ..common.fixure import FixtureDriver

@dataclass
class NanoXPSLabDriver(FixtureDriver):
    fixture_name: str = "nano_xps"

    x: float = 0
    y: float = 0

    def __post_init__(self):
        super().__post_init__()

        self.x = self.data.x.mean().item()
        self.y = self.data.y.mean().item()

    def sync_read_spectrum(self) -> np.ndarray:
        raw_arr = self.data.interp(coords={"x": self.x, "y": self.y}).values
        return np.nan_to_num(raw_arr)

    async def read_spectrum(self) -> np.ndarray:
        return self.sync_read_spectrum()


class NanoXPSLab(ManagedInstrument):
    driver_cls = NanoXPSLabDriver

    x = AxisSpecification(float, where=["x"])
    y = AxisSpecification(float, where=["y"])
    spectrum = AxisSpecification(ArrayType([95], float), where=["read_spectrum"])


dx = NanoXPSLab.scan("lab").x()
dy = NanoXPSLab.scan("lab").y()

class MyExperiment(Experiment):
    scan_methods = [
        scan(x=dx, y=dy, name="NanoXPS Scan", read={"spectrum": "lab.spectrum"}),
    ]


def main(
    cli_config: Optional[CommandLineConfig] = None,
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
):
    """This is broken out to function as an import hook."""
    warnings.filterwarnings("ignore")
    if stderr:
        sys.stderr = stderr

    if stdout:
        sys.stdout = stdout

    app = AutodiDAQt(
        __name__,
        {},
        {"experiment": MyExperiment},
        {"lab": NanoXPSLab},
    )

    if cli_config:
        app.configure_as_headless(cli_config)

    app.config._cached_settings["instruments"]["simulate_instruments"] = False
    app.start()


if __name__ == "__main__":
    main()
