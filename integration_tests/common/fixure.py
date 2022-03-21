from loguru import logger
from autodidaqt_receiver import RECEIVER_ROOT
from dataclasses import dataclass, field

import xarray as xr

@dataclass
class FixtureDriver:
    fixture_name: str

    _fixture_data: xr.DataArray = field(init=False)

    @property
    def data(self) -> xr.DataArray:
        return self._fixture_data

    @staticmethod
    def load_fixture(fixture_name):
        path_to_fixture = RECEIVER_ROOT / "fixtures" / fixture_name
        logger.info(f"Loading data fixture {path_to_fixture}'")
        assert path_to_fixture.exists()

        return xr.open_dataset(str(path_to_fixture), engine="zarr")

    def __post_init__(self):
        self._fixture_data = self.load_fixture(self.fixture_name)

        if len(self._fixture_data.data_vars) == 1:
            var_name = list(self._fixture_data.data_vars.keys())[0]
            self._fixture_data = self._fixture_data[var_name]

