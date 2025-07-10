# game.py - Minimal game state class for turn-based /pass game

class GameState(object):
    def __init__(self):
        self.players = set()
        self.ready_players = set()
        self.turn_order = []
        self.current_turn_index = 0
        self.game_active = False

    def add_player(self, nick):
        self.players.add(nick)

    def mark_ready(self, nick):
        self.ready_players.add(nick)
        return self.ready_players == self.players and len(self.players) > 0

    def start(self):
        self.turn_order = list(self.players)
        self.current_turn_index = 0
        self.game_active = True

    def current_player(self):
        if self.game_active and self.turn_order:
            return self.turn_order[self.current_turn_index]
        return None

    def next_turn(self):
        self.current_turn_index += 1
        if self.current_turn_index >= len(self.turn_order):
            return False  # End game
        return True

    def reset(self):
        self.ready_players.clear()
        self.turn_order = []
        self.current_turn_index = 0
        self.game_active = False
