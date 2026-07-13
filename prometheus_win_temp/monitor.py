import pathlib

import prometheus_client
import clr

libre_lib_path = pathlib.Path(__name__).parent / 'libre' / 'LibreHardwareMonitorLib.dll'
clr.AddReference(str(libre_lib_path.absolute()))

REMOVE_SYMBOLS = '#()'


def get_computer():
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


class Monitor:
    def __init__(self, sensor_types = ('Temperature', 'SmallData', 'Load', 'Fan')):
        self.registry = prometheus_client.CollectorRegistry()
        self.computer = get_computer()
        self.sensors: dict[prometheus_client.Gauge, ...] = {}
        self.group_sensors: dict[str, prometheus_client.Gauge] = {}
        self.sensor_types = set(sensor_types)

        for hw in self.computer.Hardware:
            hw.Update()
            for sensor in hw.Sensors:
                self._found_sensor(hw, sensor)

    def _found_sensor(self, hw, sensor) -> None:
        if sensor.SensorType.ToString() not in self.sensor_types:
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
        self.sensors[
            base_metric.labels(
                hardware=hw.Name,
                hw_type=hw.HardwareType.ToString(),
                sensor=sensor.SensorType.ToString(),
                index=sensor.Index
            )
        ] = sensor


    def update(self) -> None:
        for hw in self.computer.Hardware:
            hw.Update()
        for metric, sensor in self.sensors.items():
            metric.set(sensor.Value)

    def get_bytes(self) -> bytes:
        return prometheus_client.generate_latest(registry=self.registry)
