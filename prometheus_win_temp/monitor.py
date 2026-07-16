import pathlib
import sys
import logging

import prometheus_client
import clr
import retry
import sentry_sdk

libre_lib_path = pathlib.Path('libre') / 'LibreHardwareMonitorLib.dll'
if not libre_lib_path.exists():
    # for py2exe library search
    libre_lib_path = pathlib.Path(sys.executable).parent / libre_lib_path
clr.AddReference(str(libre_lib_path.absolute()))

REMOVE_SYMBOLS = '#()'

logger = logging.getLogger(__name__)


@retry.retry(tries=5, delay=3)
def get_computer():
    try:
        from LibreHardwareMonitor import Hardware

        handle = Hardware.Computer()
        handle.IsMotherboardEnabled = True
        handle.IsCpuEnabled = True
        handle.IsMemoryEnabled = True
        handle.IsGpuEnabled = True
        handle.IsStorageEnabled = True
        handle.IsControllerEnabled = True
        handle.IsPowerMonitorEnabled = True
        handle.IsPsuEnabled = True
        handle.IsBatteryEnabled = False
        handle.IsNetworkEnabled = False
        handle.Open()
        return handle
    except Exception as e:
        logger.exception("Exception during Computer instance creation")
        sentry_sdk.capture_exception(e)
        raise

class Monitor:
    def __init__(self, sensor_types = ('Temperature', 'SmallData', 'Load', 'Fan')):
        self.sensor_types = set(sensor_types)
        self._init()

    @retry.retry(tries=5, delay=3)
    def _init(self):
        self.registry = prometheus_client.CollectorRegistry()
        self.computer = get_computer()
        self.sensors: dict[prometheus_client.Gauge, ...] = {}
        self.group_sensors: dict[str, prometheus_client.Gauge] = {}

        for hw in self.computer.Hardware:
            hw.Update()
            for sensor in hw.Sensors:
                self._found_sensor(hw, sensor)

    def _found_sensor(self, hw, sensor) -> None:
        if self.sensor_types and sensor.SensorType.ToString() not in self.sensor_types:
            return

        name = sensor.Name
        for char in REMOVE_SYMBOLS:
            name = name.replace(char, '')

        if not (base_metric := self.group_sensors.get(name)):
            self.group_sensors[name] = base_metric = prometheus_client.Gauge(
                name,
                '',
                labelnames=['hardware', 'hw_type', 'sensor', 'index'],
                registry=self.registry
            )
        metric = base_metric.labels(
            hardware=hw.Name,
            hw_type=hw.HardwareType.ToString(),
            sensor=sensor.SensorType.ToString(),
            index=sensor.Index
        )
        metric.set(sensor.Value)
        self.sensors[metric] = sensor

    @retry.retry(tries=5, delay=3)
    def update(self) -> None:
        try:
            for hw in self.computer.Hardware:
                hw.Update()
        except Exception as e:
            logger.exception("Exception during metrics update")
            sentry_sdk.capture_exception(e)
            # reinit sensors
            self._init()
            raise

        for metric, sensor in self.sensors.items():
            metric.set(sensor.Value)

    def get_bytes(self) -> bytes:
        return prometheus_client.generate_latest(registry=self.registry)
