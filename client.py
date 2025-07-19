# -*- coding: cp437 -*-
# python 2.7 only

# client.py

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
from terminal import Terminal

class Client(SimpleIRCClient):
    def __init__(self, config):
        SimpleIRCClient.__init__(self)
        self.config = config
        self.nick = None
        self.lobby_channel = config.get('irc', 'channel')
        self.active_channel = self.lobby_channel
        #self.running = True
        self.host_process = None
        self.ui = None
    
    def connect_to_server(self):
        """Handle nickname input and server connection"""
        # Get nickname from user using Terminal
        try:
            terminal = Terminal()
            self.nick = terminal.getstr("Enter your nickname: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            sys.exit(0)
        
        # Initialize UI after we have a nickname
        self.ui = UI(self)
        terminal.clear()

        # Get connection parameters
        server = self.config.get('irc', 'server')
        port = self.config.getint('irc', 'port')
        ssl_enabled = self.config.getboolean('irc', 'ssl')
        
        # Connect to server
        try:
            if ssl_enabled:
                factory = Factory(wrapper=ssl.wrap_socket)
            else:
                factory = None
            self.connect(server, port, self.nick, connect_factory=factory)
            return True
        except ServerConnectionError:
            print("Failed to connect to IRC server")
            return False

    def on_welcome(self, connection, event):
        connection.join(self.lobby_channel)

    def on_pubmsg(self, connection, event):
        sender = NickMask(event.source).nick
        msg = event.arguments[0].strip()
        channel = event.target  # The channel where the message was sent

        # Listen for !host broadcasts from our own host
        expected_bot = "HostBot_{}".format(self.nick)
        if channel == self.lobby_channel and sender == expected_bot and msg.startswith("!host "):
            # Example: !host Alice (Players: Bob, Alice)
            import re
            m = re.match(r"!host (\S+) \(Players: (.*)\)", msg)
            if m:
                host_owner = m.group(1)
                players = [p.strip() for p in m.group(2).split(',') if p.strip()]
                if host_owner == self.nick:
                    if self.nick not in players:
                        self.ui.add_message("[System] Host {} is ready. Sending join request...".format(expected_bot))
                        self.send_user_input("!join {}".format(self.nick))
                        
        responses = self.ui.handle_server_message(channel, sender, msg)
        for resp in responses:
            self.send_user_input(resp)

    def on_invite(self, connection, event):
        channel = event.arguments[0]
        inviter = NickMask(event.source).nick
        self.ui.add_message("[System] Received invite from {} to join {}".format(inviter, channel))
        connection.join(channel)
        self.active_channel = channel
        self.ui.add_message("[System] Joined channel {} and set as active".format(channel))

    def on_disconnect(self, connection, event):
        #self.running = False
        self.stop_host_process()
        #self.connection.quit("Disconnected.") #already disconnected
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
            # Don't call connection.quit() to avoid triggering on_disconnect
            sys.exit(0)
        else:
            self.connection.privmsg(self.active_channel, user_input)

    def shutdown(self):
        print("[HOST:{}] Client from server.".format(self.nick))
        self.stop_host_process()
        self.connection.quit("Shutting down.")
        sys.exit(0)

    def start_host_process(self):
        if not self.host_process:
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            host_path = os.path.join(script_dir, 'host.py')
            self.ui.add_message("[System] Starting host process...")
            self.host_process = subprocess.Popen([sys.executable, host_path, self.nick])
            self.ui.add_message("[System] Host process started. Waiting for host to become available...")


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
            self.ui.add_message("[System] You were kicked from {}. Attempting to reconnect...".format(channel))
            time.sleep(2)  # Wait a moment before rejoining
            connection.join(channel)

    def on_ping(self, connection, event):
        self.ui.add_message("[System] Received PING from server. Responding with PONG.")
        connection.pong(event.target if hasattr(event, 'target') else None)

def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    
    client = Client(config)
    
    # Connect to server (includes nickname input)
    if not client.connect_to_server():
        sys.exit(1)

    # Start the IRC event loop in a background thread (Python 2.7 style)
    irc_thread = threading.Thread(target=client.start)
    irc_thread.daemon = False
    irc_thread.start()

    client.ui.run()

    irc_thread.join(timeout=4)
    # If the program still hangs, check for other non-daemon threads or blocking calls.

if __name__ == "__main__":
    main()
