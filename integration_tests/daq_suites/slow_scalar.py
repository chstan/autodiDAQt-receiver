from typing import Optional, TextIO

import asyncio
import sys

import numpy as np
from autodidaqt import AutodiDAQt
from autodidaqt.core import CommandLineConfig
from autodidaqt.experiment import Experiment
from autodidaqt.instrument import ManagedInstrument
from autodidaqt.instrument.spec import AxisSpecification
from autodidaqt.mock import MockMotionController
from autodidaqt.scan import scan
from autodidaqt_common.schema import ArrayType


class AsyncDriver:
    async def read_image(self):
        await asyncio.sleep(2.0)
        return np.random.random((100, 100))

    async def read_scalar(self):
        await asyncio.sleep(0.5)
        return float(np.random.random() + 3)

    async def read_image_fast(self):
        await asyncio.sleep(0.1)
        return np.random.random((100, 100))

    async def read_scalar_fast(self):
        await asyncio.sleep(0.1)
        return float(np.random.random() + 3)


class ImageDetector(ManagedInstrument):
    driver_cls = AsyncDriver
    image = AxisSpecification(ArrayType([100, 100], float), where=["read_image"])
    image_fast = AxisSpecification(ArrayType([100, 100], float), where=["read_image_fast"])
    value = AxisSpecification(float, where=["read_scalar"])
    value_fast = AxisSpecification(float, where=["read_scalar_fast"])


dx = MockMotionController.scan("mc").stages[0]()
dy = MockMotionController.scan("mc").stages[1]()
dz = MockMotionController.scan("mc").stages[2]()


class MyExperiment(Experiment):
    scan_methods = [
        scan(x=dx, name="dx Scan", read={"image": "sensor.image", "value": "sensor.value"}),
        scan(x=dx, y=dy, z=dz, name="dx-dy-dz Scan", read={"value": "sensor.value"}),
        # for programmatic testing, so we don't wait (comparatively) forever.
        scan(
            x=dx,
            name="dx Scan Fast",
            read={"image": "sensor.image_fast", "value": "sensor.value_fast"},
        ),
    ]


def main(
    cli_config: Optional[CommandLineConfig] = None,
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
):
    """This is broken out to function as an import hook."""
    if stderr:
        sys.stderr = stderr

    if stdout:
        sys.stdout = stdout

    app = AutodiDAQt(
        __name__,
        {},
        {"experiment": MyExperiment},
        {"mc": MockMotionController, "sensor": ImageDetector},
    )

    if cli_config:
        app.configure_as_headless(cli_config)

    app.config._cached_settings["instruments"]["simulate_instruments"] = False
    app.start()


if __name__ == "__main__":
    main()
