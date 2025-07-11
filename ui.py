# ui.py - version 0.2 decoupled response-returning design

class UI(object):
    def __init__(self, client):
        self.client = client

    def handle_server_message(self, sender, msg):
        responses = []
        print("[{}] {}: {}".format(self.client.active_channel, sender, msg))
        if msg == "!game-start":
            print("[UI] Detected !game-start. Placeholder for UI initialization.")
            # self.show_ui()  # Future integration
        # If UI wants to automatically respond to server msg, add here:
        # Example: if msg == "!ping": responses.append("pong")
        return responses

    def process_user_input(self, user_input):
        responses = []
        if user_input:
            responses.append(user_input)
        return responses
