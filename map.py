import sys

TILE_WIDTH = 11
TILE_HEIGHT = 3

class HexTile(object):
    def __init__(self, x, y, z, tile_type="blank"):
        assert x + y + z == 0
        self.x = x
        self.y = y
        self.z = z
        self.tile_type = tile_type

class HexMap(object):
    def __init__(self):
        self.tiles = {}

    def add_tile(self, x, y, z, tile_type="blank"):
        self.tiles[(x, y, z)] = HexTile(x, y, z, tile_type="blank")

    def generate_default_map(self, radius=3):
        for x in range(-radius, radius + 1):
            for y in range(-radius, radius + 1):
                z = -x - y
                if -radius <= z <= radius:
                    self.add_tile(x, y, z, tile_type="land")

def gotoxy(x, y):
    sys.stdout.write("\033[%d;%dH" % (y + 1, x + 1))
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
        q = tile.x
        r = tile.z
        s = tile.y

        col = (q + (r // 2) + offset_col) * (TILE_WIDTH - 1)
        row = (r + offset_row) * (TILE_HEIGHT - 1)

        if r % 2 != 0:
            col += TILE_WIDTH // 2

        # Prepare border strings
        border = "+----+----+" #.ljust(TILE_WIDTH)

        # Format coordinate string with vertical bars at start/end
        coord_str = "(%d,%d,%d)" % (q, s, r)
        coord_str = coord_str.center(TILE_WIDTH - 2)
        coord_line = "|" + coord_str + "|"

        # Write top border
        gotoxy(col, row)
        sys.stdout.write(border)

        # Write coordinate line
        gotoxy(col, row + 1)
        sys.stdout.write(coord_line)

        # Write bottom border
        gotoxy(col, row + 2)
        sys.stdout.write(border)

        sys.stdout.flush()

if __name__ == "__main__":
    sys.stdout.write("\033[2J")  # Clear screen
    sys.stdout.flush()

    hexmap = HexMap()
    hexmap.generate_default_map(radius=3)
    render_coordinates(hexmap)
