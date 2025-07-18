import sys
import atexit
import signal

class Terminal(object):
    # ncurses color pair numbers for use by UI and map drawing
    COLOR_PAIR_WHITE = 1
    COLOR_PAIR_YELLOW = 2
    COLOR_PAIR_RED = 3
    COLOR_PAIR_GREEN = 4
    COLOR_PAIR_GREY = 5
    COLOR_PAIR_BLUE = 6
    COLOR_PAIR_BRIGHT_RED = 7

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
        curses.start_color()
        if not curses.has_colors():
            raise Exception("Your terminal does not support color")
        curses.use_default_colors()
        # Define color pairs (foreground, background)
        curses.init_pair(self.COLOR_PAIR_WHITE, curses.COLOR_WHITE, -1)
        curses.init_pair(self.COLOR_PAIR_YELLOW, curses.COLOR_YELLOW, -1)
        curses.init_pair(self.COLOR_PAIR_RED, curses.COLOR_RED, -1)
        curses.init_pair(self.COLOR_PAIR_GREEN, curses.COLOR_GREEN, -1)
        # Use 8 for grey if available, else fallback to white
        curses.init_pair(self.COLOR_PAIR_GREY, 8 if hasattr(curses, 'COLOR_BLACK') else curses.COLOR_WHITE, -1)
        curses.init_pair(self.COLOR_PAIR_BLUE, curses.COLOR_BLUE, -1)
        curses.init_pair(self.COLOR_PAIR_BRIGHT_RED, curses.COLOR_RED, curses.COLOR_WHITE)
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

    def addch(self, x, y, ch):
        """Add a single character at specified position, handling special characters"""
        self.gotoxy(x, y)
        try:
            # Get actual cursor position from ncurses
            current_y, current_x = self.stdscr.getyx()
            # Handle box drawing characters
            if isinstance(ch, int):
                # If it's an integer, treat it as a character code
                if ch == 186:  # chr(186) is vertical line in CP437
                    self.stdscr.addch(self.curses.ACS_VLINE)
                elif ch == 205:  # chr(205) is horizontal line in CP437
                    self.stdscr.addch(self.curses.ACS_HLINE)
                else:
                    self.stdscr.addch(ch)
            elif isinstance(ch, str) and len(ch) == 1:
                # Handle string characters
                char_code = ord(ch)
                if char_code == 186:  # chr(186)
                    self.stdscr.addch(self.curses.ACS_VLINE)
                elif char_code == 205:  # chr(205)
                    self.stdscr.addch(self.curses.ACS_HLINE)
                else:
                    self.stdscr.addch(ch)
            else:
                # For multi-character strings, fall back to addstr
                self.stdscr.addstr(str(ch))
        except self.curses.error:
            # Handle case where character can't be displayed
            pass

    def writexy(self, x, y, text):
        """Write text at specified position"""
        self.gotoxy(x, y)
        try:
            # Get actual cursor position from ncurses
            current_y, current_x = self.stdscr.getyx()
            # Ensure text fits within screen bounds
            max_len = self.width - current_x
            if max_len > 0:
                display_text = text[:max_len]
                self.stdscr.addstr(display_text)
        except self.curses.error:
            # Handle case where text can't be displayed
            pass

    def write(self, text):
        """Write text at current cursor position"""
        try:
            # Get actual cursor position from ncurses
            current_y, current_x = self.stdscr.getyx()
            # Ensure text fits within screen bounds
            max_len = self.width - current_x
            if max_len > 0:
                display_text = text[:max_len]
                self.stdscr.addstr(display_text)
        except self.curses.error:
            # Handle case where text can't be displayed
            pass

    def setcolor(self, color_pair):
        """Set the color for subsequent text output"""
        try:
            self.stdscr.attron(self.curses.color_pair(color_pair))
        except self.curses.error:
            pass

    def resetcolor(self):
        """Reset color to default"""
        try:
            self.stdscr.attrset(0)
        except self.curses.error:
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
                    #height, width = self.gettermsize()
                    #if prompt_y + 1 < height:
                    #    self.stdscr.move(prompt_y + 1, 0)
                    #self.refresh()
                    return input_str
                    
                elif key == self.curses.KEY_BACKSPACE or key == ord('\b') or key == 127:  # Backspace
                    if input_str:
                        input_str = input_str[:-1]
                        # Clear the input area and redraw
                        self.stdscr.move(prompt_y, prompt_x)
                        self.stdscr.clrtoeol()
                        if input_str:
                            self.stdscr.addstr(input_str)
                        self.refresh()
                        
                elif key == ord('\x1b') or key == 27:  # Escape
                    height, width = self.gettermsize()
                    if prompt_y + 1 < height:
                        self.stdscr.move(prompt_y + 1, 0)
                    self.refresh()
                    return ""
                    
                elif key == ord('\x03'):  # Ctrl+C
                    height, width = self.gettermsize()
                    if prompt_y + 1 < height:
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

    def get_char_only(self, ch):
        """Extract printable character from result of inch() call"""
        c = ch & 0xff
        if c == 0:
            return ' '  # Treat null as space
        return chr(c)

    def dump_screen_to_buffer(self, stdscr, height, width):
        # Save current cursor position
        #orig_y, orig_x = stdscr.getyx()
        
        char_buffer = []
        color_buffer = []
        for y in range(height):
            char_row = []
            color_row = []
            for x in range(width):
                ch = stdscr.inch(y, x)
                c = self.get_char_only(ch)
                
                # Extract color pair from ncurses attributes
                color_pair = 0  # default
                
                # Extract from the raw character value
                # The color pair is encoded in the upper 8 bits
                color_pair = (ch >> 24) & 0xFF
                if color_pair == 0:
                    # Try alternative extraction - upper 16 bits divided by 65536
                    color_attr = ch & self.curses.A_COLOR if hasattr(self.curses, 'A_COLOR') else 0
                    if color_attr:
                        color_pair = color_attr // 65536
                    
                # Clamp to valid range (0-7 for our color pairs)
                color_pair = max(0, min(color_pair, 7))
                    
                char_row.append(c)
                color_row.append(color_pair)
                
            char_buffer.append(char_row)
            color_buffer.append(color_row)
        
        # Restore original cursor position
        #try:
        #    stdscr.move(orig_y, orig_x)
        #except:
        #    pass
            
        return char_buffer, color_buffer
    
    def color_pair_to_ansi(self, color_pair):
        # Map ncurses color pairs to ANSI color codes (foreground only)
        # You may need to adjust these mappings to match your color scheme
        ansi_map = {
            self.COLOR_PAIR_WHITE: '\033[37m',   # White
            self.COLOR_PAIR_YELLOW: '\033[33m',  # Yellow
            self.COLOR_PAIR_RED: '\033[31m',     # Red
            self.COLOR_PAIR_GREEN: '\033[32m',   # Green
            self.COLOR_PAIR_GREY: '\033[90m',    # Bright Black (Grey)
            self.COLOR_PAIR_BLUE: '\033[34m',    # Blue
            self.COLOR_PAIR_BRIGHT_RED: '\033[91m', # Bright Red
        }
        return ansi_map.get(color_pair, '\033[39m')  # Default to reset/normal

    def dump_buffer_to_console(self, char_buffer, color_buffer):
        """Print the char/color buffers to the console using ANSI color codes."""
        reset = '\033[0m'
        
        # Find the last non-empty line to avoid printing trailing blank lines
        last_content_line = len(char_buffer) - 1
        while last_content_line >= 0:
            line_content = ''.join(char_buffer[last_content_line]).strip()
            if line_content:  # Found a line with actual content
                break
            last_content_line -= 1
        
        # Print only up to the last line with content
        for row_idx in range(last_content_line + 1):
            char_row, color_row = char_buffer[row_idx], color_buffer[row_idx]
            line = ''
            last_color = None
            for c, color_pair in zip(char_row, color_row):
                ansi = self.color_pair_to_ansi(color_pair)
                if ansi != last_color:
                    line += ansi
                    last_color = ansi
                line += c
            line += reset
            print(line.rstrip())

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


