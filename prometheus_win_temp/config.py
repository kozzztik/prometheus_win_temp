import tomllib
import pathlib

class Config:
    sentry: dict
    file_path: pathlib.Path | None = None
    period: int = 5
    sensor_types: list[str] = ['Temperature', 'SmallData', 'Load']
    log_file: pathlib.Path | None = None

    def __init__(self):
        self.sentry = {}

    def load(self, file_path: pathlib.Path):
        with file_path.open('br') as f:
            data = tomllib.load(f)
        self.sentry = data.get('sentry') or {}

        file_path = data.get('file_path', None)
        if file_path:
            self.file_path = pathlib.Path(file_path)

        self.period = int(data.get('period', self.period))

        sensor_types = data.get('sensor_types', self.sensor_types)
        if isinstance(sensor_types, (list, tuple)):
            self.sensor_types = [str(sensor_type) for sensor_type in sensor_types]
        else:
            self.sensor_types = [str(sensor_types)]

        log_file = data.get('log_file', None)
        if log_file:
            self.log_file = pathlib.Path(log_file)
