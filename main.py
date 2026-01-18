import argparse

from pythonosc import udp_client


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="127.0.0.1", help="The ip of the OSC server")
    parser.add_argument(
        "--port", type=int, default=9000, help="The port the OSC server is listening on"
    )
    args = parser.parse_args()

    client = udp_client.SimpleUDPClient(args.ip, args.port)

    bypass_keyboard = True  # b
    notify = True  # n

    buffer = []
    empty_count = 0
    prompt = True

    print("Enter message to send (or 'exit' to quit): ")
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
                client.send_message("/chatbox/input", [msg, bypass_keyboard, notify])
        else:
            buffer.append(line)
            empty_count = 0
            prompt = False


if __name__ == "__main__":
    main()
