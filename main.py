import argparse
import atexit

from vrcchatbox.config import Config
from vrcchatbox.console import run_console
from vrcchatbox.server import run_server
from vrcchatbox.utils.logger import setup_logger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="127.0.0.1", help="The ip of the OSC server")
    parser.add_argument(
        "--port", type=int, default=9000, help="The port the OSC server is listening on"
    )
    parser.add_argument("--serve", action="store_true", help="Start server mode")
    parser.add_argument("--console", action="store_true", help="Start console mode")
    parser.add_argument(
        "--server-ip",
        default="0.0.0.0",
        help="Server address",
    )
    parser.add_argument(
        "--server-port",
        default=8000,
        type=int,
        help="Server port",
    )
    parser.add_argument(
        "--config",
        default="config.yml",
        help="Path to the YAML configuration file",
    )
    args = parser.parse_args()

    # 初始化配置
    config = Config(file_path=args.config)
    config.load()
    atexit.register(config.save)
    setup_logger(config)

    if not args.console:
        host, port = args.server_ip, args.server_port
        port = int(port)
        run_server(config, host, port, args.ip, args.port)
    else:
        run_console(config, args.ip, args.port)


if __name__ == "__main__":
    main()
