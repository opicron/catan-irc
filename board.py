# board.py - Game state and player logic for Catan-like hex map
# Uses the hex map structures from map.py but adds game logic
# No terminal/curses or UI code here

import networkx as nx
import random

class Player(object):
    def __init__(self, player_id, name=""):
        self.id = player_id
        self.name = name or "Player %d" % player_id
        self.roads = set()  # Set of edge IDs owned by this player
        self.settlements = set()  # Set of node IDs with settlements
        self.cities = set()  # Set of node IDs with cities
        self.longest_road_length = 0

class GameBoard(object):
    def __init__(self, hexmap):
        self.hexmap = hexmap
        self.players = {}  # player_id -> Player object
        
    def add_player(self, player_id, name=""):
        self.players[player_id] = Player(player_id, name)
        
    def build_road(self, player_id, edge_id):
        if player_id in self.players:
            self.players[player_id].roads.add(edge_id)
            self.hexmap.road_owners[edge_id] = player_id
            
    def build_settlement(self, player_id, node_id):
        if player_id in self.players:
            self.players[player_id].settlements.add(node_id)
            
    def build_city(self, player_id, node_id):
        if player_id in self.players:
            self.players[player_id].cities.add(node_id)
            # Remove settlement if upgrading
            self.players[player_id].settlements.discard(node_id)
            
    def compute_longest_road_for_player(self, player_id):
        if player_id not in self.players:
            return 0
            
        G = nx.Graph()
        for edge_id in self.players[player_id].roads:
            if edge_id not in self.hexmap.edge_to_tile:
                continue
            tile_coord, edge_idx = self.hexmap.edge_to_tile[edge_id]
            tile = self.hexmap.tiles[tile_coord]
            n1 = tile.nodes[edge_idx]
            n2 = tile.nodes[(edge_idx + 1) % 6]
            if n1 != n2:
                G.add_edge(n1, n2)
                
        if not G:
            return 0
            
        longest = 0
        for node in G.nodes():
            lengths = nx.single_source_dijkstra_path_length(G, node)
            max_len = max(lengths.values())
            if max_len > longest:
                longest = max_len
                
        self.players[player_id].longest_road_length = longest
        return longest
        
    def update_all_longest_roads(self):
        for player_id in self.players:
            self.compute_longest_road_for_player(player_id)
            
    def get_longest_road_winner(self):
        if not self.players:
            return None
        best_player = max(self.players.values(), key=lambda p: p.longest_road_length)
        if best_player.longest_road_length >= 5:  # Minimum length for longest road card
            return best_player
        return None

def random_branching_road_walk_for_player(board, player_id, steps=20, boundary_nodes=None, draw_func=None):
    """Build roads for a player using random walk algorithm"""
    if player_id not in board.players:
        board.add_player(player_id)
        
    hexmap = board.hexmap
    visited_edges = set(board.players[player_id].roads)  # Start with existing roads
    visited_nodes = set()
    
    all_nodes = list(hexmap.node_ids.values())
    if boundary_nodes is None:
        boundary_nodes = set()
        
    non_boundary_nodes = [n for n in all_nodes if n not in boundary_nodes]
    if not non_boundary_nodes:
        return
        
    # Find starting node from existing roads or pick random
    frontier = []
    if visited_edges:
        # Start from endpoints of existing roads
        for edge_id in visited_edges:
            if edge_id in hexmap.edge_to_tile:
                tile_coord, edge_idx = hexmap.edge_to_tile[edge_id]
                tile = hexmap.tiles[tile_coord]
                frontier.extend([tile.nodes[edge_idx], tile.nodes[(edge_idx + 1) % 6]])
        frontier = list(set(frontier))  # Remove duplicates
    else:
        # Start fresh
        start_node = random.choice(non_boundary_nodes)
        frontier = [start_node]
        
    visited_nodes.update(frontier)
    
    for _ in range(steps):
        if not frontier:
            break
            
        current_node = random.choice(frontier)
        neighbors = []
        
        # Find all unvisited edges incident to current_node
        for tile in hexmap.tiles.values():
            for i in range(6):
                e = tile.edges[i]
                n1 = tile.nodes[i]
                n2 = tile.nodes[(i + 1) % 6]
                
                if e in visited_edges:
                    continue
                    
                if current_node in (n1, n2):
                    other_node = n2 if current_node == n1 else n1
                    if other_node in visited_nodes or other_node in boundary_nodes:
                        continue
                    neighbors.append((tile, i, e, other_node))
                    
        if not neighbors:
            frontier.remove(current_node)
            continue
            
        # Pick one randomly and build road
        tile, edge_idx, edge_id, new_node = random.choice(neighbors)
        board.build_road(player_id, edge_id)
        
        # Draw the road if drawing function is provided
        if draw_func:
            draw_func(tile, edge_idx, player_id)
        
        visited_edges.add(edge_id)
        visited_nodes.add(new_node)
        frontier.append(new_node)

def get_boundary_nodes(hexmap):
    """Get all nodes on the boundary of the map"""
    boundary_nodes = set()
    for tile_coord, tile in hexmap.tiles.items():
        for dir_idx in range(6):
            dx, dy, dz = hexmap.directions[dir_idx]
            neighbor_coord = (tile.x + dx, tile.y + dy, tile.z + dz)
            if neighbor_coord not in hexmap.tiles:
                node_a = tile.nodes[dir_idx]
                node_b = tile.nodes[(dir_idx + 1) % 6]
                boundary_nodes.add(node_a)
                boundary_nodes.add(node_b)
    return boundary_nodes


if __name__ == "__main__":
    import time
    from map import HexMap, terminal, draw_map, get_map_screen_size
    
    terminal.clear()
    terminal.gotoxy(0, 0)

    # Create hex map and game board
    hexmap = HexMap()
    hexmap.generate_default_map(radius=3)
    hexmap.build_nodes_and_edges()

    # Create game board with players
    board = GameBoard(hexmap)
    board.add_player(1, "Player 1")
    board.add_player(2, "Player 2")

    boundary_nodes = get_boundary_nodes(hexmap)
    draw_map(hexmap, boundary_nodes)

    # Define drawing helper
    def draw_player_road(tile, edge_idx, player_id):
        from map import draw_road
        if player_id == 1:
            draw_road(tile, edge_idx, hexmap, color=terminal.COLOR_PAIR_RED)
        else:
            draw_road(tile, edge_idx, hexmap, color=terminal.COLOR_PAIR_BLUE)

    # Build roads for players using board system
    random_branching_road_walk_for_player(board, player_id=1, steps=4, boundary_nodes=boundary_nodes, draw_func=draw_player_road)
    random_branching_road_walk_for_player(board, player_id=2, steps=5, boundary_nodes=boundary_nodes, draw_func=draw_player_road)

    width, height = get_map_screen_size(hexmap)
    terminal.writexy(0, height, "")

    # Use board's longest road calculation
    board.update_all_longest_roads()
    for player_id, player in board.players.items():
        terminal.write("Longest road for %s: %d tiles\n" % (player.name, player.longest_road_length))
    
    # Capture screen buffer including the additional text lines
    height, width = terminal.gettermsize()
    char_buffer, color_buffer = terminal.dump_screen_to_buffer(terminal.stdscr, height, width)

    # Clean exit
    try:
        terminal.curses.nocbreak()
        terminal.curses.echo()
        terminal.curses.endwin()
    except:
        pass

    terminal.dump_buffer_to_console(char_buffer, color_buffer)
