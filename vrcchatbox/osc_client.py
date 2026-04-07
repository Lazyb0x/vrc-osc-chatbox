import logging

from pythonosc import udp_client

logger = logging.getLogger(__name__)


class OSCClient:

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.client = udp_client.SimpleUDPClient(ip, port)

    def chatbox_input(self, message: str, bypass_keyboard=True, notify=True):
        log_msg = message.replace("\n", "\\n")
        logger.debug(f"Sending to OSC: {log_msg}")
        self.client.send_message("/chatbox/input", [message, bypass_keyboard, notify])
