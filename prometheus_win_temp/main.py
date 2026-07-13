import argparse
import pathlib
import time

from prometheus_win_temp.monitor import Monitor
from prometheus_win_temp.config import Config

try:
    import sentry_sdk
except ModuleNotFoundError:
    sentry_sdk = None

DEFAULT_CONFIG_FILE = pathlib.Path(__name__).parent / "config.toml"


def print_metrics(monitor: Monitor, period: int = 5):
    while True:
        monitor.update()
        time.sleep(period)
        print("\033[H\033[J", end="")
        print(monitor.get_bytes().decode().replace("\n", "\r\n"))


def out_file(monitor: Monitor, path: pathlib.Path, period: int = 5):
    with path.open("bw") as f:
        stamp = time.time()
        while True:
            monitor.update()
            f.seek(0)
            f.truncate()
            f.write(monitor.get_bytes())
            f.flush()

            stamp += period
            sleep_time = max(stamp - time.time(), 0)
            if sleep_time:
                time.sleep(sleep_time)


parser = argparse.ArgumentParser(description='Prometheus Windows temperature monitor')
parser.add_argument('-p', '--period', type=int, default=5, help='Period of monitoring')
parser.add_argument('-f', '--file', type=pathlib.Path, default=None, help='File to save data')
parser.add_argument('-c', '--config', type=str, default='', help='Path to config file')


def main():
    args = parser.parse_args()
    # load config file
    config = Config()
    if args.config:
        config.load(args.config)
    elif DEFAULT_CONFIG_FILE.exists():
        config.load(DEFAULT_CONFIG_FILE)

    # override config by command line options
    if args.file:
        config.file_path = args.file
    if args.period:
        config.period = args.period

    if config.sentry and sentry_sdk:
        sentry_sdk.init(**config.sentry)

    monitor = Monitor()
    if config.file_path:
        if not config.file_path.is_absolute():
            config.file_path = pathlib.Path.home() / config.file_path
        config.file_path.parent.mkdir(parents=True, exist_ok=True)
        out_file(monitor, config.file_path, period=config.period)
    else:
        print_metrics(monitor, period=config.period)


if __name__ == "__main__":
    main()