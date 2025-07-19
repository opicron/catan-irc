# -*- coding: cp437 -*-
# python 2.7 only

# client.py

import sys
import random
import networkx as nx


TILE_WIDTH = 11
TILE_HEIGHT = 3

class HexTile(object):
    def __init__(self, tile_id, x, y, z, tile_type="blank"):
        assert x + y + z == 0
        self.id = tile_id
        self.x = x
        self.y = y
        self.z = z
        self.tile_type = tile_type
        self.nodes = []
        self.edges = []

class HexMap(object):

    # Node indices (clockwise starting at top)
    NODE_N  = 0  # Node 0 (Top / North)
    NODE_NE = 1  # Node 1
    NODE_SE = 2  # Node 2
    NODE_S  = 3  # Node 3
    NODE_SW = 4  # Node 4
    NODE_NW = 5  # Node 5

    # Edge indices (clockwise, start at top between NODE_0 and NODE_1)
    EDGE_NE = 0  # Edge 0
    EDGE_E  = 1  # Edge 1
    EDGE_SE = 2  # Edge 2
    EDGE_SW = 3  # Edge 3
    EDGE_W  = 4  # Edge 4
    EDGE_NW = 5  # Edge 5

    def __init__(self, orientation="pointy"):
        self.tiles = {}
        self.tile_autoinc = 0
        self.node_ids = {}
        self.edge_ids = {}
        self.road_owners = {}  # Maps edge ID to player ID who owns the road
        self.edge_to_tile = {} 
        self.node_autoinc = 0
        self.edge_autoinc = 0
        self.orientation = orientation

        if orientation == "pointy":
            self.directions = [
                (1, 0, -1),   # EDGE_NE = 0
                (1, -1, 0),   # EDGE_E  = 1
                (0, -1, 1),   # EDGE_SE = 2
                (-1, 0, 1),   # EDGE_SW = 3
                (-1, 1, 0),   # EDGE_W  = 4
                (0, 1, -1)    # EDGE_NW = 5
            ]
        #elif orientation == "flat":
        #    self.directions = [
        #        (0, -1, 1),   # EDGE_E  (0)
        #        (1, -1, 0),   # EDGE_SE (1)
        #        (1, 0, -1),   # EDGE_S  (2)
        #        (0, 1, -1),   # EDGE_W  (3)
        #        (-1, 1, 0),   # EDGE_NW (4)
        #        (-1, 0, 1)    # EDGE_NE (5)
        #    ]
        else:
            raise ValueError("orientation must be 'pointy' or 'flat'")
        
    def add_tile(self, x, y, z, tile_type="blank"):
        tile = HexTile(self.tile_autoinc, x, y, z, tile_type)
        self.tiles[(x, y, z)] = tile
        self.tile_autoinc += 1

    def generate_default_map(self, radius=3):
        for x in range(-radius, radius + 1):
            for y in range(-radius, radius + 1):
                z = -x - y
                if -radius <= z <= radius:
                    distance = max(abs(x), abs(y), abs(z))
                    tile_type = "sea" if distance == radius else "land"
                    self.add_tile(x, y, z, tile_type)


    def build_nodes_and_edges(self):
        def neighbor(tile, dir_idx):
            dx, dy, dz = self.directions[dir_idx]
            return (tile[0] + dx, tile[1] + dy, tile[2] + dz)

        edge_id_map = {}
        next_edge_id = 0

        # --- Pass 1: assign unique edge IDs
        for tile_coord in sorted(self.tiles.keys()):
            for dir_idx in range(6):
                neighbor_tile = neighbor(tile_coord, dir_idx)
                if neighbor_tile in self.tiles:
                    key = tuple(sorted([tile_coord, neighbor_tile]))
                else:
                    key = (tile_coord, dir_idx)

                if key not in edge_id_map:
                    edge_id_map[key] = next_edge_id
                    self.edge_to_tile[next_edge_id] = (tile_coord, dir_idx)
                    next_edge_id += 1

        self.edge_ids = edge_id_map
        self.edge_autoinc = next_edge_id

        node_id_map = {}
        next_node_id = 0

        for tile_coord, tile in self.tiles.items():
            tile_edges = []
            corner_node_ids = []

            for i in range(6):
                neighbor_tile = neighbor(tile_coord, i)
                if neighbor_tile in self.tiles:
                    key = tuple(sorted([tile_coord, neighbor_tile]))
                else:
                    key = (tile_coord, i)
                eid = edge_id_map[key]
                tile_edges.append(eid)

            # --- Robust hybrid key for nodes
            for i in range(6):
                neighbor1 = neighbor(tile_coord, (i - 1) % 6)
                neighbor2 = neighbor(tile_coord, i)

                tile_set = [tile_coord]
                if neighbor1 in self.tiles:
                    tile_set.append(neighbor1)
                if neighbor2 in self.tiles:
                    tile_set.append(neighbor2)

                if len(tile_set) == 1:
                    # Map edge: ensure unique key for single tile node
                    key = (tile_coord, i)
                else:
                    key = frozenset(tile_set)

                if key not in node_id_map:
                    node_id_map[key] = next_node_id
                    next_node_id += 1

                corner_node_ids.append(node_id_map[key])

            tile.edges = tile_edges
            tile.nodes = corner_node_ids

        self.node_ids = node_id_map
        self.node_autoinc = next_node_id


def gotoxy(x, y):
    sys.stdout.write("\033[%d;%dH" % (y + 1, x + 1))
    sys.stdout.flush()

def draw_tile(tile, col, row, color=None):
    border = "+----+----+"
    coord_str = "(%d,%d,%d)" % (tile.x, tile.y, tile.z)
    coord_str = coord_str.center(TILE_WIDTH - 2)
    coord_line = "|" + coord_str + "|"

    if color:
        sys.stdout.write(color)  # Accept any valid ANSI color sequence

    gotoxy(col, row)
    sys.stdout.write(border)
    gotoxy(col, row + 1)
    sys.stdout.write(coord_line)
    gotoxy(col, row + 2)
    sys.stdout.write(border)

    if color:
        sys.stdout.write("\033[0m")  # Reset

    sys.stdout.flush()

def draw_road(tile, edge_idx, col, row, color=None):
    
    if color is None:
        sys.stdout.write("\033[34m")
    else: 
        sys.stdout.write(color)

    road_width = (TILE_WIDTH - 3) // 2

    dir_labels = {
        HexMap.EDGE_E: chr(186)+"E",
        HexMap.EDGE_NE: "=NE=",
        HexMap.EDGE_NW: "=NW=",
        HexMap.EDGE_W: chr(186)+"W",
        HexMap.EDGE_SW: "=SW=",
        HexMap.EDGE_SE: "=SE="
        #HexMap.EDGE_E: "|",
        #HexMap.EDGE_NE: "====",
        #HexMap.EDGE_NW: "====",
        #HexMap.EDGE_W: "|",
        #HexMap.EDGE_SW: "====",
        #HexMap.EDGE_SE: "===="
    }

    label = dir_labels.get(edge_idx, "====")[:road_width]
    if edge_idx == HexMap.EDGE_E:
        gotoxy(col + TILE_WIDTH - 1, row + 1)
        sys.stdout.write(label)
    elif edge_idx == HexMap.EDGE_W:
        gotoxy(col, row + 1)
        sys.stdout.write(label)
    elif edge_idx == HexMap.EDGE_NE:
        gotoxy(col + 1 + (TILE_WIDTH // 2), row)
        sys.stdout.write(label)
    elif edge_idx == HexMap.EDGE_NW:
        gotoxy(col + 1, row)
        sys.stdout.write(label)
    elif edge_idx == HexMap.EDGE_SW:
        gotoxy(col + 1, row + 2)
        sys.stdout.write(label)
    elif edge_idx == HexMap.EDGE_SE:
        gotoxy(col + 1 + (TILE_WIDTH // 2), row + 2)
        sys.stdout.write(label)

    sys.stdout.write("\033[0m")
    sys.stdout.flush()

def draw_node(tile, node_idx, col, row, color=None):

    if color == None:
        sys.stdout.write("\033[91m") #bright red
    else:
        sys.stdout.write(color)

    if node_idx == HexMap.NODE_N:
        gotoxy(col + TILE_WIDTH // 2, row)
        sys.stdout.write("+")
    elif node_idx == HexMap.NODE_NE:
        gotoxy(col + TILE_WIDTH - 1, row)
        sys.stdout.write("+")
    elif node_idx == HexMap.NODE_SE:
        gotoxy(col + TILE_WIDTH - 1, row + 2)
        sys.stdout.write("+")
    elif node_idx == HexMap.NODE_S:
        gotoxy(col + TILE_WIDTH // 2, row + 2)
        sys.stdout.write("+")
    elif node_idx == HexMap.NODE_SW:
        gotoxy(col, row + 2)
        sys.stdout.write("+")
    elif node_idx == HexMap.NODE_NW:
        gotoxy(col, row)
        sys.stdout.write("+")
    sys.stdout.write("\033[0m")
    sys.stdout.flush()

def compute_bounds(hexmap):
    min_q = min(tile.x for tile in hexmap.tiles.values())
    max_q = max(tile.x for tile in hexmap.tiles.values())
    min_r = min(tile.z for tile in hexmap.tiles.values())
    max_r = max(tile.z for tile in hexmap.tiles.values())
    return min_q, max_q, min_r, max_r

def get_map_screen_size(hexmap):
    min_q, max_q, min_r, max_r = compute_bounds(hexmap)
    cols = []
    rows = []

    for tile in hexmap.tiles.values():
        q, r = tile.x, tile.z
        col = (q + (r // 2) - min_q) * (TILE_WIDTH - 1)
        row = (r - min_r) * (TILE_HEIGHT - 1)
        if r % 2 != 0:
            col += TILE_WIDTH // 2
        cols.append(col)
        rows.append(row)

    width = max(cols) + TILE_WIDTH
    height = max(rows) + TILE_HEIGHT
    return width, height

def get_tile_screen_pos(tile, hexmap):
    min_q, max_q, min_r, max_r = compute_bounds(hexmap)
    offset_col = -(min_q + (min_r // 2)) - 1
    offset_row = -min_r

    q, r = tile.x, tile.z
    col = (q + (r // 2) + offset_col) * (TILE_WIDTH - 1)
    row = (r + offset_row) * (TILE_HEIGHT - 1)
    if r % 2 != 0:
        col += TILE_WIDTH // 2
    return col, row


def compute_longest_road_simple(hexmap, player_id):
    G = nx.Graph()

    # Build graph: nodes = global node IDs, edges = player roads
    for edge_id, owner in hexmap.road_owners.items():
        if owner != player_id:
            continue

        tile_coord, edge_idx = hexmap.edge_to_tile[edge_id]
        tile = hexmap.tiles[tile_coord]
        n1 = tile.nodes[edge_idx]
        n2 = tile.nodes[(edge_idx + 1) % 6]

        if n1 != n2:
            G.add_edge(n1, n2)

    # Compute longest simple path
    if not G:
        return 0

    longest = 0
    for node in G.nodes():
        lengths = nx.single_source_dijkstra_path_length(G, node)
        max_len = max(lengths.values())
        if max_len > longest:
            longest = max_len

    return longest


def find_surrounding_tiles_and_nodes(hexmap, edge_id, debug=False):
    WHITE = "\033[37m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"

    if edge_id not in hexmap.edge_to_tile:
        return []

    tile_coord, edge_idx = hexmap.edge_to_tile[edge_id]
    tile = hexmap.tiles[tile_coord]

    n1 = tile.nodes[edge_idx]
    n2 = tile.nodes[(edge_idx + 1) % 6]

    candidate_nodes = []

    # --- Compute candidate nodes first (no drawing yet)
    for node in [n1, n2]:
        for neighbor_tile_coord, neighbor_tile in hexmap.tiles.items():
            for i in range(6):
                e = neighbor_tile.edges[i]
                ni = neighbor_tile.nodes[i]
                ni_next = neighbor_tile.nodes[(i + 1) % 6]

                if e == edge_id:
                    continue  # Skip the input edge itself

                if node in (ni, ni_next):
                    candidate_nodes.append((neighbor_tile, node, i))

    # --- Debug visualization at end:
    if debug:
        drawn_tiles = set()

        # Draw all tiles first:
        for neighbor_tile, _, _ in candidate_nodes:
            if neighbor_tile not in drawn_tiles:
                col, row = get_tile_screen_pos(neighbor_tile, hexmap)
                draw_tile(neighbor_tile, col, row, color=GREEN)
                drawn_tiles.add(neighbor_tile)

        # Then draw all nodes:
        for neighbor_tile, _, edge_idx in candidate_nodes:
            col, row = get_tile_screen_pos(neighbor_tile, hexmap)
            #draw_node(neighbor_tile, edge_idx, col, row, color=YELLOW)
            #draw_node(neighbor_tile, (edge_idx + 1) % 6, col, row, color=YELLOW)

    return candidate_nodes  # list of (tile, node_id, local_edge_idx)


def verify_node_id_consistency(hexmap):
    print("\nVerifying node ID consistency...")

    inconsistent = False
    checked_pairs = set()

    for tile_coord, tile in hexmap.tiles.items():
        for dir_idx, direction in enumerate(hexmap.directions):
            neighbor_coord = (
                tile.x + direction[0],
                tile.y + direction[1],
                tile.z + direction[2]
            )

            # Avoid checking each tile-neighbor pair twice
            pair = tuple(sorted([tile_coord, neighbor_coord]))
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)

            if neighbor_coord in hexmap.tiles:
                neighbor_tile = hexmap.tiles[neighbor_coord]

                # Determine shared edge and opposite edge indices
                edge_idx = dir_idx
                opp_edge_idx = (edge_idx + 3) % 6

                # Nodes at this edge on both tiles
                node_a1 = tile.nodes[edge_idx]
                node_a2 = tile.nodes[(edge_idx + 1) % 6]

                node_b1 = neighbor_tile.nodes[opp_edge_idx]
                node_b2 = neighbor_tile.nodes[(opp_edge_idx + 1) % 6]

                # Check if they match (orientation flipped)
                node1_match = node_a1 == node_b2
                node2_match = node_a2 == node_b1

                if not (node1_match and node2_match):
                    inconsistent = True
                    print("Inconsistent node IDs between tile %s and neighbor %s" % (
                        str(tile_coord), str(neighbor_coord)
                    ))
                    print("  Tile nodes: %d-%d at edge %d" % (node_a1, node_a2, edge_idx))
                    print("  Neighbor nodes: %d-%d at edge %d" % (node_b2, node_b1, opp_edge_idx))

    if not inconsistent:
        print("Node ID consistency verified: all shared nodes match correctly.")
    else:
        print("Node ID inconsistencies detected! Check your build_nodes_and_edges logic.")


def verify_edge_id_consistency(hexmap):
    print("\nVerifying edge ID consistency...")

    def neighbor_coord_func(tile_coord, dir_idx):
        dx, dy, dz = hexmap.directions[dir_idx]
        return (tile_coord[0] + dx, tile_coord[1] + dy, tile_coord[2] + dz)

    inconsistent = False
    checked_pairs = set()

    for tile_coord, tile in hexmap.tiles.items():
        for i in range(6):
            neighbor_coord = neighbor_coord_func(tile_coord, i)
            if neighbor_coord in hexmap.tiles:
                # Avoid duplicate checks
                pair = tuple(sorted([tile_coord, neighbor_coord]))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)

                neighbor_tile = hexmap.tiles[neighbor_coord]

                my_edge_id = tile.edges[i]
                opp_edge_idx = (i + 3) % 6
                their_edge_id = neighbor_tile.edges[opp_edge_idx]

                if my_edge_id != their_edge_id:
                    inconsistent = True
                    print("Inconsistent edge IDs between tile %s and neighbor %s" %
                          (str(tile_coord), str(neighbor_coord)))
                    print("  Tile edge %d = edge ID %d" % (i, my_edge_id))
                    print("  Neighbor edge %d = edge ID %d" % (opp_edge_idx, their_edge_id))

    if not inconsistent:
        print("Edge ID consistency verified: all shared edges match correctly.")
    else:
        print("Edge ID inconsistencies detected! Check your build_nodes_and_edges edge assignment.")


def check_degenerate_edges(hexmap):
    print("\nChecking degenerate edges (same node on both ends)...")

    degenerate_edges = []

    for edge_id in hexmap.edge_ids.values():
        tile_coord, edge_idx = hexmap.edge_to_tile[edge_id]
        tile = hexmap.tiles[tile_coord]

        n1 = tile.nodes[edge_idx]
        n2 = tile.nodes[(edge_idx + 1) % 6]

        if n1 == n2:
            degenerate_edges.append((edge_id, tile_coord, edge_idx))

    if not degenerate_edges:
        print("No degenerate edges found.")
    else:
        print("Degenerate edges detected:")
        for edge_id, tile_coord, edge_idx in degenerate_edges:
            print("  Edge ID %d on tile %s at index %d (nodes %d-%d)" %
                  (edge_id, str(tile_coord), edge_idx, tile.nodes[edge_idx], tile.nodes[(edge_idx + 1) % 6]))
            

def random_branching_road_walk(hexmap, player_id=1, steps=20, boundary_nodes=None):
    import time
    visited_edges = set()
    visited_nodes = set()

    all_nodes = list(hexmap.node_ids.values())

    if boundary_nodes is None:
        boundary_nodes = set()

    non_boundary_nodes = [n for n in all_nodes if n not in boundary_nodes]
    if not non_boundary_nodes:
        return  # No valid starting node

    # Start from a random non-boundary node
    start_node = random.choice(non_boundary_nodes)
    frontier = [start_node]
    visited_nodes.add(start_node)

    for _ in range(steps):
        if not frontier:
            break  # No more frontier to expand

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
                        continue  # Skip visited or boundary node

                    neighbors.append((tile, i, e, other_node))

        if not neighbors:
            frontier.remove(current_node)
            continue

        # Pick one randomly
        tile, edge_idx, edge_id, new_node = random.choice(neighbors)

        col, row = get_tile_screen_pos(tile, hexmap)

        RED = "\033[31m"
        if player_id == 1:
            draw_road(tile, edge_idx, col, row, color=RED)
        else:
            draw_road(tile, edge_idx, col, row)

        hexmap.road_owners[edge_id] = player_id

        visited_edges.add(edge_id)
        visited_nodes.add(new_node)
        frontier.append(new_node)


def get_boundary_nodes(hexmap):
    boundary_nodes = set()

    for tile_coord, tile in hexmap.tiles.items():
        for dir_idx in range(6):
            dx, dy, dz = hexmap.directions[dir_idx]
            neighbor_coord = (tile.x + dx, tile.y + dy, tile.z + dz)

            if neighbor_coord not in hexmap.tiles:
                # This edge points outward -> nodes on this edge are boundary nodes
                node_a = tile.nodes[dir_idx]
                node_b = tile.nodes[(dir_idx + 1) % 6]

                boundary_nodes.add(node_a)
                boundary_nodes.add(node_b)

    return boundary_nodes


if __name__ == "__main__":
    sys.stdout.write("\033[2J")
    sys.stdout.flush()
    gotoxy(0, 0)

    hexmap = HexMap()
    hexmap.generate_default_map(radius=3)
    hexmap.build_nodes_and_edges()

    WHITE = "\033[37m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    GREY = "\033[90m"   

    for tile in hexmap.tiles.values():
        col, row = get_tile_screen_pos(tile, hexmap)
        draw_tile(tile, col, row, GREY)

    boundary_nodes = get_boundary_nodes(hexmap)

    for tile in hexmap.tiles.values():
        col, row = get_tile_screen_pos(tile, hexmap)
        for idx, node_id in enumerate(tile.nodes):
            if node_id in boundary_nodes:
                draw_node(tile, idx, col, row, color=WHITE)  # White color

    #get neighboring tiles

    #center = (0, 0, 0)
    #neighbors = set()
    #for dx, dy, dz in hexmap.directions:
    #    neighbor_tile = (center[0]+dx, center[1]+dy, center[2]+dz)
    #    if neighbor_tile in hexmap.tiles:
    #        neighbors.add(neighbor_tile)
    #neighbors.add(center)

    # draw neighboring tiles
    #for coord in neighbors:
    #    tile = hexmap.tiles[coord]
    #    col, row = get_tile_screen_pos(tile, hexmap)
    #    draw_tile(tile, col, row, GREY)

    random_branching_road_walk(hexmap, player_id=1, steps=4, boundary_nodes=boundary_nodes)
    random_branching_road_walk(hexmap, player_id=2, steps=5, boundary_nodes=boundary_nodes)
    
    # surrounding tiles and nodes for a random edge
    #edges = list(hexmap.edge_ids.values())
    #edge_id = random.choice(edges)
    
    #store road
    #hexmap.road_owners[edge_id] = 1

    #candidate_nodes = find_surrounding_tiles_and_nodes(hexmap, edge_id, debug=True)
    #for tile, node_idx, dir_idx in candidate_nodes:
    #    #draw_node(tile, node_idx, *get_tile_screen_pos(tile, hexmap))
    #    draw_road(tile, dir_idx, *get_tile_screen_pos(tile, hexmap))
    #    #store road
    #    edge_id = tile.edges[dir_idx]
    #    hexmap.road_owners[edge_id] = 1


    width, height = get_map_screen_size(hexmap)
    gotoxy(0, height)

    length = compute_longest_road_simple(hexmap, 1)
    print("Longest road for player 1: %d tiles" % length)
    length = compute_longest_road_simple(hexmap, 2)
    print("Longest road for player 2: %d tiles" % length)

    #verify_node_id_consistency(hexmap)
    #verify_edge_id_consistency(hexmap)
    #check_degenerate_edges(hexmap)


    #for edge_id_owner in hexmap.road_owners.items():
    #    edge_id = edge_id_owner[0]
    #    owner = edge_id_owner[1]
    #    tile_coord, edge_idx = hexmap.edge_to_tile[edge_id]
    #    tile = hexmap.tiles[tile_coord]
    #    n1 = tile.nodes[edge_idx]
    #    n2 = tile.nodes[(edge_idx + 1) % 6]
    #    print("Edge %d (%s, edge %d) -> nodes %d, %d, owner=%s" % (
    #        edge_id, str(tile_coord), edge_idx, n1, n2, str(owner)
    #    ))

    # --- Custom test: draw NW road and N node on tile (0,3,-3)
    #test_coord = (0, 3, -3)
    #if test_coord in hexmap.tiles:
    #    tile = hexmap.tiles[test_coord]
    #    col, row = get_tile_screen_pos(tile, hexmap)
    #    edge_idx = hexmap.EDGE_W # NW, NE, E, SE, SW, W edge
    #    node_idx = hexmap.NODE_SW  # N, NE, NW, S, SE, SW node
    #    draw_road(tile, edge_idx, col, row)
    #    draw_node(tile, node_idx, col, row)

    # --- Custom test: draw NW road and N node on tile (0,3,-3)
    #test_coord = (-1, 3, -2)
    #if test_coord in hexmap.tiles:
    #    tile = hexmap.tiles[test_coord]
    #    col, row = get_tile_screen_pos(tile, hexmap)
    #    edge_idx = hexmap.EDGE_W # NW, NE, E, SE, SW, W edge
    #    node_idx = hexmap.NODE_SW  # N, NE, NW, S, SE, SW node
    #    draw_road(tile, edge_idx, col, row)
    #    draw_node(tile, node_idx, col, row)

    # --- Debug print amount of nodes and edges
    #selected_nodes = set()
    #selected_edges = set()
    #for coord in neighbors:
    #    tile = hexmap.tiles[coord]
    #    selected_nodes.update(tile.nodes)
    #    selected_edges.update(tile.edges)
    #print("\nTiles: %d" % hexmap.tile_autoinc)
    #print("Nodes in selection: %d unique" % len(selected_nodes))
    #print("Edges in selection: %d unique" % len(selected_edges))
    #print("All Nodes (global): %d total" % len(hexmap.node_ids))
    #print("All Edges (global): %d total" % len(hexmap.edge_ids))

    # --- Debug print of all tiles, nodes and edges
    #for tile_coord, tile in hexmap.tiles.items():
    #    print("Tile %s nodes:" % str(tile_coord))
    #    for idx, node in enumerate(tile.nodes):
    #        print("  Node idx %d = global node id %d" % (idx, node))
    #        print("Tile %s edges:" % str(tile_coord))
    #    for idx, edge in enumerate(tile.edges):
    #        print("  Edge idx %d = global edge id %d" % (idx, edge))
