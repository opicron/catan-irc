# client.py - Fixed version with active_channel switch after join

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
        self.active_channel = self.lobby_channel  # New: active target channel
        self.running = True
        self.host_process = None

    def on_welcome(self, connection, event):
        print("[DEBUG] on_welcome: joining lobby {}".format(self.lobby_channel))
        connection.join(self.lobby_channel)

    def on_pubmsg(self, connection, event):
        sender = NickMask(event.source).nick
        msg = event.arguments[0].strip()
        print("[DEBUG] Public message from {}: {}".format(sender, msg))
        if msg.startswith("HOST_AVAILABLE"):
            print("[CLIENT:{}] Host detected: {}".format(self.nick, msg))

    def on_invite(self, connection, event):
        inviter = NickMask(event.source).nick
        channel = event.arguments[0]
        print("[DEBUG] Invited by {} to {}".format(inviter, channel))
        connection.join(channel)
        print("[CLIENT:{}] Auto-joined {}".format(self.nick, channel))
        self.active_channel = channel  # Set active channel to game channel after join

    def on_nicknameinuse(self, connection, event):
        print("[DEBUG] Nickname '{}' already in use, appending '_'".format(self.nick))
        connection.nick(self.nick + "_")

    def on_disconnect(self, connection, event):
        print("[DEBUG] Disconnected from IRC")
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
                    else:
                        print("Usage: /join <username>")
                elif user_input == "/quit" or user_input == "/exit":
                    print("[CLIENT:{}] Exiting.".format(self.nick))
                    self.stop_host_process()
                    self.connection.quit("Client exiting.")
                    sys.exit(0)
                else:
                    # Send all input to active_channel
                    self.connection.privmsg(self.active_channel, user_input)
        except KeyboardInterrupt:
            print("[CLIENT:{}] Interrupted.".format(self.nick))
            self.stop_host_process()
            self.connection.quit("Interrupted.")
            sys.exit(0)

    def start_host_process(self):
        if not self.host_process:
            print("[CLIENT:{}] Starting host.py as subprocess.".format(self.nick))
            self.host_process = subprocess.Popen([sys.executable, "host.py", self.nick])
            time.sleep(2)  # Allow time for host to initialize
            self.connection.privmsg(self.lobby_channel, "/join {}".format(self.nick))
        else:
            print("[CLIENT:{}] Host already running.".format(self.nick))

    def stop_host_process(self):
        if self.host_process:
            print("[CLIENT:{}] Terminating host.py.".format(self.nick))
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
            print("[DEBUG] Connecting with SSL to {}:{}".format(server, port))
            factory = Factory(wrapper=ssl.wrap_socket)
        else:
            print("[DEBUG] Connecting with plain TCP to {}:{}".format(server, port))
            factory = None

        c.connect(server, port, nickname, connect_factory=factory)
    except ServerConnectionError as e:
        print("[ERROR] Connection failed: {}".format(e))
        sys.exit(1)

    threading.Thread(target=c.run_main_loop).start()
    c.start()

if __name__ == "__main__":
    main()
