import ConfigParser
import ssl
import subprocess
import sys
import threading
import time

from irc.client import SimpleIRCClient, NickMask, ServerConnectionError
from irc.connection import Factory

from ui import UI

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
        responses = self.ui.handle_server_message(sender, msg)
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

    def user_input_loop(self):
        try:
            while True:
                user_input = raw_input("> ").strip()
                responses = self.ui.process_user_input(user_input)
                for resp in responses:
                    self.send_user_input(resp)
        except KeyboardInterrupt:
            self.shutdown()

def main():
    config = ConfigParser.ConfigParser()
    config.read('config.ini')
    server = config.get('irc', 'server')
    port = config.getint('irc', 'port')
    ssl_enabled = config.getboolean('irc', 'ssl')

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

    threading.Thread(target=client.user_input_loop).start()
    client.start()

if __name__ == "__main__":
    main()
