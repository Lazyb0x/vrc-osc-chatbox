import logging

from pythonosc import udp_client

logger = logging.getLogger(__name__)


class OSCClient:

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.client = udp_client.SimpleUDPClient(ip, port)

    def chatbox_input(self, message, bypass_keyboard=True, notify=True):
        logger.debug(f"Sending to OSC: {message}")
        self.client.send_message("/chatbox/input", [message, bypass_keyboard, notify])
