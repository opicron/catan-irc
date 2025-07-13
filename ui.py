import sys
from display import Display
from input import Input

# ui.py - version 0.3 ANSI-based design

class UI(object):
    def __init__(self, client):
        self.client = client
        self.chat_history = []
        self.max_history = 100
        self.compact_mode = True  # False = full, True = compact
        self.input_handler = Input()

    def handle_server_message(self, channel, sender, msg):
        responses = []
        formatted = "[{}] {}: {}".format(channel, sender, msg)
        self.add_message(formatted)
        if msg == "!game-start":
            self.add_message("[UI] Detected !game-start. Placeholder for UI initialization.")
            # self.show_ui()  # Future integration
        # If UI wants to automatically respond to server msg, add here:
        # Example: if msg == "!ping": responses.append("pong")
        return responses

    def process_user_input(self, user_input):
        responses = []
        if user_input:
            responses.append(user_input)
            self.add_message("[You]: {}".format(user_input))
        return responses

    def add_message(self, msg):
        self.chat_history.append(msg)
        if len(self.chat_history) > self.max_history:
            self.chat_history.pop(0)
        if hasattr(self, 'display'):
            self.draw()

    def run(self):
        self.display = Display()
        input_buffer = ""
        self.draw(input_buffer)  # Draw once initially
        
        try:
            while True:
                # Use the improved input handler methods
                if self.input_handler.keypressed():
                    ch = self.input_handler.getch()
                    
                    # Handle different key codes
                    if ord(ch) == 13 or ord(ch) == 10:  # Enter
                        if input_buffer.strip():
                            responses = self.process_user_input(input_buffer.strip())
                            for resp in responses:
                                self.client.send_user_input(resp)
                            if input_buffer.strip() in ("!quit", "!exit"):
                                break
                        input_buffer = ""
                        self.draw(input_buffer)  # Redraw only when needed
                    elif ord(ch) == 8 or ord(ch) == 127:  # Backspace
                        if input_buffer:
                            input_buffer = input_buffer[:-1]
                            self.draw(input_buffer)  # Redraw when input changes
                    elif ord(ch) == 27:  # Escape - quit
                        self.client.send_user_input("!quit")
                        break
                    elif ord(ch) == 3:  # Ctrl+C - quit
                        self.client.send_user_input("!quit")
                        break
                    elif ord(ch) == 9:  # Tab - toggle compact mode
                        self.compact_mode = not self.compact_mode
                        self.display.clear()
                        self.draw(input_buffer)  # Redraw when display mode changes
                    elif ord(ch) >= 32 and ord(ch) <= 126:  # Printable characters
                        input_buffer += ch
                        self.draw(input_buffer)  # Redraw when input changes
                else:
                    # No key pressed - add small delay to prevent high CPU usage
                    import time
                    time.sleep(0.01)  # 10ms delay
                        
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            self.client.send_user_input("!quit")
        except Exception as e:
            # Handle any unexpected errors gracefully
            pass
        
        self.client.shutdown()

    def draw(self, input_buffer=""):
        height, width = self.display.gettermsize()
        blank = " " * (width - 1)
        if self.compact_mode:
            chat_lines = 5
            start_row = height - 1 - chat_lines
            start = max(0, len(self.chat_history) - chat_lines)
            for idx in range(chat_lines):
                row = start_row + idx
                msg_idx = start + idx
                msg = self.chat_history[msg_idx] if msg_idx < len(self.chat_history) else ""
                self.display.writexy(0, row, (msg + blank)[:width - 1])
        else:
            chat_lines = height - 1
            start = max(0, len(self.chat_history) - chat_lines)
            for idx in range(chat_lines):
                msg_idx = start + idx
                msg = self.chat_history[msg_idx] if msg_idx < len(self.chat_history) else ""
                self.display.writexy(0, idx, (msg + blank)[:width - 1])
        # Draw prompt
        prompt = "> " + input_buffer
        self.display.writexy(0, height - 1, (prompt + blank)[:width - 1])
        self.display.gotoxy(min(len(prompt), width - 1), height - 1)
        self.display.refresh()
