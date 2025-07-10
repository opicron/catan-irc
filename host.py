# host.py - final version for Python 2.7 + irc==16.4 with Python 2.7-compatible threading
import ConfigParser
import ssl
import sys
import threading
import time

from irc.client import SimpleIRCClient, NickMask, ServerConnectionError
from irc.connection import Factory

class HostBot(SimpleIRCClient):
    def __init__(self, config):
        SimpleIRCClient.__init__(self)
        self.config = config
        self.lobby_channel = config.get('irc', 'channel')
        self.game_channel = "&catan-game"
        self.players = set()
        self.running = True

    def on_welcome(self, connection, event):
        print("[HOST] on_welcome: joining lobby and creating game channel")
        connection.join(self.lobby_channel)
        connection.join(self.game_channel)
        connection.mode(self.game_channel, "+i")
        print("[HOST] Set {} invite-only (+i)".format(self.game_channel))
        self.start_broadcast_thread()

    def on_pubmsg(self, connection, event):
        sender = NickMask(event.source).nick
        msg = event.arguments[0].strip()
        print("[HOST] Message from {}: {}".format(sender, msg))
        if event.target == self.lobby_channel and msg.startswith("/join"):
            if sender not in self.players:
                self.players.add(sender)
                print("[HOST] {} joining game.".format(sender))
                connection.privmsg(self.lobby_channel, "[HOST] {} is joining the game.".format(sender))
                connection.invite(sender, self.game_channel)

    def on_disconnect(self, connection, event):
        print("[HOST] Disconnected from IRC")
        sys.exit(0)

    def start_broadcast_thread(self):
        def loop():
            while self.running:
                players = ', '.join(self.players) if self.players else 'None'
                self.connection.privmsg(self.lobby_channel, "HOST_AVAILABLE (Players: {})".format(players))
                print("[HOST] Broadcast: HOST_AVAILABLE (Players: {})".format(players))
                time.sleep(5)

        t = threading.Thread(target=loop)
        t.daemon = True  # Python 2.7-compatible daemon flag
        t.start()

def main():
    config = ConfigParser.ConfigParser()
    config.read('config.ini')
    server = config.get('irc', 'server')
    port = config.getint('irc', 'port')
    ssl_enabled = config.getboolean('irc', 'ssl')

    nick = "HostBot"

    c = HostBot(config)

    try:
        if ssl_enabled:
            print("[HOST] Connecting with SSL to {}:{}".format(server, port))
            factory = Factory(wrapper=ssl.wrap_socket)
        else:
            print("[HOST] Connecting with plain TCP to {}:{}".format(server, port))
            factory = None

        c.connect(server, port, nick, connect_factory=factory)
    except ServerConnectionError as e:
        print("[HOST ERROR] Connection failed: {}".format(e))
        sys.exit(1)

    c.start()

if __name__ == "__main__":
    main()
