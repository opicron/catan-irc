# client.py

import ConfigParser
import ssl
import subprocess
import sys
import threading
import time

from irc.client import SimpleIRCClient, Reactor, NickMask, ServerConnectionError
from irc.connection import Factory

class Client(SimpleIRCClient):
    def __init__(self, config, nickname):
        SimpleIRCClient.__init__(self)
        self.config = config
        self.nick = nickname
        self.lobby_channel = config.get('irc', 'channel')
        self.active_channel = self.lobby_channel
        self.running = True
        self.host_process = None

    def on_welcome(self, connection, event):
        connection.join(self.lobby_channel)

    def on_pubmsg(self, connection, event):
        sender = NickMask(event.source).nick
        msg = event.arguments[0].strip()
        print("[{}] {}: {}".format(event.target, sender, msg))

        if msg == "!game-start":
            print("[CLIENT:{}] Detected !game-start, ready to launch UI.".format(self.nick))
            # Placeholder for future UI trigger
            # self.show_ui()

    def on_invite(self, connection, event):
        channel = event.arguments[0]
        connection.join(channel)
        self.active_channel = channel

    def on_disconnect(self, connection, event):
        self.running = False
        sys.exit(0)

    def run_main_loop(self):
        try:
            while True:
                user_input = raw_input("> ").strip()
                if user_input == "/start":
                    self.start_host_process()
                elif user_input.startswith("/join"):
                    parts = user_input.split(" ", 1)
                    if len(parts) == 2:
                        target_username = parts[1].strip()
                        self.connection.privmsg(self.lobby_channel, "/join {}".format(target_username))
                elif user_input == "/quit" or user_input == "/exit":
                    self.stop_host_process()
                    self.connection.quit("Client exiting.")
                    sys.exit(0)
                else:
                    self.connection.privmsg(self.active_channel, user_input)
        except KeyboardInterrupt:
            self.stop_host_process()
            self.connection.quit("Interrupted.")
            sys.exit(0)

    def start_host_process(self):
        if not self.host_process:
            self.host_process = subprocess.Popen([sys.executable, "host.py", self.nick])
            time.sleep(2)
            self.connection.privmsg(self.lobby_channel, "/join {}".format(self.nick))

    def stop_host_process(self):
        if self.host_process:
            self.host_process.terminate()
            self.host_process.wait()
            self.host_process = None

def main():
    config = ConfigParser.ConfigParser()
    config.read('config.ini')
    server = config.get('irc', 'server')
    port = config.getint('irc', 'port')
    ssl_enabled = config.getboolean('irc', 'ssl')

    nickname = raw_input("Enter your nickname: ").strip()

    c = Client(config, nickname)

    try:
        if ssl_enabled:
            factory = Factory(wrapper=ssl.wrap_socket)
        else:
            factory = None
        c.connect(server, port, nickname, connect_factory=factory)
    except ServerConnectionError as e:
        sys.exit(1)

    threading.Thread(target=c.run_main_loop).start()
    c.start()

if __name__ == "__main__":
    main()
