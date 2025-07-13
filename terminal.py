import sys
import atexit
import signal

class Terminal(object):
    _cleanup_registered = False
    _curses_module = None
    _instance = None
    
    @classmethod
    def _emergency_cleanup(cls):
        """Emergency cleanup function for atexit and signal handlers"""
        if cls._curses_module:
            try:
                cls._curses_module.nocbreak()
                cls._curses_module.echo()
                cls._curses_module.endwin()
            except:
                pass
    
    def __new__(cls):
        # Singleton pattern to ensure only one terminal instance
        if cls._instance is None:
            cls._instance = super(Terminal, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if hasattr(self, '_initialized'):
            return
        
        import curses
        self.curses = curses
        Terminal._curses_module = curses
        
        # Register cleanup handlers only once
        if not Terminal._cleanup_registered:
            atexit.register(Terminal._emergency_cleanup)
            signal.signal(signal.SIGINT, lambda s, f: (Terminal._emergency_cleanup(), sys.exit(0)))
            signal.signal(signal.SIGTERM, lambda s, f: (Terminal._emergency_cleanup(), sys.exit(0)))
            Terminal._cleanup_registered = True
        
        # Initialize curses
        self.stdscr = curses.initscr()
        curses.noecho()        # Don't echo keys to screen
        curses.cbreak()        # React to keys instantly
        curses.curs_set(1)     # Show cursor for input
        self.stdscr.nodelay(1) # Make getch() non-blocking
        self.stdscr.keypad(1)  # Enable special keys
        
        # Get terminal dimensions
        self.height, self.width = self.stdscr.getmaxyx()
        self.cursor_x = 0
        self.cursor_y = 0
        
        self._initialized = True

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.curses.nocbreak()
            self.curses.echo()
            self.curses.endwin()
        except:
            pass

    # Display methods
    def gotoxy(self, x, y):
        """Move cursor to specified position"""
        self.cursor_x = min(x, self.width - 1)
        self.cursor_y = min(y, self.height - 1)
        try:
            self.stdscr.move(self.cursor_y, self.cursor_x)
        except self.curses.error:
            # Handle case where cursor position is invalid
            pass

    def writexy(self, x, y, text):
        """Write text at specified position"""
        self.gotoxy(x, y)
        try:
            # Ensure text fits within screen bounds
            max_len = self.width - x
            if max_len > 0:
                display_text = text[:max_len]
                self.stdscr.addstr(self.cursor_y, self.cursor_x, display_text)
        except self.curses.error:
            # Handle case where text can't be displayed
            pass

    def clear(self):
        """Clear the entire screen"""
        try:
            self.stdscr.clear()
        except self.curses.error:
            pass

    def refresh(self):
        """Refresh the screen to show changes"""
        try:
            self.stdscr.refresh()
        except self.curses.error:
            pass

    def gettermsize(self):
        """Get terminal dimensions, with fallback"""
        try:
            self.height, self.width = self.stdscr.getmaxyx()
            return self.height, self.width
        except:
            return 25, 80  # Default fallback

    # Input methods
    def kbhit(self):
        """Check if a key has been pressed (non-blocking)"""
        try:
            key = self.stdscr.getch()
            if key != -1:  # -1 means no key available
                # Put the key back for getch() to retrieve
                self.curses.ungetch(key)
                return True
            return False
        except:
            return False

    def getch(self):
        """Get a single character without pressing Enter"""
        try:
            key = self.stdscr.getch()
            if key == -1:  # No key available
                return None
            
            # Just return the key value directly - curses handles everything
            return key
        except:
            return None

    def keypressed(self):
        """Alias for kbhit for compatibility"""
        return self.kbhit()

    def getstr(self, prompt=""):
        """Get a string input with optional prompt using ncurses"""
        # Save current cursor position
        start_y, start_x = self.stdscr.getyx()
        
        # Display the prompt using ncurses
        if prompt:
            self.stdscr.addstr(prompt)
            self.refresh()
            prompt_y, prompt_x = self.stdscr.getyx()
        else:
            prompt_y, prompt_x = start_y, start_x
        
        input_str = ""
        
        while True:
            if self.kbhit():
                key = self.getch()
                if key is None:
                    continue

                #self.stdscr.addstr(str(key))
                #self.refresh()

                # Handle special keys
                if key == self.curses.KEY_UP or key == self.curses.KEY_DOWN or key == self.curses.KEY_LEFT or key == self.curses.KEY_RIGHT:
                    continue  # Ignore arrow keys for string input
                elif key > 255:  # Other special curses keys
                    continue
                
                # Handle regular keys
                if key == self.curses.KEY_ENTER or key==10:  # Enter key
                    self.stdscr.move(prompt_y + 1, 0)
                    self.refresh()
                    return input_str
                    
                elif key == self.curses.KEY_BACKSPACE:  # Backspace
                    if input_str:
                        input_str = input_str[:-1]
                        # Clear the input area and redraw
                        self.stdscr.move(prompt_y, prompt_x)
                        self.stdscr.clrtoeol()
                        if input_str:
                            self.stdscr.addstr(input_str)
                        self.refresh()
                        
                elif key == ord('\x1b') or key == 27:  # Escape
                    self.stdscr.move(prompt_y + 1, 0)
                    self.refresh()
                    return ""
                    
                elif key == ord('\x03'):  # Ctrl+C
                    self.stdscr.move(prompt_y + 1, 0)
                    self.refresh()
                    raise KeyboardInterrupt()
                    
                elif 32 <= key <= 126:  # Printable characters
                    ch = chr(key)
                    input_str += ch
                    self.stdscr.addstr(ch)
                    self.refresh()

    def getstr_debug(self, prompt=""):
        """Debug version of getstr that shows key codes"""
        # Save current cursor position
        start_y, start_x = self.stdscr.getyx()
        
        # Display the prompt using ncurses
        if prompt:
            self.stdscr.addstr(prompt)
            self.refresh()
            prompt_y, prompt_x = self.stdscr.getyx()
        else:
            prompt_y, prompt_x = start_y, start_x
        
        input_str = ""
        
        while True:
            if self.kbhit():
                key = self.getch()
                if key is None:
                    continue
                
                # Debug: show key code
                debug_msg = " [DEBUG: key={}] ".format(key)
                try:
                    height, width = self.gettermsize()
                    self.stdscr.move(0, 0)
                    self.stdscr.addstr(debug_msg[:width-1])
                    self.stdscr.move(prompt_y, prompt_x + len(input_str))
                    self.refresh()
                except:
                    pass
                
                # Handle special keys
                if key == self.curses.KEY_UP or key == self.curses.KEY_DOWN or key == self.curses.KEY_LEFT or key == self.curses.KEY_RIGHT:
                    continue  # Ignore arrow keys for string input
                elif key > 255:  # Other special curses keys
                    continue
                
                # Handle regular keys
                if key == self.curses.KEY_ENTER:  # Enter key
                    self.stdscr.move(prompt_y + 1, 0)
                    self.refresh()
                    return input_str
                    
                elif key == self.curses.KEY_BACKSPACE:  # Backspace
                    if input_str:
                        input_str = input_str[:-1]
                        # Clear the input area and redraw
                        self.stdscr.move(prompt_y, prompt_x)
                        self.stdscr.clrtoeol()
                        if input_str:
                            self.stdscr.addstr(input_str)
                        self.refresh()
                        
                elif key == ord('\x1b'):  # Escape
                    self.stdscr.move(prompt_y + 1, 0)
                    self.refresh()
                    return ""
                    
                elif key == ord('\x03'):  # Ctrl+C
                    self.stdscr.move(prompt_y + 1, 0)
                    self.refresh()
                    raise KeyboardInterrupt()
                    
                elif 32 <= key <= 126:  # Printable characters
                    ch = chr(key)
                    input_str += ch
                    self.stdscr.addstr(ch)
                    self.refresh()

# Example usage:
if __name__ == '__main__':
    terminal = Terminal()
    
    # Use ncurses for output instead of print
    terminal.clear()
    terminal.writexy(0, 0, "Testing Terminal class with ncurses...")
    terminal.writexy(0, 1, "Press keys (Esc to exit):")
    terminal.writexy(0, 2, "Try arrow keys, they should be detected as curses constants.")
    terminal.refresh()
    
    current_line = 4  # Start output below instructions
    
    # Test character input
    while True:
        if terminal.kbhit():
            key = terminal.getch()
            if key is None:
                continue
            
            output_msg = ""
            
            # Check for special keys using curses constants
            if key == terminal.curses.KEY_UP:
                output_msg = "KEY_UP ({})".format(key)
            elif key == terminal.curses.KEY_DOWN:
                output_msg = "KEY_DOWN ({})".format(key)
            elif key == terminal.curses.KEY_LEFT:
                output_msg = "KEY_LEFT ({})".format(key)
            elif key == terminal.curses.KEY_RIGHT:
                output_msg = "KEY_RIGHT ({})".format(key)
            elif key == ord('\x1b'):
                output_msg = "ESC ({})".format(key)
            elif key == terminal.curses.KEY_ENTER or key == ord('\n') or key == ord('\r'):
                output_msg = "ENTER ({})".format(key)
            elif key == ord('\t'):
                output_msg = "TAB ({})".format(key)
            elif key == terminal.curses.KEY_BACKSPACE or key == ord('\b') or key == ord('\x7f'):
                output_msg = "BACKSPACE ({})".format(key)
            elif 32 <= key <= 126:  # Printable characters
                output_msg = "'{}' ({})".format(chr(key), key)
            else:
                output_msg = "KEY_{}".format(key)
            
            # Display the message using ncurses
            height, width = terminal.gettermsize()
            if current_line < height - 1:
                terminal.writexy(0, current_line, output_msg)
                current_line += 1
            else:
                # Scroll up when we reach the bottom
                terminal.clear()
                terminal.writexy(0, 0, "Testing Terminal class with ncurses...")
                terminal.writexy(0, 1, "Press keys (Esc to exit):")
                terminal.writexy(0, 2, "Try arrow keys, they should be detected as curses constants.")
                current_line = 4
                terminal.writexy(0, current_line, output_msg)
                current_line += 1
            
            terminal.refresh()
            
            if key == ord('\x1b'):  # Escape key
                terminal.writexy(0, current_line, "Exiting...")
                terminal.refresh()
                import time
                time.sleep(1)  # Show exit message briefly
                break
