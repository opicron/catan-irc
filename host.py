# host.py - Final version for Python 2.7 + irc==16.4
import ConfigParser
import ssl
import sys
import threading
import time

from irc.client import SimpleIRCClient, NickMask, ServerConnectionError
from irc.connection import Factory

class HostBot(SimpleIRCClient):
    def __init__(self, config, owner_username):
        SimpleIRCClient.__init__(self)
        self.config = config
        self.owner_username = owner_username
        self.lobby_channel = config.get('irc', 'channel')
        self.game_channel = "&catan-game-{}".format(owner_username)
        self.players = set()
        self.running = True

    def on_welcome(self, connection, event):
        print("[HOST:{}] on_welcome: joining lobby and creating {}".format(self.owner_username, self.game_channel))
        connection.join(self.lobby_channel)
        connection.join(self.game_channel)
        connection.mode(self.game_channel, "+i")
        print("[HOST:{}] {} set invite-only (+i)".format(self.owner_username, self.game_channel))
        self.start_broadcast_thread()

    def on_pubmsg(self, connection, event):
        sender = NickMask(event.source).nick
        msg = event.arguments[0].strip()
        print("[HOST:{}] Message from {}: {}".format(self.owner_username, sender, msg))
        expected_command = "/join {}".format(self.owner_username)
        if event.target == self.lobby_channel and msg == expected_command:
            if sender not in self.players:
                self.players.add(sender)
                print("[HOST:{}] {} joining game.".format(self.owner_username, sender))
                connection.privmsg(self.lobby_channel, "[HOST:{}] {} is joining the game.".format(self.owner_username, sender))
                connection.invite(sender, self.game_channel)

    def on_disconnect(self, connection, event):
        print("[HOST:{}] Disconnected from IRC".format(self.owner_username))
        sys.exit(0)

    def start_broadcast_thread(self):
        def loop():
            while self.running:
                players = ', '.join(self.players) if self.players else 'None'
                self.connection.privmsg(self.lobby_channel, "HOST_AVAILABLE {} (Players: {})".format(self.owner_username, players))
                print("[HOST:{}] Broadcast: HOST_AVAILABLE (Players: {})".format(self.owner_username, players))
                time.sleep(5)

        t = threading.Thread(target=loop)
        t.daemon = True  # Python 2.7-compatible daemon flag
        t.start()

def main():
    # Accept username from client.py or fallback for manual testing
    if len(sys.argv) >= 2:
        owner_username = sys.argv[1]
    else:
        owner_username = raw_input("Enter owner username for this host: ").strip()

    config = ConfigParser.ConfigParser()
    config.read('config.ini')
    server = config.get('irc', 'server')
    port = config.getint('irc', 'port')
    ssl_enabled = config.getboolean('irc', 'ssl')

    nick = "HostBot_{}".format(owner_username)

    c = HostBot(config, owner_username)

    try:
        if ssl_enabled:
            print("[HOST:{}] SSL: {}:{}".format(owner_username, server, port))
            factory = Factory(wrapper=ssl.wrap_socket)
        else:
            print("[HOST:{}] TCP: {}:{}".format(owner_username, server, port))
            factory = None

        c.connect(server, port, nick, connect_factory=factory)
    except ServerConnectionError as e:
        print("[HOST:{} ERROR] Connection failed: {}".format(owner_username, e))
        sys.exit(1)

    c.start()

if __name__ == "__main__":
    main()
