import sys

class Display(object):
    def __init__(self):
        self.cursor_x = 0
        self.cursor_y = 0
        self.width = 80
        self.height = 25

    def gotoxy(self, x, y):
        self.cursor_x = x
        self.cursor_y = y
        sys.stdout.write("\033[{};{}H".format(y + 1, x + 1))
        sys.stdout.flush()

    def writexy(self, x, y, text):
        self.gotoxy(x, y)
        max_length = self.width - x
        if max_length > 0:
            truncated_text = text[:max_length]
            sys.stdout.write(truncated_text)
            sys.stdout.flush()

    def write(self, text):
        self.writexy(self.cursor_x, self.cursor_y, text)

    def clear(self):
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
        self.cursor_x = 0
        self.cursor_y = 0

    def refresh(self):
        sys.stdout.flush()

    def gettermsize(self):
        return (self.height, self.width)