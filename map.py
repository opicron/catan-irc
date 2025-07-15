import sys

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
    def __init__(self, orientation="pointy"):
        self.tiles = {}
        self.tile_autoinc = 0
        self.node_ids = {}
        self.edge_ids = {}
        self.node_autoinc = 0
        self.edge_autoinc = 0
        self.orientation = orientation

        if orientation == "pointy":
            self.directions = [
                (1, -1, 0),  # E
                (1, 0, -1),  # NE
                (0, 1, -1),  # NW
                (-1, 1, 0),  # W
                (-1, 0, 1),  # SW
                (0, -1, 1)   # SE
            ]
        elif orientation == "flat":
            self.directions = [
                (1, -1, 0),  # E
                (0, -1, 1),  # SE
                (-1, 0, 1),  # SW
                (-1, 1, 0),  # W
                (0, 1, -1),  # NW
                (1, 0, -1)   # NE
            ]
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

        # First pass: compute unique edges
        for tile in self.tiles:
            for dir_idx in range(6):
                neighbor_tile = neighbor(tile, dir_idx)
                if neighbor_tile in self.tiles:
                    key = tuple(sorted([tile, neighbor_tile]))
                else:
                    key = (tile, dir_idx)
                if key not in edge_id_map:
                    edge_id_map[key] = next_edge_id
                    next_edge_id += 1

        # Helper for retrieving edge id
        def edge_id(a, d_or_b):
            if isinstance(d_or_b, int):
                key = (a, d_or_b)
            else:
                key = tuple(sorted([a, d_or_b]))
            return edge_id_map[key]

        # Second pass: compute unique nodes and attach edges/nodes to tiles
        for tile_coord, tile in self.tiles.items():
            tile_edges = []
            corner_node_ids = set()

            for i in range(6):
                # Assign edges
                neighbor_tile = neighbor(tile_coord, i)
                eid = edge_id(tile_coord, neighbor_tile if neighbor_tile in self.tiles else i)
                tile_edges.append(eid)

            for i in range(6):
                j = (i+1) % 6
                A = tile_coord
                B = neighbor(A, i)
                C = neighbor(A, j)
                has_B = B in self.tiles
                has_C = C in self.tiles

                edges = [
                    edge_id(A, B if has_B else i),
                    edge_id(A, C if has_C else j)
                ]

                if has_B and has_C:
                    k = tuple(sorted([B, C]))
                    if k in edge_id_map:
                        edges.append(edge_id_map[k])
                elif has_B:
                    diff = (C[0]-B[0], C[1]-B[1], C[2]-B[2])
                    if diff in dir_index:
                        idx = dir_index[diff]
                        edges.append(edge_id(B, idx))
                elif has_C:
                    diff = (B[0]-C[0], B[1]-C[1], B[2]-C[2])
                    if diff in dir_index:
                        idx = dir_index[diff]
                        edges.append(edge_id(C, idx))

                key = tuple(sorted(set(edges)))
                if key not in node_id_map:
                    node_id_map[key] = next_node_id
                    next_node_id += 1

                corner_node_ids.add(node_id_map[key])

            tile.edges = tile_edges
            tile.nodes = list(corner_node_ids)

        self.node_ids = node_id_map
        self.edge_ids = edge_id_map
        self.node_autoinc = next_node_id
        self.edge_autoinc = next_edge_id


def gotoxy(x, y):
    sys.stdout.write("\033[%d;%dH" % (y + 1, x + 1))
    sys.stdout.flush()

def draw_tile(tile, col, row, highlight=False):
    border = "+----+----+"
    coord_str = "(%d,%d,%d)" % (tile.x, tile.y, tile.z)
    coord_str = coord_str.center(TILE_WIDTH - 2)
    coord_line = "|" + coord_str + "|"

    if highlight:
        sys.stdout.write("\033[33m")
    else:
        sys.stdout.write("\033[0m")

    gotoxy(col, row)
    sys.stdout.write(border)
    gotoxy(col, row + 1)
    sys.stdout.write(coord_line)
    gotoxy(col, row + 2)
    sys.stdout.write(border)

    sys.stdout.flush()

def compute_bounds(hexmap):
    min_q = min(tile.x for tile in hexmap.tiles.values())
    max_q = max(tile.x for tile in hexmap.tiles.values())
    min_r = min(tile.z for tile in hexmap.tiles.values())
    max_r = max(tile.z for tile in hexmap.tiles.values())
    return min_q, max_q, min_r, max_r

def render_coordinates(hexmap):
    min_q, max_q, min_r, max_r = compute_bounds(hexmap)
    offset_col = -(min_q + (min_r // 2)) - 1
    offset_row = -min_r

    for tile in hexmap.tiles.values():
        q, r, s = tile.x, tile.z, tile.y
        col = (q + (r // 2) + offset_col) * (TILE_WIDTH - 1)
        row = (r + offset_row) * (TILE_HEIGHT - 1)
        if r % 2 != 0:
            col += TILE_WIDTH // 2

        draw_tile(tile, col, row)

if __name__ == "__main__":
    sys.stdout.write("\033[2J")
    sys.stdout.flush()

    hexmap = HexMap(orientation="pointy")
    hexmap.generate_default_map(radius=3)
    hexmap.build_nodes_and_edges()

    center = (0, 0, 0)
    neighbors = set()
    for dx, dy, dz in hexmap.directions:
        neighbor = (center[0]+dx, center[1]+dy, center[2]+dz)
        if neighbor in hexmap.tiles:
            neighbors.add(neighbor)
    neighbors.add(center)

    render_coordinates(hexmap)

    min_q, max_q, min_r, max_r = compute_bounds(hexmap)
    offset_col = -(min_q + (min_r // 2)) - 1
    offset_row = -min_r

    for coord in neighbors:
        tile = hexmap.tiles[coord]
        q, r, s = tile.x, tile.z, tile.y
        col = (q + (r // 2) + offset_col) * (TILE_WIDTH - 1)
        row = (r + offset_row) * (TILE_HEIGHT - 1)
        if r % 2 != 0:
            col += TILE_WIDTH // 2
        draw_tile(tile, col, row, highlight=True)

    selected_nodes = set()
    selected_edges = set()
    for coord in neighbors:
        tile = hexmap.tiles[coord]
        selected_nodes.update(tile.nodes)
        selected_edges.update(tile.edges)

    print("\nTiles: %d" % hexmap.tile_autoinc)
    print("Nodes in selection: %d unique" % len(selected_nodes))
    print("Edges in selection: %d unique" % len(selected_edges))

    print("\nAll Nodes (global): %d total" % len(hexmap.node_ids))
    #for node_key, node_id in hexmap.node_ids.items():
    #    print("Node %d: edges=%s" % (node_id, node_key))

    print("\nAll Edges (global): %d total" % len(hexmap.edge_ids))
    #for edge_key, edge_id in hexmap.edge_ids.items():
    #    print("Edge %d: %s" % (edge_id, edge_key))
