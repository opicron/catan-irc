# host.py - Host bot with game channel invite mechanism
import ConfigParser
import threading
import time
from irc.client import SimpleIRCClient, Reactor, NickMask

class HostBot(SimpleIRCClient):
    def __init__(self, config):
        SimpleIRCClient.__init__(self)
        self.config = config
        self.lobby_channel = config.get('irc', 'channel')
        self.game_channel = "#catan-game"  # Could add unique suffix or ID
        self.players = set()
        self.running = True

    def on_welcome(self, connection, event):
        connection.join(self.lobby_channel)
        print("[HOST] Joined lobby {}".format(self.lobby_channel))
        self.connection.join(self.game_channel)
        print("[HOST] Created game channel {}".format(self.game_channel))
        self.start_broadcast_thread()

    def on_pubmsg(self, connection, event):
        msg = event.arguments[0].strip()
        sender = NickMask(event.source).nick

        if event.target == self.lobby_channel:
            if msg.startswith("/join"):
                if sender not in self.players:
                    self.players.add(sender)
                    print("[HOST] {} joined the game.".format(sender))
                    self.connection.privmsg(self.lobby_channel, "[HOST] {} is joining the game.".format(sender))
                    self.connection.invite(sender, self.game_channel)  # IRC INVITE
                else:
                    print("[HOST] {} is already in the game.".format(sender))

    def start_broadcast_thread(self):
        def loop():
            while self.running:
                players = ', '.join(self.players) if self.players else 'None'
                self.connection.privmsg(self.lobby_channel, "HOST_AVAILABLE (Players: {})".format(players))
                time.sleep(5)
        t = threading.Thread(target=loop)
        t.daemon = True
        t.start()

def main():
    config = ConfigParser.ConfigParser()
    config.read('config.ini')
    server = config.get('irc', 'server')
    port = config.getint('irc', 'port')
    nick = "HostBot"

    reactor = Reactor()
    bot = HostBot(config)
    reactor.scheduler.execute_after(1, lambda: bot.connect(server, port, nick))
    reactor.process_forever()

if __name__ == "__main__":
    main()
