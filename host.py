# host.py - Final version with NAMES-based invite monitoring for Python 2.7 + irc==16.4

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
        self.present_nicks = set()

    def on_welcome(self, connection, event):
        print("[HOST:{}] on_welcome: joining lobby and creating {}".format(self.owner_username, self.game_channel))
        connection.join(self.lobby_channel)
        connection.join(self.game_channel)
        connection.mode(self.game_channel, "+i")
        print("[HOST:{}] {} set invite-only (+i)".format(self.owner_username, self.game_channel))
        self.start_broadcast_thread()
        self.start_invite_monitor_thread()

    def on_pubmsg(self, connection, event):
        sender = NickMask(event.source).nick
        msg = event.arguments[0].strip()
        print("[HOST:{}] Message from {}: {}".format(self.owner_username, sender, msg))
        expected_command = "/join {}".format(self.owner_username)
        if event.target == self.lobby_channel and msg == expected_command:
            print("[HOST:{}] Received /join {} from {}, sending invite immediately.".format(self.owner_username, self.owner_username, sender))
            self.send_invite(sender)

    def on_join(self, connection, event):
        nick = NickMask(event.source).nick
        channel = event.target
        if channel == self.game_channel:
            if nick not in self.players and nick != self.connection.get_nickname():
                self.players.add(nick)
                print("[HOST:{}] {} has joined game channel.".format(self.owner_username, nick))

    def send_invite(self, nick):
        print("[HOST:{}] Sending invite to {}".format(self.owner_username, nick))
        self.connection.invite(nick, self.game_channel)

    def start_invite_monitor_thread(self):
        def loop():
            while self.running:
                print("[HOST:{}] Requesting NAMES for {}".format(self.owner_username, self.game_channel))
                self.present_nicks.clear()
                self.connection.names(self.game_channel)
                time.sleep(10)
        t = threading.Thread(target=loop)
        t.daemon = True
        t.start()

    def on_namreply(self, connection, event):
        channel = event.arguments[1]
        names = event.arguments[2].split()
        print("[HOST:{}] NAMES reply for {}: {}".format(self.owner_username, channel, names))
        for name in names:
            cleaned_name = name.lstrip("@+")
            self.present_nicks.add(cleaned_name)

    def on_endofnames(self, connection, event):
        print("[HOST:{}] End of NAMES list. Checking players.".format(self.owner_username))
        for player in self.players:
            if player not in self.present_nicks:
                print("[HOST:{}] Player {} missing from channel, sending invite.".format(self.owner_username, player))
                self.send_invite(player)

    def start_broadcast_thread(self):
        def loop():
            while self.running:
                visible_players = [nick for nick in self.players if nick != self.connection.get_nickname()]
                players_str = ', '.join(visible_players) if visible_players else 'None'
                self.connection.privmsg(
                    self.lobby_channel,
                    "HOST_AVAILABLE {} (Players: {})".format(self.owner_username, players_str)
                )
                print("[HOST:{}] Broadcast: HOST_AVAILABLE (Players: {})".format(self.owner_username, players_str))
                time.sleep(10)
        t = threading.Thread(target=loop)
        t.daemon = True
        t.start()

    def on_disconnect(self, connection, event):
        print("[HOST:{}] Disconnected from IRC".format(self.owner_username))
        sys.exit(0)

def main():
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
