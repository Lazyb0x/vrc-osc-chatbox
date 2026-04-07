import asyncio

from vrcchatbox.config import Config
from vrcchatbox.message import Message, MessageProcessor
from vrcchatbox.osc_client import OSCClient


def run_console(config: Config, ip: str, port: int):
    osc_client = OSCClient(ip, port)
    message_processor = MessageProcessor(config)

    buffer = []
    empty_count = 0
    prompt = True

    print("Enter message to send (or 'exit' to quit): ")
    try:
        while True:
            line = input("> " if prompt else "  ")
            if line.lower() in ("exit", "quit", "/q"):
                break

            if line == "":
                empty_count += 1
                if empty_count >= 1:
                    msg = "\n".join(buffer)
                    buffer = []
                    empty_count = 0
                    prompt = True

                    async def process_message():
                        final_msg = ""
                        async for out_msg in message_processor.process(Message(data=msg)):
                            final_msg = out_msg
                            osc_client.chatbox_input(out_msg)
                        print(final_msg)

                    asyncio.run(process_message())
            else:
                buffer.append(line)
                empty_count = 0
                prompt = False
    except KeyboardInterrupt:
        print("\nInterrupted.")
