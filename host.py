# host.py

import ConfigParser
import ssl
import sys
import threading
import time
import os

from irc.client import SimpleIRCClient, NickMask, ServerConnectionError
from irc.connection import Factory

from game import GameState

class Host(SimpleIRCClient):
    def __init__(self, config, owner_username):
        SimpleIRCClient.__init__(self)
        self.config = config
        self.owner_username = owner_username
        self.lobby_channel = config.get('irc', 'channel')
        self.game_channel = "&catan-game-{}".format(owner_username)
        self.running = True
        self.broadcast_running = True
        self.present_nicks = set()
        self.game = GameState()

    def debug_log(self, message):
        """Write debug messages to a log file since curses blocks stdout"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            log_path = os.path.join(script_dir, 'host_debug.log')
            with open(log_path, 'a') as f:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write("[{}] {}\n".format(timestamp, message))
        except:
            pass  # Ignore logging errors

    def on_welcome(self, connection, event):
        self.debug_log("[HOST:{}] Connected successfully! Joining channels...".format(self.owner_username))
        connection.join(self.lobby_channel)
        connection.join(self.game_channel)
        connection.mode(self.game_channel, "+i")
        self.debug_log("[HOST:{}] Joined {} and {}".format(self.owner_username, self.lobby_channel, self.game_channel))
        self.start_broadcast_thread()
        self.start_invite_monitor_thread()

    def on_pubmsg(self, connection, event):
        sender = NickMask(event.source).nick
        msg = event.arguments[0].strip()

        self.debug_log("[HOST:{}] Received message from {}: '{}' in channel {}".format(self.owner_username, sender, msg, event.target))
        
        if event.target == self.lobby_channel and msg == "!join {}".format(self.owner_username):
            self.debug_log("[HOST:{}] Processing join request from {}".format(self.owner_username, sender))
            self.send_invite(sender)
        elif event.target == self.game_channel:
            responses = self.game.handle_command(sender, msg)
            for resp in responses:
                if resp == "!game-start":
                    self.broadcast_running = False
                    self.debug_log("[HOST:{}] Broadcast stopped on !game-start".format(self.owner_username))
                self.connection.privmsg(self.game_channel, resp)

    def on_join(self, connection, event):
        nick = NickMask(event.source).nick
        channel = event.target
        if channel == self.game_channel and nick != self.connection.get_nickname():
            self.game.add_player(nick)

    def send_invite(self, nick):
        self.debug_log("[HOST:{}] Sending invite to {} for channel {}".format(self.owner_username, nick, self.game_channel))
        self.connection.invite(nick, self.game_channel)

    def start_broadcast_thread(self):
        def loop():
            while self.running and self.broadcast_running:
                visible_players = [p for p in self.game.players if p != self.connection.get_nickname()]
                players_str = ', '.join(visible_players) if visible_players else 'None'
                try:
                    self.connection.privmsg(self.lobby_channel, "HOST_AVAILABLE {} (Players: {})".format(self.owner_username, players_str))
                except:
                    break
                time.sleep(5)
        t = threading.Thread(target=loop)
        t.daemon = True
        t.start()

    def start_invite_monitor_thread(self):
        def loop():
            while self.running:
                self.present_nicks.clear()
                self.connection.names(self.game_channel)
                time.sleep(20)
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

    def on_disconnect(self, connection, event):
        event_type = getattr(event, 'type', None)
        event_args = getattr(event, 'arguments', None)
        self.debug_log("[HOST:{}] Disconnected from server. Event: {} | Type: {} | Args: {}".format(self.owner_username, repr(event), event_type, event_args))
        self.running = False
        sys.exit(0)

    def on_kick(self, connection, event):
        channel = event.target
        kicked_nick = NickMask(event.arguments[0]).nick
        self.debug_log("[HOST:{}] Kicked from {}: {}. Event: {}".format(self.owner_username, channel, kicked_nick, repr(event)))
        print("[HOST:{}] Kicked from {}: {}".format(self.owner_username, channel, kicked_nick))
        # If kicked from the lobby, try to rejoin
        if channel == self.lobby_channel:
            self.debug_log("[HOST:{}] Kicked from lobby, rejoining. Event: {}".format(self.owner_username, repr(event)))
            print("[HOST:{}] Kicked from lobby, rejoining.".format(self.owner_username))
            connection.join(self.lobby_channel)

    def on_part(self, connection, event):
        if event.target == self.lobby_channel:
            self.debug_log("[HOST:{}] Left lobby, rejoining. Event: {}".format(self.owner_username, repr(event)))
            print("[HOST:{}] Left lobby, rejoining.".format(self.owner_username))
            connection.join(self.lobby_channel)

    def on_ping(self, connection, event):
        self.debug_log("[HOST:{}] Received PING from server. Responding with PONG.".format(self.owner_username))
        connection.pong(event.target if hasattr(event, 'target') else None)

def main():
    print("[HOST] Starting host.py script...")
    if len(sys.argv) >= 2:
        owner_username = sys.argv[1]
        print("[HOST] Using command line username: {}".format(owner_username))
    else:
        try:
            owner_username = raw_input("Enter owner username for this host: ").strip()
        except NameError:
            # Python 3 compatibility
            owner_username = input("Enter owner username for this host: ").strip()
        print("[HOST] Using entered username: {}".format(owner_username))

    config = ConfigParser.ConfigParser()
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    config.read(config_path)
    server = config.get('irc', 'server')
    port = config.getint('irc', 'port')
    ssl_enabled = config.getboolean('irc', 'ssl')

    nick = "HostBot_{}".format(owner_username)
    print("[HOST:{}] Attempting to connect to {}:{} with nick '{}'".format(owner_username, server, port, nick))
    c = Host(config, owner_username)

    try:
        if ssl_enabled:
            factory = Factory(wrapper=ssl.wrap_socket)
        else:
            factory = None
        c.connect(server, port, nick, connect_factory=factory)
        print("[HOST:{}] Connection initiated successfully".format(owner_username))
    except ServerConnectionError as e:
        print("[HOST:{}] Connection failed: {}".format(owner_username, str(e)))
        sys.exit(1)

    c.start()

if __name__ == "__main__":
    main()
