"""The game's mud-and-litter ground mask (src/episodes/ep1/data/pathGround.ts),
ported so Blender previews show the ground as the game draws it: a soft, ragged
mix of trodden mud and leaf litter instead of the terrain's 1 m material steps.
Babylon space (x = -Blender x, z = -Blender y). Plain Python; keep in step with
pathGround.ts.
"""
import math

import village_layout as L

PATH = [(-1.5, 60), (-2.5, 50), (-0.5, 40), (2.5, 30), (2, 20), (-0.5, 10), (0, 3)]
YARD = (-13, 13, -32, 3)  # minX, maxX, minZ, maxZ
ROAD_Z = 63.5


def _fract(v):
    return v - math.floor(v)


def _hash(x, z):
    return _fract(math.sin(x * 127.1 + z * 311.7) * 43758.5453)


def _value_noise(x, z):
    ix, iz = math.floor(x), math.floor(z)
    fx, fz = x - ix, z - iz
    ux, uz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    a, b = _hash(ix, iz), _hash(ix + 1, iz)
    c, d = _hash(ix, iz + 1), _hash(ix + 1, iz + 1)
    return a + (b - a) * ux + (c - a) * uz + (a - b - c + d) * ux * uz


def fbm(x, z):
    return (_value_noise(x, z) * 0.55 + _value_noise(x * 2.1 + 17, z * 2.1 - 9) * 0.3
            + _value_noise(x * 4.3 - 5, z * 4.3 + 31) * 0.15)


def _smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _seg(x, z, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / (dx * dx + dz * dz)))
    return math.hypot(x - a[0] - t * dx, z - a[1] - t * dz)


def path_distance(x, z):
    return min(_seg(x, z, a, b) for a, b in zip(PATH, PATH[1:]))


def _outside_yard(x, z):
    x0, x1, z0, z1 = YARD
    dx = max(x0 - x, x - x1)
    dz = max(z0 - z, z - z1)
    if dx <= 0 and dz <= 0:
        return max(dx, dz)
    return math.hypot(max(dx, 0), max(dz, 0))


def ground_mix(x, z):
    """(mud, wet) at Babylon (x, z), as groundMix in pathGround.ts."""
    wobble = fbm(x * 0.45, z * 0.45)
    grain = fbm(x * 1.6 + 40, z * 1.6 - 12)
    d = path_distance(x, z)
    edge = 0.95 + 0.75 * wobble + 0.25 * (grain - 0.5)
    path = 1 - _smooth(edge - 0.45, edge + 0.4, d)
    drift = _smooth(0.58, 0.78, fbm(x * 0.9 - 7, z * 0.9 + 3))
    path *= 1 - drift * (0.35 + 0.5 * _smooth(0.2, 1.1, d))
    yard = 1 - _smooth(-0.6, 0.9, _outside_yard(x, z) - 0.5 + 1.2 * (wobble - 0.5))
    road = _smooth(59.6, 61.2, z + 1.6 * (wobble - 0.5))
    lane_edge = 0.55 + 0.45 * wobble + 0.2 * (grain - 0.5)
    side_lane = (1 - _smooth(lane_edge - 0.35, lane_edge + 0.3, L.lane_distance(-x, -z))) * (1 - drift * 0.5)
    bank = pond_bank(x, z, wobble, grain)
    mud = max(path, yard, road, side_lane * 0.9, bank)
    lane = 1 - abs(d - 0.32) / 0.22 if abs(d - 0.32) < 0.22 else 0
    rut = max(0, 1 - abs(abs(z - ROAD_Z) - 0.8) / 0.35) * road
    wet = min(1, (lane * 0.6 + rut + 0.35 * _smooth(0.55, 0.85, grain)) * mud)
    return mud, max(wet, bank * 0.8)


def pond_bank(x, z, wobble, grain):
    """The pond's trodden, wet bank: a ragged ring of mud at the shore."""
    if "east" not in L.BUILT:
        return 0.0
    r = math.sqrt(L.ellipse_value(-x, -z, L.EAST_POND["water"]))
    edge = 1.14 + 0.12 * (wobble - 0.5) + 0.06 * (grain - 0.5)
    return 1 - _smooth(edge - 0.05, edge + 0.07, r)
