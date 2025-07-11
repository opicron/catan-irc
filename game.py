# ====================== game.py ======================

import random

RESOURCE_TYPES = ['brick', 'lumber', 'wool', 'grain', 'ore']

class Player(object):
    def __init__(self, nick):
        self.nick = nick
        self.resources = dict((r, 0) for r in RESOURCE_TYPES)
        self.roads = set()
        self.settlements = set()
        self.cities = set()

    def total_victory_points(self):
        return len(self.settlements) + 2 * len(self.cities)

class GameState(object):
    def __init__(self):
        self.players = {}
        self.ready_players = set()
        self.turn_order = []
        self.current_turn_index = 0
        self.game_active = False
        self.state = 'awaiting_ready'  # State-driven model
        self.robber_tile = None

    def add_player(self, nick):
        if nick not in self.players:
            self.players[nick] = Player(nick)

    def handle_command(self, sender, msg):
        responses = []

        if msg == "/ready":
            return self.handle_ready(sender)

        if self.state == 'awaiting_ready':
            return ["Game not started yet."]

        if sender != self.current_player():
            return ["It's not your turn, {}.".format(sender)]

        if self.state == 'awaiting_roll':
            if msg == "/roll":
                return self.handle_roll(sender)
            return ["You must /roll first."]

        if self.state == 'awaiting_robber_move':
            if msg.startswith("/robber"):
                return self.handle_robber(sender, msg)
            return ["You must move the robber now."]

        if self.state == 'awaiting_actions':
            if msg == "/pass":
                return self.handle_pass(sender)
            if msg.startswith("/build") or msg.startswith("/trade"):
                return ["Action processed (abstract, validation omitted)."]
            return ["Unknown action during your turn."]

        return ["Invalid state."]

    def handle_ready(self, sender):
        responses = []
        if sender in self.players:
            self.ready_players.add(sender)
            responses.append("{} is ready.".format(sender))
            if len(self.ready_players) >= 2 and self.ready_players == set(self.players.keys()):
                responses += self.start_game()
        else:
            responses.append("You must join first.")
        return responses

    def start_game(self):
        self.turn_order = list(self.players.keys())
        self.current_turn_index = 0
        self.game_active = True
        self.state = 'awaiting_roll'
        return ["!game-start", "Game started.", "It's {}'s turn. Type /roll.".format(self.current_player())]

    def handle_roll(self, sender):
        dice = self.roll_dice()
        responses = ["{} rolled {}.".format(sender, dice)]
        if dice == 7:
            self.state = 'awaiting_robber_move'
            responses.append("Robber activated.")
            responses.append("!robber-expected {}".format(sender))
        else:
            responses.append("Resources distributed for roll {} (abstracted).".format(dice))
            self.state = 'awaiting_actions'
        return responses

    def handle_robber(self, sender, msg):
        parts = msg.split()
        if len(parts) != 2:
            return ["Usage: /robber <tile>."]
        tile = parts[1]
        self.robber_tile = tile  # Abstract position
        self.state = 'awaiting_actions'
        return ["Robber moved to tile {} (abstracted).".format(tile)]

    def handle_pass(self, sender):
        winner = self.check_winner()
        if winner:
            self.state = 'awaiting_ready'
            self.game_active = False
            return ["{} wins with 10 VP!".format(winner)]
        self.next_turn()
        self.state = 'awaiting_roll'
        return ["Turn passed. {}'s turn. Type /roll.".format(self.current_player())]

    def roll_dice(self):
        return random.randint(1, 6) + random.randint(1, 6)

    def current_player(self):
        return self.turn_order[self.current_turn_index]

    def next_turn(self):
        self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)

    def check_winner(self):
        for p in self.players.values():
            if p.total_victory_points() >= 10:
                return p.nick
        return None
