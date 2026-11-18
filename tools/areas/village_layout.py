"""Episode 1 village expansion (November 2026): where the four new areas and their
side lanes lie round the family compound. Plain Python, no Blender, so the area
builders, the terrain patch and the preview scripts share one plan.

Blender space, metres: x east, y north (the back of the house faces north, the
road along the paddies is south). The game's Babylon space mirrors it:
x = -x, z = -y (src/episodes/ep1/data/forestBorder.ts keeps the same plan).

Approved map (2026-11-17): the compound stays where it is; an old family yard
to the west (ruined first house, rice granary, buffalo byre), a pond with a
bathing jetty and sala to the east, a back garden to the north (ancestor stupa,
well, termite mounds) and a Neak Ta grove to the south-west round the banyan
shrine. Play area about 120 x 140 m; still no neighbours.
"""
import math

# The authored ground (1 m grid) and where Sora is held (walls in the thicket).
TERRAIN = {"x0": -65.0, "x1": 65.0, "y0": -92.0, "y1": 57.0}
PLAY = {"x0": -60.0, "x1": 60.0, "y0": -88.0, "y1": 52.0}
# The ground before the expansion: its heights are kept exactly.
OLD_TERRAIN = {"x0": -40.0, "x1": 40.0, "y0": -92.0, "y1": 40.0}

# ------------------------------------------------------------------ areas
# Each clearing is an ellipse (cx, cy, rx, ry, turn): open ground, no forest.

WEST_YARD = {
    "clearing": (-41.0, 15.5, 12.5, 11.0, math.radians(-6)),
    "house": (-45.0, 20.0, math.radians(8)),      # ruined first house, ridge east-west
    "granary": (-35.2, 23.6, math.radians(-4)),
    "byre": (-44.5, 7.6, math.radians(3)),
    "stack": (-37.2, 9.2),                        # rice-straw stack
    "cart": (-36.4, 15.0, math.radians(200)),     # the old ox cart, pole down
    "old_tree": (-32.0, 18.0),                    # the yard's old tree (HERO_TREES)
}

EAST_POND = {
    "clearing": (38.0, 12.5, 15.5, 11.5, math.radians(4)),
    "water": (38.5, 12.0, 9.5, 6.0, math.radians(4)),
    "jetty": (29.4, 11.4, 0.0),                   # root on the west bank, runs east
    "sala": (37.0, 22.6, math.radians(180)),      # on the north bank, open to the pond
}

NORTH_GARDEN = {
    "clearing": (-1.0, 42.5, 15.0, 9.0, 0.0),
    "stupa": (-6.0, 45.5, 0.0),
    "well": (8.0, 41.0),
    "termites": [(12.5, 47.0, 2.6), (-13.0, 37.5, 2.1), (3.5, 49.5, 1.7)],
    "gate": (3.6, 32.0),                          # gap in the back fence by the rear stairs
}

NEAKTA_GROVE = {
    # A dark grove under old trees rather than a clearing: the floor is kept open.
    "clearing": (-17.0, -35.0, 11.0, 9.0, math.radians(10)),
    "shrine": (-3.9, -34.9),                      # rebuilt banyan shrine (do not move)
}

AREAS = {"west": WEST_YARD, "east": EAST_POND, "north": NORTH_GARDEN, "grove": NEAKTA_GROVE}
# Areas built into the village so far (each is added once the user has approved
# its renders); the others stay forest. Previews add to it in memory.
BUILT = {"west"}

# ------------------------------------------------------------------ lanes
# Narrow trodden lanes (about 1.1 m), west yard -> grove -> path makes a loop.

ALL_LANES = {
    "west": [(-13.0, 11.0), (-18.0, 11.2), (-23.0, 12.6), (-29.0, 14.0)],
    "east": [(13.0, 8.0), (18.0, 9.0), (22.5, 12.3), (27.2, 11.6)],
    "north": [(3.6, 32.0), (3.2, 36.0), (0.5, 40.0), (-3.5, 43.5)],
    "grove": [(-1.6, -33.0), (-9.5, -36.8), (-17.5, -35.2), (-24.0, -30.5)],
    "loop": [(-24.0, -30.5), (-27.0, -20.0), (-29.0, -8.0), (-30.5, 4.5)],
}
LANE_AREA = {"west": "west", "east": "east", "north": "north", "grove": "grove", "loop": "grove"}
LANE_WIDTH = 1.1


class _Built(dict):
    """A live view of the built areas' clearings or lanes (follows BUILT)."""

    def __init__(self, source, area_of):
        super().__init__()
        self.source, self.area_of = source, area_of

    def _live(self):
        return {k: v for k, v in self.source.items() if self.area_of(k) in BUILT}

    def items(self):
        return self._live().items()

    def values(self):
        return self._live().values()

    def keys(self):
        return self._live().keys()

    def __iter__(self):
        return iter(self._live())


LANES = _Built(ALL_LANES, lambda k: LANE_AREA[k])


class _Clearings:
    def __iter__(self):
        return iter([AREAS[k]["clearing"] for k in AREAS if k in BUILT])


CLEARINGS = _Clearings()


def _seg_distance(x, y, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - ax - t * dx, y - ay - t * dy)


def lane_distance(x, y):
    """Distance to the nearest side lane's centre line."""
    best = math.inf
    for pts in LANES.values():
        for a, b in zip(pts, pts[1:]):
            best = min(best, _seg_distance(x, y, a, b))
    return best


def ellipse_value(x, y, e, grow=0.0):
    """< 1 inside the ellipse (cx, cy, rx, ry, turn) grown by `grow` metres."""
    cx, cy, rx, ry, turn = e
    c, s = math.cos(-turn), math.sin(-turn)
    u, v = (x - cx) * c - (y - cy) * s, (x - cx) * s + (y - cy) * c
    return (u / (rx + grow)) ** 2 + (v / (ry + grow)) ** 2


def in_clearing(x, y, grow=0.0):
    return any(ellipse_value(x, y, e, grow) < 1 for e in CLEARINGS)


def in_pond(x, y, grow=0.0):
    return "east" in BUILT and ellipse_value(x, y, EAST_POND["water"], grow) < 1


def in_new_ground(x, y):
    """Ground that did not exist before the expansion."""
    o = OLD_TERRAIN
    return not (o["x0"] <= x <= o["x1"] and o["y0"] <= y <= o["y1"])


def open_ground(x, y, margin=0.0):
    """Kept free of forest: the new clearings and lanes (with a margin)."""
    return in_clearing(x, y, margin) or lane_distance(x, y) < LANE_WIDTH / 2 + 0.9 + margin
