import sys
import os

class Input(object):
    def __init__(self):
        self.platform = os.name
        self._old_term_settings = None
        
        # Import platform-specific modules
        if self.platform == 'nt':
            import msvcrt
            self.msvcrt = msvcrt
        else:
            import tty
            import termios
            import atexit
            import select
            self.tty = tty
            self.termios = termios
            self.select = select
            self.atexit = atexit
            
            # Set up terminal for Unix/Linux
            self.fd = sys.stdin.fileno()
            self._old_term_settings = self.termios.tcgetattr(self.fd)
            self.tty.setcbreak(self.fd)
            self.atexit.register(self._restore_terminal)

    def _restore_terminal(self):
        """Restore terminal to original settings"""
        if self.platform != 'nt' and self._old_term_settings is not None:
            self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self._old_term_settings)

    def kbhit(self):
        """Check if a key has been pressed (non-blocking)"""
        if self.platform == 'nt':
            return self.msvcrt.kbhit()
        else:
            dr, dw, de = self.select.select([sys.stdin], [], [], 0)
            return dr != []

    def getch(self):
        """Get a single character without pressing Enter"""
        if self.platform == 'nt':
            return self.msvcrt.getch()
        else:
            return sys.stdin.read(1)

    def keypressed(self):
        """Alias for kbhit for compatibility"""
        return self.kbhit()


# Example usage:
if __name__ == '__main__':
    input_handler = Input()
    
    print("Testing Input class...")
        
    # Test character input
    print("Press keys (Esc to exit):")
    while True:
        if input_handler.kbhit():
            ch = input_handler.getch()
            # Handle Windows bytes to string conversion for display
            if os.name == 'nt' and isinstance(ch, bytes):
                try:
                    ch = ch.decode('utf-8')
                except UnicodeDecodeError:
                    ch = '?'
            print("You pressed: {} (ASCII: {})".format(repr(ch), ord(ch)))
            if ord(ch) == 27:  # Escape key
                print("Exiting...")
                break
