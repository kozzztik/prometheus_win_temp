import argparse
import pathlib
import time
import logging
import typing as t
import threading
import sys

import windowsservice

from prometheus_win_temp.monitor import Monitor
from prometheus_win_temp.config import Config

try:
    import sentry_sdk
except ModuleNotFoundError:
    sentry_sdk = None

logger = logging.getLogger(__name__)
DEFAULT_CONFIG_FILES = [
    pathlib.Path(__name__).parent / "config.toml",  # for python script
    pathlib.Path(sys.executable).parent / "config.toml",  # for py2exe executable
]


def print_metrics(monitor: Monitor) -> t.Iterator[None]:
    while True:
        monitor.update()
        yield
        print("\033[H\033[J", end="")
        print(monitor.get_bytes().decode().replace("\n", "\r\n"))


def out_file(monitor: Monitor, path: pathlib.Path) -> t.Iterator[None]:
    with path.open("bw") as f:
        # stamp = time.time()
        while True:
            monitor.update()
            f.seek(0)
            f.truncate()
            f.write(monitor.get_bytes())
            f.flush()
            yield 
            # stamp += period
            # sleep_time = max(stamp - time.time(), 0)
            # if sleep_time:
            #     time.sleep(sleep_time)


parser = argparse.ArgumentParser(description='Prometheus Windows temperature monitor')
parser.add_argument(
    'command',
    type=str,
    default='',
    nargs='?',
    choices=[
        # windows service commands
        'install', 'remove', 'update', 'start', 'restart', 'debug', '',
        # own commands
        'file'
    ],
    help='Action to perform'
)
parser.add_argument('-p', '--period', type=int, default=5, help='Period of monitoring')
parser.add_argument('-f', '--file', type=pathlib.Path, default=None, help='File to save data')
parser.add_argument('-c', '--config', type=str, default='', help='Path to config file')


class Service(windowsservice.BaseService):
    _svc_name_ = "prometheus-windows-exporter"
    _svc_display_name_ = "Prometheus Windows Exporter"
    _svc_description_ = "Addon to windows_exporting adding temperature and other hardware specific metrics"
    _svc_deps_ = ('windows_exporter',)

    stop_event = threading.Event()

    def start(self):
        # While service is not configured yet, log near executable.
        # Services have no stdout/stderr so it is an only way to have
        # any information about startup process.
        logging.basicConfig(
            filename=str(pathlib.Path(sys.executable).parent / "log.txt"),
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
        )
        logger.info("Starting application as service")

    def main(self):
        config, _ = configure()
        logger.info("Application configured and ready as service")

        monitor = Monitor()
        logger.info("Monitor created")
        if not config.file_path:
            raise NotImplementedError('File path not configured.')
        if not config.file_path.is_absolute():
            config.file_path = pathlib.Path.home() / config.file_path
        config.file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Starting file output to {}".format(config.file_path))
        iterator = out_file(monitor, config.file_path)

        try:
            while not self.stop_event.is_set():
                stamp = time.time()
                next(iterator)
                sleep_time = stamp + config.period - time.time()
                if sleep_time > 0:
                    self.stop_event.wait(sleep_time)
        except Exception:
            logger.exception("Unhandled exception")
            if sentry_sdk:
                sentry_sdk.capture_exception()
            raise

    def stop(self):
        self.stop_event.set()


def configure() -> tuple[Config, argparse.Namespace]:
    logger.info("Starting configuration")

    try:
        args = parser.parse_known_args()[0]
        logger.info("Parsed args")

        # load config file
        config = Config()
        if args.config:
            config.load(args.config)
            logger.info("loaded config {}".format(args.config))
        else:
            for path in DEFAULT_CONFIG_FILES:
                if path.exists():
                    config.load(path)
                    logger.info("loaded config {}".format(path))
                    break
            else:
                logger.info("Config not loaded")

        if config.log_file:
            logging.basicConfig(
                filename=config.log_file,
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s',
            )
            logger.info("Logging reconfigured.")

        # override config by command line options
        if args.file:
            config.file_path = args.file
        if args.period:
            config.period = args.period

        if config.sentry and sentry_sdk:
            logger.info("Init sentry")
            sentry_sdk.init(**config.sentry, auto_enabling_integrations=False, integrations=[])

        return config, args
    except BaseException:
        logger.exception("Unhandled exception")
        raise

def main():
    config, args = configure()

    monitor = Monitor()
    logger.info("Monitor created")

    if not args.command:
        logger.info("Start output to screen")
        iterator = print_metrics(monitor)
    elif args.command == 'file':
        if not config.file_path.is_absolute():
            config.file_path = pathlib.Path.home() / config.file_path
        config.file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Starting file output to {}".format(config.file_path))
        iterator = out_file(monitor, config.file_path)
    else:
        raise NotImplementedError

    logger.info("Application configured and ready as script")
    try:
        stamp = time.time()
        while True:
            next(iterator)
            stamp += config.period
            sleep_time = max(stamp - time.time(), 0)
            if sleep_time:
                time.sleep(sleep_time)
    except Exception:
        logger.exception("Unhandled exception")
        if sentry_sdk:
            sentry_sdk.capture_exception()
        raise

if __name__ == "__main__":
    main()