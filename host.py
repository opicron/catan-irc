# host.py - Uses GameState from game.py for simple round /pass based game

import ConfigParser
import ssl
import sys
import threading
import time

from irc.client import SimpleIRCClient, NickMask, ServerConnectionError
from irc.connection import Factory

from game import GameState  # Import our separated game logic

class HostBot(SimpleIRCClient):
    def __init__(self, config, owner_username):
        SimpleIRCClient.__init__(self)
        self.config = config
        self.owner_username = owner_username
        self.lobby_channel = config.get('irc', 'channel')
        self.game_channel = "&catan-game-{}".format(owner_username)
        self.running = True
        self.present_nicks = set()

        self.game = GameState()

    def on_welcome(self, connection, event):
        print("[HOST:{}] on_welcome: joining lobby and creating {}".format(self.owner_username, self.game_channel))
        connection.join(self.lobby_channel)
        connection.join(self.game_channel)
        connection.mode(self.game_channel, "+i")
        self.start_broadcast_thread()
        self.start_invite_monitor_thread()

    def on_pubmsg(self, connection, event):
        sender = NickMask(event.source).nick
        msg = event.arguments[0].strip()

        if event.target == self.lobby_channel and msg == "/join {}".format(self.owner_username):
            self.send_invite(sender)
        elif event.target == self.game_channel:
            if msg == "/game":
                print("[DEBUG] /game from {} (channel {})".format(sender, event.target))
                print("[DEBUG] Players known: {}".format(self.game.players))
                if sender in self.game.players and not self.game.game_active:
                    ready = self.game.mark_ready(sender)
                    self.connection.privmsg(self.game_channel, "{} is ready.".format(sender))
                    if ready:
                        self.start_game()
            elif msg == "/pass":
                if self.game.game_active and sender == self.game.current_player():
                    if not self.game.next_turn():
                        self.end_game()
                    else:
                        self.prompt_current_player()
            else:
                self.connection.privmsg(self.game_channel, "{}: {}".format(sender, msg))

    def on_join(self, connection, event):
        nick = NickMask(event.source).nick
        channel = event.target
        if channel == self.game_channel and nick != self.connection.get_nickname():
            self.game.add_player(nick)
            print("[HOST:{}] {} joined game.".format(self.owner_username, nick))

    def send_invite(self, nick):
        print("[HOST:{}] Sending invite to {}".format(self.owner_username, nick))
        self.connection.invite(nick, self.game_channel)

    def start_broadcast_thread(self):
        def loop():
            while self.running:
                visible_players = [p for p in self.game.players if p != self.connection.get_nickname()]
                players_str = ', '.join(visible_players) if visible_players else 'None'
                self.connection.privmsg(self.lobby_channel, "HOST_AVAILABLE {} (Players: {})".format(self.owner_username, players_str))
                time.sleep(10)
        t = threading.Thread(target=loop)
        t.daemon = True
        t.start()

    def start_invite_monitor_thread(self):
        def loop():
            while self.running:
                self.present_nicks.clear()
                self.connection.names(self.game_channel)
                time.sleep(10)
        t = threading.Thread(target=loop)
        t.daemon = True
        t.start()

    def on_namreply(self, connection, event):
        names = event.arguments[2].split()
        for name in names:
            cleaned = name.lstrip("@+")
            self.present_nicks.add(cleaned)

    def on_endofnames(self, connection, event):
        for player in self.game.players:
            if player not in self.present_nicks:
                self.send_invite(player)

    def start_game(self):
        self.game.start()
        self.connection.privmsg(self.game_channel, "Game started! Turn order: {}".format(", ".join(self.game.turn_order)))
        self.prompt_current_player()

    def prompt_current_player(self):
        current = self.game.current_player()
        if current:
            self.connection.privmsg(self.game_channel, "It's {}'s turn. Type /pass to end your turn.".format(current))

    def end_game(self):
        self.connection.privmsg(self.game_channel, "Game over! Thanks for playing.")
        self.game.reset()

    def on_disconnect(self, connection, event):
        print("[HOST:{}] Disconnected from IRC".format(self.owner_username))
        self.running = False  # <--- Ensure threads exit gracefully
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
            factory = Factory(wrapper=ssl.wrap_socket)
        else:
            factory = None
        c.connect(server, port, nick, connect_factory=factory)
    except ServerConnectionError as e:
        print("[HOST:{} ERROR] Connection failed: {}".format(owner_username, e))
        sys.exit(1)

    c.start()

if __name__ == "__main__":
    main()
