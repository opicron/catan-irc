# client.py - IRC client that auto-joins invited game channels
import ConfigParser
import threading
import time
from irc.client import SimpleIRCClient, Reactor, NickMask
import subprocess
import sys

class Client(SimpleIRCClient):
    def __init__(self, config, nickname):
        SimpleIRCClient.__init__(self)
        self.config = config
        self.nick = nickname
        self.lobby_channel = config.get('irc', 'channel')
        self.running = True
        self.host_process = None

    def on_welcome(self, connection, event):
        connection.join(self.lobby_channel)
        print("[CLIENT:{}] Joined lobby {}".format(self.nick, self.lobby_channel))

    def on_pubmsg(self, connection, event):
        msg = event.arguments[0].strip()
        sender = NickMask(event.source).nick

        if msg.startswith("HOST_AVAILABLE"):
            print("[CLIENT:{}] Host available from {}".format(self.nick, sender))
        else:
            print("[CLIENT:{}] {} says: {}".format(self.nick, sender, msg))

    def on_invite(self, connection, event):
        inviter = NickMask(event.source).nick
        channel = event.arguments[0]
        print("[CLIENT:{}] Invited by {} to join {}".format(self.nick, inviter, channel))
        self.connection.join(channel)
        print("[CLIENT:{}] Auto-joined game channel {}".format(self.nick, channel))

    def run_main_loop(self):
        try:
            while True:
                user_input = raw_input("> ").strip()
                if user_input == "/start":
                    self.start_host_process()
                elif user_input == "/join":
                    self.connection.privmsg(self.lobby_channel, "/join")
                elif user_input == "/quit":
                    print("[CLIENT:{}] Exiting.".format(self.nick))
                    self.stop_host_process()
                    self.running = False
                    self.connection.quit("Client exiting.")
                    break
                else:
                    self.connection.privmsg(self.lobby_channel, "{} says: {}".format(self.nick, user_input))
        except KeyboardInterrupt:
            print("[CLIENT:{}] Interrupted.".format(self.nick))
            self.stop_host_process()
            self.running = False
            self.connection.quit("Client interrupted.")

    def start_host_process(self):
        if not self.host_process:
            print("[CLIENT:{}] Spawning host.py as external host.".format(self.nick))
            self.host_process = subprocess.Popen([sys.executable, "host.py"])
            time.sleep(1)
            self.connection.privmsg(self.lobby_channel, "/join")
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

    nickname = raw_input("Enter your nickname: ").strip()

    reactor = Reactor()
    client = Client(config, nickname)
    reactor.scheduler.execute_after(1, lambda: client.connect(server, port, nickname))

    reactor_thread = threading.Thread(target=reactor.process_forever)
    reactor_thread.daemon = True
    reactor_thread.start()

    client.run_main_loop()

if __name__ == "__main__":
    main()
