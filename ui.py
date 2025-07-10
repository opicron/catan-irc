# ui.py - Decoupled UI layer for IRC-based client

class UI(object):
    def __init__(self, client):
        self.client = client

    def handle_server_message(self, sender, msg):
        print("[{}] {}: {}".format(self.client.active_channel, sender, msg))
        if msg == "!game-start":
            print("[UI] Detected !game-start. Placeholder for UI launch.")
            # self.show_ui()  # Future UI integration

    def user_input_loop(self):
        try:
            while True:
                user_input = raw_input("> ").strip()
                self.client.send_user_input(user_input)
        except KeyboardInterrupt:
            print("[UI] Interrupted by user.")
            self.client.shutdown()
