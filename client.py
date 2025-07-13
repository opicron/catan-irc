import ConfigParser
import ssl
import subprocess
import sys
import threading
import time
import os

from irc.client import SimpleIRCClient, NickMask, ServerConnectionError
from irc.connection import Factory

from ui import UI
from input import Input

class Client(SimpleIRCClient):
    def __init__(self, config, nickname):
        SimpleIRCClient.__init__(self)
        self.config = config
        self.nick = nickname
        self.lobby_channel = config.get('irc', 'channel')
        self.active_channel = self.lobby_channel
        self.running = True
        self.host_process = None
        self.ui = UI(self)

    def on_welcome(self, connection, event):
        connection.join(self.lobby_channel)

    def on_pubmsg(self, connection, event):
        sender = NickMask(event.source).nick
        msg = event.arguments[0].strip()
        channel = event.target  # The channel where the message was sent
        responses = self.ui.handle_server_message(channel, sender, msg)
        for resp in responses:
            self.send_user_input(resp)

    def on_invite(self, connection, event):
        channel = event.arguments[0]
        connection.join(channel)
        self.active_channel = channel

    def on_disconnect(self, connection, event):
        self.running = False
        sys.exit(0)

    def send_user_input(self, user_input):
        if user_input == "!start":
            self.start_host_process()
        elif user_input.startswith("!join"):
            parts = user_input.split(" ", 1)
            if len(parts) == 2:
                target_username = parts[1].strip()
                self.connection.privmsg(self.lobby_channel, "!join {}".format(target_username))
        elif user_input in ("!quit", "!exit"):
            self.stop_host_process()
            self.connection.quit("Client exiting.")
            sys.exit(0)
        else:
            self.connection.privmsg(self.active_channel, user_input)

    def shutdown(self):
        self.stop_host_process()
        self.connection.quit("Shutting down.")
        sys.exit(0)

    def start_host_process(self):
        if not self.host_process:
            self.host_process = subprocess.Popen([sys.executable, "host.py", self.nick])
            time.sleep(2)
            self.connection.privmsg(self.lobby_channel, "!join {}".format(self.nick))

    def stop_host_process(self):
        if self.host_process:
            self.host_process.terminate()
            self.host_process.wait()
            self.host_process = None

    def on_kick(self, connection, event):
        kicked_nick = event.arguments[0]
        channel = event.target
        if kicked_nick == self.nick:
            # Optionally, notify the UI
            if hasattr(self, "ui"):
                self.ui.add_message("[System] You were kicked from {}. Attempting to reconnect...".format(channel))
            time.sleep(2)  # Wait a moment before rejoining
            connection.join(channel)

def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    server = config.get('irc', 'server')
    port = config.getint('irc', 'port')
    ssl_enabled = config.getboolean('irc', 'ssl')

    #input_handler = Input()
    nickname = raw_input("Enter your nickname: ").strip()

    client = Client(config, nickname)

    try:
        if ssl_enabled:
            factory = Factory(wrapper=ssl.wrap_socket)
        else:
            factory = None
        client.connect(server, port, nickname, connect_factory=factory)
    except ServerConnectionError:
        sys.exit(1)

    #threading.Thread(target=client.user_input_loop).start()
    #client.start()

    # Start the IRC event loop in a background thread (Python 2.7 style)
    irc_thread = threading.Thread(target=client.start)
    irc_thread.daemon = True
    irc_thread.start()

    client.ui.run()  # <

if __name__ == "__main__":
    main()
