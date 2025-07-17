import sys
import random

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
        dir_index = {d: i for i, d in enumerate(self.directions)}

        def neighbor(tile, dir_idx):
            dx, dy, dz = self.directions[dir_idx]
            return (tile[0]+dx, tile[1]+dy, tile[2]+dz)

        edge_id_map = {}
        node_id_map = {}
        next_edge_id = 0
        next_node_id = 0

        # --- Pass 1: assign unique edge IDs
        for tile_coord in self.tiles:
            for dir_idx in range(6):
                neighbor_tile = neighbor(tile_coord, dir_idx)
                if neighbor_tile in self.tiles:
                    key = tuple(sorted([tile_coord, neighbor_tile]))
                else:
                    key = (tile_coord, dir_idx)

                if key not in edge_id_map:
                    edge_id_map[key] = next_edge_id
                    next_edge_id += 1

                    if isinstance(key[1], int):
                        canonical_tile = tile_coord
                        canonical_edge_idx = dir_idx
                    else:
                        ta, tb = key
                        canonical_tile = min(ta, tb)
                        if canonical_tile == tile_coord:
                            canonical_edge_idx = dir_idx
                        else:
                            reverse_idx = (dir_idx + 3) % 6
                            canonical_edge_idx = reverse_idx
                            canonical_tile = neighbor_tile

                    self.edge_to_tile[edge_id_map[key]] = (canonical_tile, canonical_edge_idx)

        def edge_id(a, d_or_b):
            if isinstance(d_or_b, int):
                key = (a, d_or_b)
            else:
                key = tuple(sorted([a, d_or_b]))
            return edge_id_map[key]

        # --- Pass 2: assign edges and nodes explicitly according to NODE_x / EDGE_x convention
        for tile_coord, tile in self.tiles.items():
            tile_edges = []
            corner_node_ids = []

            for i in range(6):
                neighbor_tile = neighbor(tile_coord, i)
                eid = edge_id(tile_coord, neighbor_tile if neighbor_tile in self.tiles else i)
                tile_edges.append(eid)

            # Now assign nodes: for each NODE_i (corner i), define it as the node between edges (i-1, i)
            for i in range(6):
                prev_edge_idx = (i - 1) % 6
                curr_edge_idx = i
                edges_at_corner = [tile_edges[prev_edge_idx], tile_edges[curr_edge_idx]]

                key = tuple(sorted(edges_at_corner))
                if key not in node_id_map:
                    node_id_map[key] = next_node_id
                    next_node_id += 1

                corner_node_ids.append(node_id_map[key])

            tile.edges = tile_edges
            tile.nodes = corner_node_ids

        self.node_ids = node_id_map
        self.edge_ids = edge_id_map
        self.node_autoinc = next_node_id
        self.edge_autoinc = next_edge_id


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

def draw_road(tile, edge_idx, col, row):
    sys.stdout.write("\033[34m")
    road_width = (TILE_WIDTH - 3) // 2

    dir_labels = {
        HexMap.EDGE_E: "|E",
        HexMap.EDGE_NE: "=NE=",
        HexMap.EDGE_NW: "=NW=",
        HexMap.EDGE_W: "|W",
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


def road_walk_old(hexmap, steps=10):
    import time
    visited = set()
    visited_nodes = set()
    edges = list(hexmap.edge_ids.values())
    if not edges:
        return

    # --- Start from random edge
    edge = random.choice(edges)
    tile_coord, edge_idx = hexmap.edge_to_tile[edge]
    tile = hexmap.tiles[tile_coord]

    # --- Defensive fix: explicitly mark first edge's nodes as visited BEFORE loop
    node_a = hexmap.tiles[tile_coord].nodes[edge_idx]
    node_b = hexmap.tiles[tile_coord].nodes[(edge_idx + 1) % 6]
    visited_nodes.update([node_a, node_b])

    for _ in range(steps):
        # Draw current edge
        col, row = get_tile_screen_pos(tile, hexmap)
        draw_road(tile, edge_idx, col, row)

        draw_node(tile, edge_idx, col, row)
        draw_node(tile, (edge_idx + 1) % 6, col, row)

        visited.add(edge)

        candidates = []

        # --- Neighbor tile search
        dx, dy, dz = hexmap.directions[edge_idx]
        neighbor_coord = (tile.x + dx, tile.y + dy, tile.z + dz)

        if neighbor_coord in hexmap.tiles:
            neighbor_tile = hexmap.tiles[neighbor_coord]
            neighbor_edge_idx = (edge_idx + 3) % 6  # Opposite edge on neighbor

            shared_node_a = neighbor_tile.nodes[neighbor_edge_idx]
            shared_node_b = neighbor_tile.nodes[(neighbor_edge_idx + 1) % 6]

            for idx, e in enumerate(neighbor_tile.edges):
                if e in visited:
                    continue
                n1 = neighbor_tile.nodes[idx]
                n2 = neighbor_tile.nodes[(idx + 1) % 6]
                if shared_node_a in (n1, n2) or shared_node_b in (n1, n2):
                    if not (n1 in visited_nodes and n2 in visited_nodes):
                        node_used = shared_node_a if shared_node_a in (n1, n2) else shared_node_b
                        candidates.append((neighbor_tile, idx, e, node_used))

        # --- Global fallback search
        if not candidates:
            for node in visited_nodes:
                for t_coord, t in hexmap.tiles.items():
                    for i in range(6):
                        e = t.edges[i]
                        if e in visited:
                            continue
                        n1 = t.nodes[i]
                        n2 = t.nodes[(i + 1) % 6]
                        if node in (n1, n2):
                            if not (n1 in visited_nodes and n2 in visited_nodes):
                                candidates.append((t, i, e, node))

        if not candidates:
            break  # No valid next step, terminate gracefully

        tile, edge_idx, edge, chosen_node = random.choice(candidates)

        visited_nodes.update([tile.nodes[edge_idx], tile.nodes[(edge_idx + 1) % 6]])

        time.sleep(0.1)


def node_walker(hexmap, steps=10):
    import time
    visited_nodes = set()

    # STEP 1: Start from random edge
    edge = random.choice(list(hexmap.edge_ids.values()))
    tile_coord, edge_idx = hexmap.edge_to_tile[edge]
    tile = hexmap.tiles[tile_coord]

    node_a = tile.nodes[edge_idx]
    node_b = tile.nodes[(edge_idx + 1) % 6]
    visited_nodes.update([node_a, node_b])

    # Draw initial edge and nodes
    col, row = get_tile_screen_pos(tile, hexmap)
    draw_road(tile, edge_idx, col, row)
    draw_node(tile, edge_idx, col, row)
    draw_node(tile, (edge_idx + 1) % 6, col, row)

    current_node = node_a  # Start from one of the two nodes
    step = 1

    while step <= steps:
        # Find all tiles that contain this node
        candidate_tiles = []
        for t_coord, t in hexmap.tiles.items():
            if current_node in t.nodes:
                candidate_tiles.append((t_coord, t))

        next_move_found = False
        for t_coord, t in candidate_tiles:
            for i in range(6):
                n1 = t.nodes[i]
                n2 = t.nodes[(i + 1) % 6]
                if current_node in (n1, n2):
                    if not (n1 in visited_nodes and n2 in visited_nodes):
                        # Found a next edge that touches current_node
                        col, row = get_tile_screen_pos(t, hexmap)
                        draw_road(t, i, col, row)
                        draw_node(t, i, col, row)
                        draw_node(t, (i + 1) % 6, col, row)

                        visited_nodes.update([n1, n2])
                        # Pick one of these as next current_node
                        current_node = n2 if current_node == n1 else n1
                        next_move_found = True
                        break
            if next_move_found:
                break

        if not next_move_found:
            # Fallback: look for neighbor tiles geometrically around current node
            # This happens if we hit a corner edge at map boundary
            for node_idx in range(6):
                if current_node in tile.nodes:
                    idx_in_tile = tile.nodes.index(current_node)
                    neighbor_tiles = node_neighbor_tiles(tile_coord, idx_in_tile, hexmap)
                    for neighbor_coord in neighbor_tiles:
                        if neighbor_coord not in hexmap.tiles:
                            continue
                        neighbor_tile = hexmap.tiles[neighbor_coord]
                        for i in range(6):
                            n1 = neighbor_tile.nodes[i]
                            n2 = neighbor_tile.nodes[(i + 1) % 6]
                            if current_node in (n1, n2):
                                if not (n1 in visited_nodes and n2 in visited_nodes):
                                    col, row = get_tile_screen_pos(neighbor_tile, hexmap)
                                    draw_road(neighbor_tile, i, col, row)
                                    draw_node(neighbor_tile, i, col, row)
                                    draw_node(neighbor_tile, (i + 1) % 6, col, row)

                                    visited_nodes.update([n1, n2])
                                    current_node = n2 if current_node == n1 else n1
                                    next_move_found = True
                                    break
                        if next_move_found:
                            break
            if not next_move_found:
                break  # Completely stuck; exit loop

        step += 1
        time.sleep(0.1)


def node_neighbor_tiles(tile_coord, node_idx, hexmap):
    d1 = hexmap.directions[node_idx]
    neighbor1 = (tile_coord[0] + d1[0], tile_coord[1] + d1[1], tile_coord[2] + d1[2])

    d2 = hexmap.directions[(node_idx - 1) % 6]
    neighbor2 = (tile_coord[0] + d2[0], tile_coord[1] + d2[1], tile_coord[2] + d2[2])

    return [neighbor1, neighbor2]


    """
    Find all surrounding tiles and nodes where a road connected to a given edge can attach.

    Summary:
    --------
    Given a global edge ID, this function identifies neighboring tiles and node indices
    that are adjacent to that edge and could serve as valid connection points for roads.

    It works by:
    1. Locating the tile and local edge index corresponding to the given global edge.
    2. Checking neighbor tiles in the clockwise and counterclockwise directions around the edge.
    3. Adding node candidates from these neighbors based on relative positions.
    4. If insufficient candidates are found (e.g. at a map edge), fallback nodes from the
       current tile are included.
    5. Handling special directional cases (e.g. EDGE_E and EDGE_W neighbors).
    6. Optionally rendering debug highlights if debug=True.

    Parameters:
    -----------
    hexmap : HexMap
        The hex map containing tiles, edges, nodes, and directional info.

    edge : int
        The global edge ID for which to find surrounding nodes.

    debug : bool (default False)
        If True, visually highlights the involved tiles and nodes for inspection.

    Returns:
    --------
    candidate_nodes : list of (node_idx, tile) tuples
        A list of node indices and corresponding tile objects where attachment is possible.

    Notes:
    ------
    - Neighbor relationships are determined geometrically based on hex directions.
    - Handles map boundaries gracefully by falling back to local tile nodes.
    - Designed for pointy-top hex orientation.

    Example:
    --------
    edge = random.choice(list(hexmap.edge_ids.values()))
    nodes = find_surrounding_tiles_and_nodes(hexmap, edge, debug=True)
    for node_idx, tile in nodes:
        print("Node %d on tile (%d, %d, %d)" % (node_idx, tile.x, tile.y, tile.z))
    """
def find_surrounding_tiles_and_nodes(hexmap, edge, debug=False):
    WHITE = "\033[37m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    GREEN = "\033[32m"

    candidate_nodes = []  # Now list of (tile, node_idx, direction_idx)

    tile_coord, edge_idx = hexmap.edge_to_tile[edge]
    #tile_coord = (-3,1,2)
    #edge_idx = hexmap.EDGE_NW  # Example edge for testing

    tile = hexmap.tiles[tile_coord]

    # --- 1st neighboring tile
    direction = hexmap.directions[(edge_idx+1)%6]
    neighbor_coord = (tile.x + direction[0], tile.y + direction[1], tile.z + direction[2])
    if neighbor_coord in hexmap.tiles:
        tile_a = hexmap.tiles[neighbor_coord]
        if debug:
            draw_tile(tile_a, *get_tile_screen_pos(tile_a, hexmap), color=YELLOW)
        node_a_idx_1 = (((edge_idx+3) % 6) + 1) % 6
        node_a_idx_2 = (((edge_idx+3) % 6) + 3) % 6
        candidate_nodes.append((tile_a, node_a_idx_1, node_a_idx_1))
        candidate_nodes.append((tile_a, node_a_idx_2, (node_a_idx_2 -1) % 6))

    # --- 2nd neighboring tile
    direction = hexmap.directions[(edge_idx-1)%6]
    neighbor_coord = (tile.x + direction[0], tile.y + direction[1], tile.z + direction[2])
    if neighbor_coord in hexmap.tiles:
        tile_b = hexmap.tiles[neighbor_coord]
        if debug:
            draw_tile(tile_b, *get_tile_screen_pos(tile_b, hexmap), color=YELLOW)
        node_b_idx_1 = (edge_idx+1) % 6
        node_b_idx_2 = (edge_idx+3) % 6
        candidate_nodes.append((tile_b, node_b_idx_1, node_b_idx_1))
        candidate_nodes.append((tile_b, node_b_idx_2, (node_b_idx_2-1)%6))

    # --- Fallback: current tile nodes if too few found
    if len(candidate_nodes) < 4:
        if debug:
            draw_tile(tile, *get_tile_screen_pos(tile, hexmap), color=GREEN)
        fallback_node_1 = (edge_idx-1)%6
        fallback_node_2 = (edge_idx+2)%6
        candidate_nodes.append((tile, fallback_node_1, fallback_node_1))
        candidate_nodes.append((tile, fallback_node_2, (fallback_node_2-1) %6))

        # Check special cases for E/W/NW/NE edges
        neighbors = [
            (hexmap.EDGE_E, 1, 'east'),
            (hexmap.EDGE_W, 4, 'west'),
            (hexmap.EDGE_NW, 5, 'nw'),
            (hexmap.EDGE_NE, 0, 'ne')
        ]

        for edge_type, dir_idx, label in neighbors:
            if edge_idx == edge_type:
                d = hexmap.directions[dir_idx]
                neighbor_coord = (tile.x + d[0], tile.y + d[1], tile.z + d[2])
                neighbor_tile = hexmap.tiles.get(neighbor_coord)
                if neighbor_tile:
                    idx1 = (((edge_idx+3) % 6) + 5) % 6
                    idx2 = (((edge_idx+3) % 6) + 2) % 6
                    candidate_nodes.append((neighbor_tile, idx1, idx1))
                    candidate_nodes.append((neighbor_tile, idx2, (idx2-1)%6))
                    if debug:
                        draw_tile(neighbor_tile, *get_tile_screen_pos(neighbor_tile, hexmap), color=RED)

    # Debug draw central tile and edge
    if debug:
        draw_road(tile, edge_idx, *get_tile_screen_pos(tile, hexmap))
        draw_node(tile, edge_idx, *get_tile_screen_pos(tile, hexmap))
        draw_node(tile, (edge_idx+1) % 6, *get_tile_screen_pos(tile, hexmap))

    # Debug draw all candidate nodes
    if debug:
        for node_tile, node_idx, _ in candidate_nodes:
            draw_node(node_tile, node_idx, *get_tile_screen_pos(node_tile, hexmap), color=WHITE)

    return candidate_nodes  # Now contains (tile, node_idx, direction_idx)



if __name__ == "__main__":
    sys.stdout.write("\033[2J")
    sys.stdout.flush()

    hexmap = HexMap()
    hexmap.generate_default_map(radius=1)
    hexmap.build_nodes_and_edges()

    WHITE = "\033[37m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    GREY = "\033[90m"   

    for tile in hexmap.tiles.values():
        col, row = get_tile_screen_pos(tile, hexmap)
        draw_tile(tile, col, row, GREY)


    #get neighboring tiles

    center = (0, 0, 0)
    neighbors = set()
    for dx, dy, dz in hexmap.directions:
        neighbor = (center[0]+dx, center[1]+dy, center[2]+dz)
        if neighbor in hexmap.tiles:
            neighbors.add(neighbor)
    neighbors.add(center)

    # draw neighboring tiles
    for coord in neighbors:
        tile = hexmap.tiles[coord]
        col, row = get_tile_screen_pos(tile, hexmap)
        draw_tile(tile, col, row, GREY)


    #walk_road(hexmap, steps=10)
    #node_walker(hexmap, steps=3)

    # surrounding tiles and nodes for a random edge
    edges = list(hexmap.edge_ids.values())
    edge = random.choice(edges)
    candidate_nodes = find_surrounding_tiles_and_nodes(hexmap, edge, debug=True)

    for tile, node_idx, dir_idx in candidate_nodes:
        #draw_node(tile, node_idx, *get_tile_screen_pos(tile, hexmap))
        draw_road(tile, dir_idx, *get_tile_screen_pos(tile, hexmap))

    width, height = get_map_screen_size(hexmap)
    gotoxy(0, height)

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
