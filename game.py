# game.py

class GameState(object):
    def __init__(self):
        self.players = set()
        self.ready_players = set()
        self.turn_order = []
        self.current_turn_index = 0
        self.game_active = False

    def add_player(self, nick):
        self.players.add(nick)

    def handle_command(self, sender, msg):
        responses = []

        if not self.game_active:
            if msg == "/game":
                if sender in self.players:
                    self.ready_players.add(sender)
                    responses.append("{} is ready.".format(sender))
                    if self.ready_players == self.players and len(self.players) > 0:
                        self.start_game()
                        responses.append("!game-start")
                        responses.append("Game started! Turn order: {}".format(", ".join(self.turn_order)))
                        responses.append("It's {}'s turn. Type /pass.".format(self.current_player()))
                else:
                    responses.append("You must join first.")
            else:
                responses.append("{} says: {}".format(sender, msg))
        else:
            if msg == "/pass":
                if sender == self.current_player():
                    if not self.next_turn():
                        responses.append("Game over! Thanks for playing.")
                        self.reset()
                    else:
                        responses.append("It's {}'s turn. Type /pass.".format(self.current_player()))
                else:
                    responses.append("It's not your turn, {}".format(sender))
            else:
                responses.append("{} says: {}".format(sender, msg))

        return responses

    def start_game(self):
        self.turn_order = list(self.players)
        self.current_turn_index = 0
        self.game_active = True

    def current_player(self):
        if self.turn_order:
            return self.turn_order[self.current_turn_index]
        return None

    def next_turn(self):
        self.current_turn_index += 1
        if self.current_turn_index >= len(self.turn_order):
            return False
        return True

    def reset(self):
        self.ready_players.clear()
        self.turn_order = []
        self.current_turn_index = 0
        self.game_active = False
