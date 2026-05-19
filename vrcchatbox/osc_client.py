import logging

from pythonosc import udp_client

logger = logging.getLogger(__name__)


class OSCClient:

    def __init__(self, host: str, port: int):
        self.ip = host
        self.port = port
        self.client = udp_client.SimpleUDPClient(host, port)

    def chatbox_input(self, message: str, bypass_keyboard=True, notify=True):
        log_msg = message.replace("\n", "\\n")
        logger.debug(f"Sending to OSC: {log_msg}")
        self.client.send_message("/chatbox/input", [message, bypass_keyboard, notify])

    def chatbox_typing(self, is_typing: bool = True):
        logger.debug(f"Sending to OSC: {is_typing}")
        self.client.send_message("/chatbox/typing", [is_typing])
