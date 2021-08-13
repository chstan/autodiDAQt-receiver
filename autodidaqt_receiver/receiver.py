from typing import Any, DefaultDict, Dict, Iterator, List, Optional

import datetime
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pynng
import xarray as xr
from autodidaqt_common.collation import Collation, CollationInfo
from autodidaqt_common.path import AxisPath
from autodidaqt_common.remote.command import (
    AllState,
    AxisRead,
    GetAllStateCommand,
    HeartbeatCommand,
    Log,
    ReadAxisCommand,
    RecordData,
    RunSummary,
    SetScanConfigCommand,
    StartRunCommand,
    WriteAxisCommand,
)
from autodidaqt_common.remote.middleware import (
    Middleware,
    TranslateCommandsMiddleware,
    WireMiddleware,
)
from autodidaqt_common.remote.schema import (
    RemoteApplicationState,
    RemoteAxisState,
    RemoteExperimentState,
    RemoteInstrumentState,
    TypeDefinition,
    Value,
)
from autodidaqt_common.remote.socket import AsyncUnbufferedSocket

from autodidaqt_receiver.repl import hotfix_prompt_toolkit_windows

hotfix_prompt_toolkit_windows()

import ptpython.repl
from autodidaqt_common.remote.config import RemoteConfiguration

__all__ = [
    "RemoteConfiguration",
    "Receiver",
]


@dataclass
class HeartbeatInfo:
    ping_ms: float


@dataclass
class ScanRepresentation:
    type_def: TypeDefinition

    @property
    def name(self):
        return self.type_def.name


@dataclass
class AxisRepresentation:
    instrument_name: str
    state: RemoteAxisState
    value: Any
    normalized_value: Value

    def set(self, v: Value):
        self.normalized_value = v
        self.value = v.to_instance()


@dataclass
class AxisTable:
    """Representation of the remote axes and acquisition hardware."""

    axes: Dict[str, AxisRepresentation] = field(default_factory=dict)

    def __getitem__(self, key):
        return self.axes[AxisPath.to_tuple(key)]

    def __setitem__(self, key, value):
        self.axes[AxisPath.to_tuple(key)] = value

    def record(self, data_message: RecordData):
        path = AxisPath.to_tuple(data_message.path)
        self[path].set(data_message.value)


@dataclass
class MessageReceipt:
    message: Any
    receipt_time: datetime.datetime = field(default_factory=datetime.datetime.now)


@dataclass
class Connection:
    """Maintains a connection to the remote instrumentation."""

    remote_configuration: RemoteConfiguration
    request_driving_rights: bool

    middleware: List[Middleware] = field(default_factory=list)
    socket: AsyncUnbufferedSocket = field(init=False)
    raw_socket: pynng.Pair1 = field(init=False)
    unhandled_messages: Dict[type, List[MessageReceipt]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def newest_message(self) -> Optional[Any]:
        """Fetches the earliest pending message.

        Each queue organized by type is sorted by increasing arrival time, so we
        only need to check the heads of each queue to find the earliest one.
        """
        earliest_type = None
        earliest_time = None

        for message_type, messages in self.unhandled_messages.items():
            if messages:
                first_of_type = messages[0]
                if earliest_time is None or first_of_type.receipt_time < earliest_time:
                    earliest_time = first_of_type.receipt_time
                    earliest_type = message_type

        if earliest_type is None:
            return None

        receipt = self.unhandled_messages[earliest_type][0]
        self.unhandled_messages[earliest_type] = self.unhandled_messages[earliest_type][1:]
        return receipt.message

    def messages_by_arrival(self) -> Iterator[Any]:
        """Iterate through all messages by their arrival time."""
        while True:
            message = self.newest_message()
            if message is None:
                # try running an acquisition and if there are still none,
                # then we are through, otherwise continue reading
                self.acquire_messages()
                message = self.newest_message()
                if message is None:
                    return

            yield message

    def __post_init__(self):
        self.connect()

    def __del__(self):
        self.close()

    def close(self):
        if self.raw_socket:
            self.raw_socket.close()
            self.raw_socket = None

    def connect(self):
        self.raw_socket = pynng.Pair1(listen=self.remote_configuration.ui_address)
        self.socket = AsyncUnbufferedSocket(self.raw_socket, middleware=self.middleware)

    def acquire_messages(self, sleep=None):
        if sleep is not None:
            time.sleep(sleep)
        while True:
            try:
                message = self.socket.recv(block=False)
                if isinstance(message, Log):
                    # logger.info(message.msg)
                    continue

                self.unhandled_messages[type(message)].append(MessageReceipt(message))

            except pynng.TryAgain:
                break

    def wait_for_message_of_type(self, message_type: type, sleep=1.0) -> Optional[Any]:
        if message_type == Log:
            raise ValueError("Cannot wait for a log as they are handled at read time.")

        tick = 0.005
        message = None
        while True:
            if self.unhandled_messages[message_type]:
                message = self.unhandled_messages[message_type][0].message
                self.unhandled_messages[message_type] = self.unhandled_messages[message_type][1:]
                break

            self.acquire_messages(sleep=None)
            time.sleep(tick)
            sleep -= tick
            if sleep < 0:
                break

        return message


@dataclass
class Run:
    """Represents the currently running acquisition."""

    scan_configuration: Optional[Any] = None
    collation: Optional[Collation] = None

    step: int = 0
    point: int = 0

    metadata: List[Dict[str, Any]] = field(default_factory=list)
    steps_taken: List[Dict[str, Any]] = field(default_factory=list)
    point_started: List[Dict[str, Any]] = field(default_factory=list)
    point_ended: List[Dict[str, Any]] = field(default_factory=list)
    daq_values: Dict[str, Any] = field(default_factory=lambda: defaultdict(list))

    # used for updating UI, represents the accumulated "flat" value
    # or the most recent value for
    streaming_daq_xs: Dict[str, DefaultDict[str, List]] = field(
        default_factory=lambda: defaultdict(list)
    )
    streaming_daq_ys: Dict[str, DefaultDict[str, List]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def collate(self, collation_info: CollationInfo):
        self.collation = collation_info.to_collation()

    def record(self, data_message: RecordData):
        data = data_message.value.to_instance()
        path = tuple(data_message.path)
        self.point = data_message.point
        self.step = data_message.step

        self.daq_values[path].append(
            {
                "data": data,
                "step": self.step,
                "point": self.point,
                "time": data_message.time,
            }
        )
        self.streaming_daq_xs[path].append(self.point)
        self.streaming_daq_ys[path].append(data)

        if self.collation:
            self.collation.receive(path, data)

    def to_xarray(self) -> xr.Dataset:
        assert self.collation is not None
        return self.collation.to_xarray(self.daq_values)

    @property
    def data(self):
        return self.to_xarray()


@dataclass
class Receiver:
    """The data and scan interface for interacting with autodiDAQt.

    Does not handle the details of connections or collection, but delegates
    these responsibilities. This provides only the high level interface
    which an experimenter interacts with in Jupyter.
    """

    remote_configuration: RemoteConfiguration
    data_path: Optional[Path] = None

    connection: Connection = field(init=False)
    axes: AxisTable = field(init=False)

    history: List[Run] = field(default_factory=list)
    run: Optional[Run] = None

    scan_methods: List[ScanRepresentation] = field(default_factory=list)

    _initial_state: Optional[RemoteApplicationState] = None

    def heartbeat(self) -> Optional[HeartbeatInfo]:
        """Checks whether the client is still attached."""

        sent_time = time.time()
        self.connection.socket.send(HeartbeatCommand())
        hb = self.connection.wait_for_message_of_type(HeartbeatCommand)
        if hb is not None:
            return HeartbeatInfo(ping_ms=1000 * (time.time() - sent_time))
        return None

    def cli(self):
        ptpython.repl.embed(
            globals(),
            {
                "receiver": self,
            },
        )

    def __post_init__(self):
        if isinstance(self.remote_configuration, str):
            self.remote_configuration = RemoteConfiguration(self.remote_configuration)

        self.axes = AxisTable()

    @property
    def location(self):
        the_location = {}
        for path, axis in self.axes.axes.items():
            if isinstance(axis.value, np.ndarray):
                continue
            the_location[AxisPath.to_natural_string(path)] = axis.value

        return the_location

    def connect(self, request_driving_rights: bool = True):
        """Begins the connection to the remote DAQ process.

        It's only sensible for one remote to control the acquisition,
        so we can specify whether we would like to kick the other
        receiver off the line if there is an existing connection.

        This will not prevent that receiver from being informed of data
        as it is provided, but only rescind its "driving privileges".

        Args:
            request_driving_rights: Whether we would like to assume the
                right to remotely sequence acquisition.
        """

        self.connection = Connection(
            self.remote_configuration,
            request_driving_rights,
            middleware=[
                TranslateCommandsMiddleware(),
                WireMiddleware(),
            ],
        )

        self.connection.socket.send(GetAllStateCommand())
        state: AllState = self.connection.wait_for_message_of_type(AllState)
        assert state is not None
        self._initial_state = state.state
        self.initialize_from_initial_experiment_state(state.state)

    def write(self, axis_path, value):
        axis_path = AxisPath.to_tuple(axis_path)
        axis: AxisRepresentation = self.axes[axis_path]
        type_def = TypeDefinition.get_definition_by_id(axis.state.schema)

        value = type_def.to_value(value)
        self.connection.socket.send(WriteAxisCommand(axis_path, value))

    def read(self, axis_path):
        axis_path = AxisPath.to_tuple(axis_path)
        self.connection.socket.send(ReadAxisCommand(axis_path))

    @property
    def data(self):
        self.catchup_on_messages()

        if self.run is None:
            return None

        if self.run.collation is None:
            return self.run.daq_values
        else:
            return self.run.to_xarray()

    def summarize(self):
        print("Instruments:")
        for ins_name in sorted(list(self._initial_state.instruments.keys())):
            print(f"\t{ins_name}")

        print("Axes:")
        for axis_path, axis in self.axes.axes.items():
            print(f"\t{axis_path}")
            print(f"\t\tValue: {axis.value}" + (" (Not populated)" if axis.value is None else ""))
            type_def = TypeDefinition.get_definition_by_id(axis.state.schema)
            print(f"\t\tSchema: {type_def.name}")
            if type_def.info is not None:
                print(f"\t\t\t{type_def.info}")
            if type_def.enum_fields is not None:
                print(f"\t\t\t{type_def.enum_fields}")

        print("Scans:")
        for scan_method in self.scan_methods:
            print(f"\t{scan_method.type_def.name}")
            print("\tFields")
            for _, field in scan_method.type_def.fields.items():
                print(f"\t\t{field.name}")
                type_def = TypeDefinition.get_definition_by_id(field.type_id)
                print(f"\t\t\tType: {type_def.name}")
                if type_def.info is not None:
                    print(f"\t\t\t{type_def.info}")
                if type_def.enum_fields is not None:
                    print(f"\t\t\t{type_def.enum_fields}")

    def build_scan_config(self, scan_name, *args, **kwargs) -> Any:
        if isinstance(scan_name, str):
            scan_reps = [s for s in self.scan_methods if s.name == scan_name]

            if len(scan_reps) != 1:
                raise ValueError(
                    f"No scan was found with matching name {scan_name} among {[s.name for s in self.scan_methods]}.\nUse one of these or an index."
                )

            scan_rep = scan_reps[0]
        else:
            scan_rep = self.scan_methods[scan_name]

        scan_type_def = scan_rep.type_def
        scan_type = scan_type_def.type

        scan = scan_type(*args, **kwargs)
        return scan

    def catchup_on_messages(self):
        for message in self.connection.messages_by_arrival():
            if isinstance(message, CollationInfo):
                if self.run is None:
                    self.run = Run()

                self.run.collate(message)
            elif isinstance(message, RecordData):
                self.run.record(message)
                self.axes.record(message)
            elif isinstance(message, RunSummary):
                self.finalize_run()
            elif isinstance(message, AxisRead):
                axis: AxisRepresentation = self.axes[message.axis_path]
                axis.set(message.value)
            else:
                print(message)

    def finalize_run(self):
        assert self.run is not None
        self.history.append(self.run)
        self.run = None

    def scan(self, scan_name, *args, **kwargs):
        config = self.build_scan_config(scan_name, *args, **kwargs)
        self.catchup_on_messages()
        if self.run is not None:
            raise ValueError(
                f"The experiment is currently running: {self.run}. Use `Receiver.queue` if you want to queue a scan to run later."
            )

        self.connection.socket.send(SetScanConfigCommand.from_scan_config(config))
        self.connection.socket.send(StartRunCommand())
        self.run = Run()
        print(f"Starting scan: {config}")
        print(f"You can access your data with `Receiver.run.data`.")

    def initialize_from_initial_experiment_state(self, state: RemoteApplicationState):
        """Builds axis representations, etc. from the initial experiment state."""
        for _, type_def in state.extra_types.items():
            try:
                TypeDefinition.get_definition_by_id(type_def.id)
            except KeyError:
                TypeDefinition.register_type_definition(type_def, type_def.hydrate_type())

        self.populate_axis_table(state.instruments)
        self.populate_experiment_state(state.experiment_state)

    def populate_experiment_state(self, state: RemoteExperimentState):
        self.scan_methods = [
            ScanRepresentation(TypeDefinition.get_definition_by_id(s)) for s in state.scan_methods
        ]

    def populate_axis_table(self, instruments: Dict[str, RemoteInstrumentState]):
        for instrument_name, ins in instruments.items():
            for axis in ins.flat_axes:
                self.axes[[instrument_name] + list(axis.path)] = AxisRepresentation(
                    instrument_name, axis, None, None
                )
