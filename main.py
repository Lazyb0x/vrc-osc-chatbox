import argparse
import atexit
import logging

from vrcchatbox.config import Config
from vrcchatbox.console import run_console
from vrcchatbox.server import run_server
from vrcchatbox.utils.logger import setup_logger

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="Start server mode (default)")
    parser.add_argument("--console", action="store_true", help="Start console mode")
    parser.add_argument("--config", help="Path to the YAML configuration file")
    parser.add_argument("--osc-host", help="The address of the OSC server")
    parser.add_argument("--osc-port", type=int, help="The port the OSC server is listening on")
    parser.add_argument("--server-host", help="Web server address")
    parser.add_argument("--server-port", type=int, help="Web server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    setup_logger(logging_level= "DEBUG" if args.debug else None)
    config = Config(file_path=args.config)
    config.load()
    atexit.register(config.save)
    
    host = args.server_host or config.base.host
    port = args.server_port or config.base.port
    osc_host = args.osc_host or config.base.osc_host
    osc_port = args.osc_port or config.base.osc_port

    if not args.console:
        run_server(config, host, port, osc_host, osc_port)
    else:
        run_console(config, osc_host, osc_port)


if __name__ == "__main__":
    main()
