import sys
from terminal import Terminal

# ui.py - version 0.4 with combined Terminal class

class UI(object):
    def __init__(self, client):
        self.client = client
        self.chat_history = []
        self.max_history = 100
        self.compact_mode = True  # False = full, True = compact
        self.terminal = Terminal()

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
        if hasattr(self, 'terminal'):
            self.draw_chat()  # Only redraw chat when new message arrives

    def run(self):
        # Terminal is already initialized in __init__
        
        input_buffer = ""
        self.draw_chat()  # Draw chat initially
        self.draw_prompt(input_buffer)  # Draw prompt initially
        
        try:
            while True:
                # Use curses getch() for proper key handling
                key = self.terminal.getch()
                
                if key is None or key == -1:
                    # No key pressed - add small delay to prevent high CPU usage
                    import time
                    time.sleep(0.01)  # 10ms delay
                    continue
                
                # Handle special curses keys
                if key == self.terminal.curses.KEY_ENTER or key == ord('\n') or key == ord('\r'):  # Enter
                    if input_buffer.strip():
                        # Check for quit commands first
                        if input_buffer.strip() in ("!quit", "!exit"):
                            self.client.send_user_input(input_buffer.strip())
                            #break
                        # Process normal input
                        responses = self.process_user_input(input_buffer.strip())
                        for resp in responses:
                            self.client.send_user_input(resp)
                    input_buffer = ""
                    self.draw_prompt(input_buffer)
                    
                elif key == self.terminal.curses.KEY_BACKSPACE or key == ord('\b') or key == 127:  # Backspace
                    if input_buffer:
                        input_buffer = input_buffer[:-1]
                        self.draw_prompt(input_buffer)
                        
                elif key == ord('\x1b'):  # Escape - quit
                    self.client.send_user_input("!quit")
                    #break
                    
                elif key == ord('\x03'):  # Ctrl+C - quit
                    self.client.send_user_input("!quit")
                    #break
                    
                elif key == ord('\t'):  # Tab - toggle compact mode
                    self.compact_mode = not self.compact_mode
                    self.terminal.clear()
                    self.draw_chat()  # Redraw chat when mode changes
                    self.draw_prompt(input_buffer)  # Redraw prompt after chat
                    
                elif key > 255:  # Other special curses keys (arrows, function keys, etc.)
                    # Ignore special keys for chat input
                    continue
                    
                elif 32 <= key <= 126:  # Printable ASCII characters
                    ch = chr(key)
                    input_buffer += ch
                    self.draw_prompt(input_buffer)
                        
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            self.client.send_user_input("!quit")
        except Exception as e:
            # Handle any unexpected errors gracefully
            pass
        finally:
            # Ensure terminal cleanup
            try:
                if hasattr(self, 'terminal') and hasattr(self.terminal, 'curses'):
                    self.terminal.curses.nocbreak()
                    self.terminal.curses.echo()
                    self.terminal.curses.endwin()
            except:
                pass
        
        self.client.shutdown()

    def draw_chat(self):
        """Draw only the chat area"""
        height, width = self.terminal.gettermsize()
        blank = " " * (width - 1)
        
        if self.compact_mode:
            chat_lines = 5
            start_row = height - 1 - chat_lines
            start = max(0, len(self.chat_history) - chat_lines)
            for idx in range(chat_lines):
                row = start_row + idx
                msg_idx = start + idx
                msg = self.chat_history[msg_idx] if msg_idx < len(self.chat_history) else ""
                self.terminal.writexy(0, row, (msg + blank)[:width - 1])
        else:
            chat_lines = height - 1
            start = max(0, len(self.chat_history) - chat_lines)
            for idx in range(chat_lines):
                msg_idx = start + idx
                msg = self.chat_history[msg_idx] if msg_idx < len(self.chat_history) else ""
                self.terminal.writexy(0, idx, (msg + blank)[:width - 1])
        
        self.terminal.refresh()

    def draw_prompt(self, input_buffer=""):
        """Draw only the input prompt line"""
        height, width = self.terminal.gettermsize()
        blank = " " * (width - 1)
        
        # Draw prompt
        prompt = "> " + input_buffer
        self.terminal.writexy(0, height - 1, (prompt + blank)[:width - 1])
        self.terminal.gotoxy(min(len(prompt), width - 1), height - 1)
        self.terminal.refresh()


