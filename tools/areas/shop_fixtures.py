"""Furniture and the larger things in the village road's shops (shop_interiors.py places them):
shelving, counters and benches; a barber's hydraulic chair, a dentist's chair; a step-through
motorbike; the noodle seller's cart; a treadle sewing machine, a dress form and a hood dryer;
a box television showing snow, a cassette radio, a desk fan, wall clocks, a pan balance, oil
drums, tyres and soda crates. All in a Kit (shop_goods.py), local frames, metres.
"""
import math

import numpy as np
from mathutils import Matrix, Vector

from shop_goods import (T, band, bottle, boxm, curved_sheet, cylm, extrude_outline, lathe, noodle_nest, quad, sphere,
                        torus, tube, wrap_rect)

WOOD = "shop_dark_wood"


# ------------------------------------------------------------------ furniture

def shelf_unit(K, M, w=1.3, h=1.9, d=0.38, tiers=5, wood=WOOD, back=True):
    """Free-standing plank shelving against a wall (its back at local x 0, front +x): four
    square uprights, planks with a front lip, a slatted back. Returns the shelves' top z."""
    for x in (0.02, d - 0.02):
        for y in (-w / 2 + 0.02, w / 2 - 0.02):
            boxm(K[wood], M, (x, y, h / 2), (0.04, 0.04, h), bevel=0.004)
    tops = []
    for k in range(tiers):
        z = 0.12 + k * (h - 0.2) / max(1, tiers - 1)
        boxm(K[wood], M, (d / 2, 0, z - 0.011), (d, w, 0.022), bevel=0.003)
        boxm(K[wood], M, (d - 0.008, 0, z + 0.008), (0.016, w - 0.06, 0.03), bevel=0.003)
        tops.append(z)
    if back:
        for k in range(int(w / 0.14)):
            y = -w / 2 + 0.07 + k * 0.14
            boxm(K[wood], M, (0.006, y, h / 2), (0.012, 0.12, h - 0.06), bevel=0.002)
    return tops


def wall_shelf(K, M, w=1.2, d=0.22, wood=WOOD):
    """A plank on two iron brackets (its back at local x 0). Returns its top z (local)."""
    boxm(K[wood], M, (d / 2, 0, 0), (d, w, 0.024), bevel=0.003)
    for y in (-w / 2 + 0.12, w / 2 - 0.12):
        extrude_outline(K["shop_iron"], M @ T(0, y, -0.012, tilt=(math.pi / 2, 0)),
                        [(0.0, 0.0), (d * 0.85, 0.0), (d * 0.85, -0.012), (0.012, -0.16), (0.0, -0.16)], 0.008)
    return 0.012


def counter(K, M, w=1.6, d=0.55, h=0.92, glass_top=True, wood=WOOD):
    """A shop counter (its back at local x 0, customer side +x): a framed cabinet, plank front,
    a glass display top with goods under it. Returns (top z, display floor z)."""
    for x in (0.02, d - 0.02):
        for y in (-w / 2 + 0.02, w / 2 - 0.02):
            boxm(K[wood], M, (x, y, h / 2), (0.045, 0.045, h), bevel=0.004)
    for k in range(int(w / 0.12)):
        y = -w / 2 + 0.06 + k * (w - 0.12) / max(1, int(w / 0.12) - 1)
        boxm(K[wood], M, (d - 0.01, y, h * 0.38), (0.018, 0.115, h * 0.7), bevel=0.003)
    boxm(K[wood], M, (d / 2, 0, 0.06), (d, w, 0.03))
    floor = h - 0.16
    boxm(K[wood], M, (d / 2, 0, floor), (d - 0.05, w - 0.05, 0.02))
    boxm(K[wood], M, (d / 2, 0, h - 0.17), (d + 0.02, w + 0.02, 0.03), bevel=0.004)
    if glass_top:
        for x in (0.0, d):
            boxm(K[wood], M, (x, 0, h - 0.01), (0.03, w + 0.02, 0.03), bevel=0.003)
        for y in (-w / 2, w / 2):
            boxm(K[wood], M, (d / 2, y, h - 0.01), (d + 0.02, 0.03, 0.03), bevel=0.003)
        boxm(K["glass"], M, (d / 2, 0, h + 0.003), (d, w, 0.006))
        boxm(K["glass"], M, (d - 0.008, 0, h - 0.08), (0.006, w - 0.04, 0.13))
    else:
        boxm(K[wood], M, (d / 2, 0, h), (d + 0.04, w + 0.04, 0.035), bevel=0.005)
    return h + (0.006 if glass_top else 0.018), floor + 0.01


def bench(K, M, w=1.5, d=0.34, h=0.45, wood=WOOD):
    boxm(K[wood], M, (0, 0, h - 0.02), (d, w, 0.04), bevel=0.006)
    for y in (-w / 2 + 0.12, w / 2 - 0.12):
        for x in (-d / 2 + 0.05, d / 2 - 0.05):
            boxm(K[wood], M, (x, y, (h - 0.04) / 2), (0.045, 0.045, h - 0.04), bevel=0.004)
        boxm(K[wood], M, (0, y, 0.14), (d - 0.06, 0.03, 0.03))
    boxm(K[wood], M, (0, 0, 0.14), (0.03, w - 0.24, 0.03))


def stool(K, M, key="plastic_red"):
    """A moulded plastic stool, the low kind every roadside shop stacks."""
    lathe(K[key], [(0.0, 0.42), (0.14, 0.42), (0.155, 0.415), (0.155, 0.395), (0.13, 0.39), (0.13, 0.36)], M, segs=24)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        cylm(K[key], M, (math.cos(a) * 0.1, math.sin(a) * 0.1, 0.38), (math.cos(a) * 0.16, math.sin(a) * 0.16, 0.0),
             0.022, 0.018, segs=8)
    torus(K[key], M, (0, 0, 0.14), (0, 0, 1), 0.13, 0.008, n=20, m=5)


def mat_roll(K, M, length=0.9, r=0.07, key="shop_kantel"):
    cylm(K[key], M, (0, -length / 2, r), (0, length / 2, r), r, segs=16)
    for y in (-length / 3, length / 3):
        torus(K["thread_red"], M, (0, y, r), (0, 1, 0), r + 0.002, 0.004, n=16, m=4)


# ------------------------------------------------------------------ chairs

def barber_chair(K, M, leather="leather_red"):
    """A hydraulic barber's chair facing local +x: its round foot and pump, a tufted seat and
    back, white enamel arms with leather pads, a headrest on its rod, a chrome footrest."""
    lathe(K["porcelain"], [(0.0, 0.0), (0.29, 0.0), (0.3, 0.012), (0.27, 0.04), (0.12, 0.07), (0.075, 0.09), (0.0, 0.09)], M,
          segs=32)
    lathe(K["chrome"], [(0.06, 0.09), (0.062, 0.12), (0.05, 0.13), (0.05, 0.4), (0.07, 0.43), (0.07, 0.46), (0.0, 0.47)], M,
          segs=20)
    cylm(K["chrome"], M, (0.0, 0.04, 0.2), (-0.05, 0.3, 0.32), 0.012, segs=8)
    boxm(K["chrome"], M, (-0.05, 0.31, 0.33), (0.07, 0.04, 0.02), bevel=0.006)
    # The seat: a box of enamel with the cushion on it, piped round its edge.
    boxm(K["porcelain"], M, (0, 0, 0.5), (0.5, 0.5, 0.07), bevel=0.025, segs=3)
    boxm(K[leather], M, (0.01, 0, 0.58), (0.48, 0.46, 0.1), bevel=0.045, segs=4)
    torus(K[leather], M @ Matrix.Diagonal((1.0, 0.96, 1.0, 1.0)), (0.01, 0, 0.6), (0, 0, 1), 0.235, 0.012, n=28, m=6)
    # The back, raked, tufted with buttons, and its enamel shell behind.
    B = M @ T(-0.25, 0, 0.6, tilt=(0, -0.24))
    boxm(K[leather], B, (0.04, 0, 0.34), (0.1, 0.46, 0.66), bevel=0.045, segs=4)
    boxm(K["porcelain"], B, (-0.02, 0, 0.32), (0.04, 0.48, 0.64), bevel=0.015)
    for i in range(3):
        for j in range(3):
            sphere(K[leather], B, (0.092, -0.13 + j * 0.13, 0.16 + i * 0.16), 0.009, 8, 5)
    # The headrest on its chrome rod.
    cylm(K["chrome"], B, (0.0, 0, 0.62), (0.03, 0, 0.84), 0.012, segs=8)
    boxm(K[leather], B, (0.06, 0, 0.86), (0.08, 0.26, 0.11), bevel=0.035, segs=4)
    # The arms: enamel, a leather pad, a chrome front scroll.
    for y in (-0.27, 0.27):
        boxm(K["porcelain"], M, (0.03, y, 0.73), (0.5, 0.05, 0.05), bevel=0.012)
        boxm(K[leather], M, (0.02, y, 0.765), (0.42, 0.065, 0.03), bevel=0.013, segs=3)
        cylm(K["chrome"], M, (0.21, y * 0.94, 0.47), (0.25, y, 0.74), 0.016, segs=10)
        boxm(K["porcelain"], M, (-0.18, y * 0.95, 0.6), (0.06, 0.05, 0.26), bevel=0.01)
    # The footrest: a bracket and a ribbed chrome plate.
    cylm(K["chrome"], M, (0.24, 0, 0.47), (0.42, 0, 0.26), 0.018, segs=10)
    boxm(K["chrome"], M, (0.46, 0, 0.255), (0.12, 0.34, 0.016), bevel=0.004)
    for k in range(6):
        boxm(K["rubber"], M, (0.42 + k * 0.016, 0, 0.266), (0.006, 0.32, 0.006))


def salon_chair(K, M):
    barber_chair(K, M, leather="vinyl_cream")


def dental_chair(K, M):
    """An old dentist's chair facing local +x, raked back: cast-iron foot, cream upholstery,
    a headrest, a spittoon bowl on its arm, the lamp on its jointed arm."""
    lathe(K["cast_iron"], [(0.0, 0.0), (0.32, 0.0), (0.33, 0.02), (0.18, 0.06), (0.09, 0.1), (0.08, 0.38), (0.0, 0.38)], M,
          segs=28)
    boxm(K["porcelain"], M, (0, 0, 0.42), (0.5, 0.48, 0.08), bevel=0.02)
    boxm(K["vinyl_cream"], M, (0.03, 0, 0.5), (0.52, 0.46, 0.09), bevel=0.04, segs=4)
    B = M @ T(-0.24, 0, 0.5, tilt=(0, -0.5))
    boxm(K["vinyl_cream"], B, (0.04, 0, 0.34), (0.09, 0.44, 0.66), bevel=0.04, segs=4)
    boxm(K["porcelain"], B, (-0.015, 0, 0.32), (0.035, 0.46, 0.64), bevel=0.012)
    cylm(K["chrome"], B, (0.0, 0, 0.62), (0.03, 0, 0.82), 0.012, segs=8)
    boxm(K["vinyl_cream"], B, (0.06, 0, 0.84), (0.08, 0.24, 0.12), bevel=0.03)
    boxm(K["vinyl_cream"], M, (0.42, 0, 0.36), (0.36, 0.4, 0.07), bevel=0.025)
    for y in (-0.26, 0.26):
        boxm(K["vinyl_cream"], M, (0.02, y * 0.96, 0.66), (0.44, 0.06, 0.04), bevel=0.015)
        cylm(K["chrome"], M, (0.2, y * 0.9, 0.45), (0.2, y * 0.9, 0.65), 0.014, segs=8)
    # The spittoon on its swing arm, a glass for rinsing beside it.
    cylm(K["chrome"], M, (0.0, -0.22, 0.42), (0.1, -0.46, 0.8), 0.014, segs=8)
    from shop_goods import bowl, tumbler
    bowl(K, M @ T(0.12, -0.5, 0.8), 0.11, 0.07, key="porcelain")
    tumbler(K, M @ T(0.22, -0.42, 0.8), r=0.028, h=0.09, liquid="water")
    # The lamp: a jointed arm from a pole behind the chair, the reflector over the mouth.
    cylm(K["cast_iron"], M, (-0.45, 0.32, 0.0), (-0.45, 0.32, 1.55), 0.02, segs=10)
    cylm(K["chrome"], M, (-0.45, 0.32, 1.5), (-0.05, 0.18, 1.6), 0.012, segs=8)
    cylm(K["chrome"], M, (-0.05, 0.18, 1.6), (0.18, 0.05, 1.42), 0.011, segs=8)
    lathe(K["porcelain"], [(0.0, 0.0), (0.05, 0.005), (0.09, 0.04), (0.095, 0.05)], M @ T(0.2, 0.04, 1.42, tilt=(0, 2.4)),
          segs=18, cap_bottom=False)
    sphere(K["shop_bulb"], M @ T(0.2, 0.04, 1.42, tilt=(0, 2.4)), (0, 0, 0.03), 0.02, 10, 6)


# ------------------------------------------------------------------ the motorbike

def _wheel(K, M, r_tyre=0.29, width=0.07, spokes=36):
    """A spoked wheel in local x-z, axle along y."""
    torus(K["tyre"], M, (0, 0, 0), (0, 1, 0), r_tyre - width * 0.5, width * 0.5, n=40, m=10)
    for k in range(40):
        a = k / 40 * math.tau
        p = Vector((math.cos(a), 0, math.sin(a)))
        boxm(K["tyre"], M @ Matrix.Translation(p * (r_tyre - 0.004)) @ Matrix.Rotation(-a, 4, "Y"), (0, 0, 0),
             (0.012, width * 0.9, 0.016))
    rim = r_tyre - width * 0.95
    torus(K["chrome"], M, (0, 0, 0), (0, 1, 0), rim, 0.01, n=36, m=6)
    cylm(K["chrome"], M, (0, -0.06, 0), (0, 0.06, 0), 0.055, segs=16)
    for side in (-1, 1):
        lathe(K["steel"], [(0.0, 0.0), (0.085, 0.0), (0.085, 0.012), (0.0, 0.012)], M @ T(0, side * 0.06, 0, tilt=(-side * math.pi / 2, 0)),
              segs=18)
    for k in range(spokes):
        a = k / spokes * math.tau
        side = 1 if k % 2 else -1
        hub = Vector((math.cos(a + 0.3 * side) * 0.04, side * 0.045, math.sin(a + 0.3 * side) * 0.04))
        tip = Vector((math.cos(a) * (rim - 0.005), 0, math.sin(a) * (rim - 0.005)))
        cylm(K["steel"], M, hub, tip, 0.0018, segs=4, cap=False)


def motorbike(K, M, paint="plastic_blue"):
    """A step-through 100 cc motorbike, the kind every Cambodian road is full of, on its centre
    stand: spoked wheels, telescopic fork, leg shield, horizontal engine with finned cylinder,
    exhaust and muffler, the long black seat, rear rack, headlamp, mirrors, number plate."""
    rw, fw = Vector((-0.6, 0, 0.29)), Vector((0.62, 0, 0.29))
    _wheel(K, M @ Matrix.Translation(rw))
    _wheel(K, M @ Matrix.Translation(fw))
    head = Vector((0.47, 0, 0.9))
    # The fork: two chrome legs, their black covers, the steering stem.
    for y in (-0.07, 0.07):
        cylm(K["chrome"], M, fw + Vector((0, y, 0)), head + Vector((0, y, -0.12)), 0.016, segs=10)
        cylm(K["black_paint"], M, fw + Vector((-0.04, y, 0.18)), head + Vector((-0.01, y, -0.14)), 0.022, segs=10)
    cylm(K[paint], M, head + Vector((0, 0, -0.14)), head + Vector((0.02, 0, 0.12)), 0.04, segs=12)
    boxm(K["cast_iron"], M, head + Vector((0.0, 0, -0.12)), (0.07, 0.2, 0.035), bevel=0.01)
    # The front mudguard, curving over the front tyre.
    curved_sheet(K[paint], M, fw, 0.33, 0.25, 2.55, 0.11)
    # The backbone, from the head down under the step and up to the tail.
    tube(K[paint], M, [head + Vector((-0.02, 0, -0.06)), Vector((0.32, 0, 0.62)), Vector((0.12, 0, 0.42)),
                       Vector((-0.08, 0, 0.42)), Vector((-0.3, 0, 0.6)), Vector((-0.7, 0, 0.72))], 0.03, segs=12)
    # The leg shield: a curved panel in front of the rider's legs, and the floor step.
    for off, flip in ((0.0, False), (-0.008, True)):
        rows = []
        for z in np.linspace(0.36, 0.9, 8):
            row = []
            t = (z - 0.36) / 0.54
            half = 0.13 + 0.07 * math.sin(math.pi * min(1.0, t * 1.15) * 0.5)
            for y in np.linspace(-1.0, 1.0, 9):
                x = 0.31 + off - 0.11 * y * y + 0.07 * t - 0.03 * math.sin(math.pi * t)
                row.append(K[paint].verts.new(M @ Vector((x, y * half, z))))
            rows.append(row)
        for a, b in zip(rows, rows[1:]):
            for k in range(len(a) - 1):
                q = (a[k], a[k + 1], b[k + 1], b[k])
                K[paint].faces.new(tuple(reversed(q)) if flip else q)
    boxm(K["rubber"], M, (0.12, 0, 0.44), (0.3, 0.32, 0.02), bevel=0.006)
    # The engine: crankcase, the finned cylinder lying forward, carburettor, kick-start.
    boxm(K["steel"], M, (0.02, 0, 0.3), (0.3, 0.22, 0.2), bevel=0.05)
    lathe(K["steel"], [(0.0, 0.0), (0.07, 0.0), (0.07, 0.06), (0.0, 0.06)], M @ T(0.15, 0, 0.3, tilt=(0, math.pi / 2 - 0.2)),
          segs=16)
    for k in range(8):
        lathe(K["cast_iron"], [(0.05, 0.0), (0.085, 0.0), (0.085, 0.006), (0.05, 0.006)],
              M @ T(0.17 + k * 0.016, 0, 0.3 + k * 0.003, tilt=(0, math.pi / 2 - 0.2)), segs=16, cap_bottom=False)
    boxm(K["cast_iron"], M, (0.33, 0, 0.33), (0.06, 0.1, 0.09), bevel=0.015)
    lathe(K["steel"], [(0.0, 0.0), (0.03, 0.0), (0.03, 0.05), (0.0, 0.05)], M @ T(0.0, 0.1, 0.42), segs=12)
    cylm(K["steel"], M, (-0.08, -0.13, 0.32), (-0.2, -0.16, 0.18), 0.012, segs=8)
    # The exhaust: the pipe from the head down the right side to a long muffler.
    tube(K["chrome"], M, [Vector((0.36, -0.05, 0.3)), Vector((0.36, -0.11, 0.2)), Vector((0.2, -0.15, 0.17)),
                          Vector((-0.2, -0.16, 0.2))], 0.02, segs=10)
    lathe(K["chrome"], [(0.0, 0.0), (0.035, 0.01), (0.045, 0.06), (0.045, 0.42), (0.03, 0.46), (0.014, 0.5), (0.0, 0.5)],
          M @ T(-0.2, -0.16, 0.2, tilt=(0, -math.pi / 2 + 0.08)), segs=16)
    boxm(K["steel"], M, (-0.45, -0.17, 0.25), (0.22, 0.012, 0.08), bevel=0.006)
    # The rear: swing arm, chain guard, two shocks, mudguard, side covers.
    for y in (-0.07, 0.07):
        cylm(K["black_paint"], M, rw + Vector((0, y, 0)), Vector((-0.02, y, 0.34)), 0.016, segs=8)
        cylm(K["chrome"], M, rw + Vector((0.02, y * 1.4, 0.04)), Vector((-0.48, y * 1.6, 0.68)), 0.02, segs=10)
        for k in range(9):
            t = 0.15 + k * 0.08
            p = (rw + Vector((0.02, y * 1.4, 0.04))).lerp(Vector((-0.48, y * 1.6, 0.68)), t)
            torus(K["chrome"], M, p, (0.12, 0, 1), 0.026, 0.004, n=12, m=4)
    boxm(K["black_paint"], M, (-0.3, 0.08, 0.32), (0.56, 0.02, 0.09), bevel=0.02)
    curved_sheet(K[paint], M, rw, 0.335, 0.55, 2.45, 0.13)
    for side in (-1, 1):
        boxm(K[paint], M, (-0.3, side * 0.12, 0.6), (0.4, 0.02, 0.16), bevel=0.03)
    # The seat, its chrome trim strap; the rear rack, the tail lamp and the number plate.
    boxm(K["leather_black"], M, (-0.3, 0, 0.78), (0.62, 0.25, 0.09), bevel=0.04, segs=4)
    boxm(K["chrome"], M, (-0.3, 0, 0.83), (0.02, 0.26, 0.008))
    for y in (-0.1, 0.1):
        tube(K["chrome"], M, [Vector((-0.58, y, 0.76)), Vector((-0.66, y, 0.8)), Vector((-0.92, y, 0.8))], 0.009, segs=6)
    for x in (-0.7, -0.8, -0.9):
        cylm(K["chrome"], M, (x, -0.1, 0.8), (x, 0.1, 0.8), 0.006, segs=6)
    boxm(K["black_paint"], M, (-0.905, 0, 0.67), (0.012, 0.05, 0.27))
    lathe(K["plastic_red"], [(0.0, 0.0), (0.04, 0.0), (0.045, 0.02), (0.0, 0.03)], M @ T(-0.911, 0, 0.74, tilt=(0, -math.pi / 2)),
          segs=12)
    boxm(K["plastic_white"], M, (-0.914, 0, 0.6), (0.006, 0.16, 0.1))
    # The handlebar: bar, grips, levers, the headlamp housing, the speedometer, two mirrors.
    bar = head + Vector((0.0, 0, 0.17))
    cylm(K["chrome"], M, bar + Vector((-0.04, -0.32, 0.02)), bar + Vector((-0.04, 0.32, 0.02)), 0.011, segs=8)
    for y in (-1, 1):
        cylm(K["rubber"], M, bar + Vector((-0.045, y * 0.24, 0.02)), bar + Vector((-0.05, y * 0.35, 0.02)), 0.017, segs=10)
        cylm(K["chrome"], M, bar + Vector((0.0, y * 0.2, 0.03)), bar + Vector((-0.08, y * 0.3, 0.03)), 0.006, segs=6)
        cylm(K["chrome"], M, bar + Vector((-0.03, y * 0.22, 0.02)), bar + Vector((-0.06, y * 0.25, 0.34)), 0.005, segs=6)
        lathe(K["chrome"], [(0.0, -0.004), (0.04, -0.004), (0.045, 0.006), (0.0, 0.01)],
              M @ T(bar.x - 0.06, y * 0.25, bar.z + 0.36, tilt=(0, -math.pi / 2)), segs=14)
        lathe(K["glass"], [(0.0, 0.0105), (0.038, 0.0105), (0.0, 0.0115)],
              M @ T(bar.x - 0.06, y * 0.25, bar.z + 0.36, tilt=(0, -math.pi / 2)), segs=14, cap_bottom=False)
    boxm(K[paint], M, bar + Vector((0.02, 0, -0.02)), (0.16, 0.3, 0.12), bevel=0.04)
    lathe(K["chrome"], [(0.0, 0.0), (0.07, 0.0), (0.075, 0.03), (0.07, 0.07), (0.0, 0.075)],
          M @ T(bar.x + 0.08, 0, bar.z - 0.04, tilt=(0, math.pi / 2)), segs=20)
    lathe(K["glass"], [(0.0, 0.07), (0.066, 0.072), (0.0, 0.09)], M @ T(bar.x + 0.08, 0, bar.z - 0.04, tilt=(0, math.pi / 2)),
          segs=20, cap_bottom=False)
    lathe(K["plastic_white"], [(0.0, 0.0), (0.035, 0.0), (0.035, 0.006), (0.0, 0.006)],
          M @ T(bar.x - 0.02, 0, bar.z + 0.045, tilt=(0, -0.5)), segs=16)
    # The centre stand down, the kick-start, the footpegs.
    for y in (-0.09, 0.09):
        cylm(K["black_paint"], M, (-0.05, y, 0.3), (-0.12, y * 1.4, 0.0), 0.012, segs=6)
    cylm(K["black_paint"], M, (-0.12, -0.13, 0.0), (-0.12, 0.13, 0.0), 0.01, segs=6)
    cylm(K["steel"], M, (-0.12, 0, 0.3), (-0.18, 0, 0.3), 0.015, segs=8)
    cylm(K["steel"], M, (-0.18, -0.14, 0.3), (-0.18, 0.14, 0.3), 0.011, segs=8)
    for y in (-0.22, 0.22):
        cylm(K["rubber"], M, (-0.18, y * 0.6, 0.3), (-0.18, y, 0.3), 0.013, segs=8)


# ------------------------------------------------------------------ the noodle cart

def noodle_cart(K, M, paint="plastic_blue"):
    """The kuy teav seller's cart (front +x, the road): a timber cabinet painted blue with tin
    corners on two bicycle wheels; on it the glass case of noodles and hanging pork, the
    cauldron of broth on its burner, bowls, ladle, the condiments; the push bar behind."""
    from shop_goods import bowl_stack, chopsticks, jar, tin

    w, d, h = 1.5, 0.62, 0.84
    boxm(K[paint], M, (0, 0, h / 2 + 0.1), (d, w, h - 0.2), bevel=0.012)
    for y in np.linspace(-w / 2 + 0.05, w / 2 - 0.05, 9):
        boxm(K[WOOD], M, (d / 2 + 0.004, y, h / 2 + 0.1), (0.012, 0.02, h - 0.24))
    for y in (-w / 2, w / 2):
        for x in (-d / 2, d / 2):
            boxm(K["tinplate"], M, (x, y, h / 2 + 0.1), (0.03, 0.03, h - 0.18))
    boxm(K["tinplate"], M, (0, 0, h), (d + 0.04, w + 0.04, 0.03), bevel=0.006)
    for y in (-w / 2 + 0.08, w / 2 - 0.08):
        _wheel(K, M @ T(-0.06, y * 1.08, 0.24, s=0.82))
    for y in (-w / 2 + 0.06, w / 2 - 0.06):
        cylm(K["steel"], M, (d / 2 - 0.05, y, 0.2), (d / 2 - 0.05, y, 0.0), 0.014, segs=8)
        cylm(K["steel"], M, (-d / 2, y, h - 0.04), (-d / 2 - 0.32, y, h + 0.08), 0.014, segs=8)
    cylm(K["rubber"], M, (-d / 2 - 0.32, -w / 2 + 0.06, h + 0.08), (-d / 2 - 0.32, w / 2 - 0.06, h + 0.08), 0.017, segs=10)
    # The glass case on the left half: frame, panes, a shelf of noodle nests, pork on hooks.
    cx, cy, cw, cd, ch = 0.02, -0.33, 0.7, 0.52, 0.62
    z0 = h + 0.016
    for x in (cx - cd / 2, cx + cd / 2):
        for y in (cy - cw / 2, cy + cw / 2):
            boxm(K["tinplate"], M, (x, y, z0 + ch / 2), (0.022, 0.022, ch))
    for z in (z0 + 0.01, z0 + ch):
        boxm(K["tinplate"], M, (cx, cy - cw / 2, z), (cd, 0.022, 0.02))
        boxm(K["tinplate"], M, (cx, cy + cw / 2, z), (cd, 0.022, 0.02))
        boxm(K["tinplate"], M, (cx + cd / 2, cy, z), (0.022, cw, 0.02))
        boxm(K["tinplate"], M, (cx - cd / 2, cy, z), (0.022, cw, 0.02))
    for (px, py, sx, sy) in ((cx + cd / 2, cy, 0.005, cw), (cx - cd / 2, cy, 0.005, cw), (cx, cy - cw / 2, cd, 0.005),
                             (cx, cy + cw / 2, cd, 0.005)):
        boxm(K["glass"], M, (px, py, z0 + ch / 2), (sx, sy, ch - 0.02))
    boxm(K["glass"], M, (cx, cy, z0 + ch + 0.004), (cd, cw, 0.005))
    boxm(K["tinplate"], M, (cx, cy, z0 + 0.22), (cd - 0.03, cw - 0.03, 0.01))
    rng = np.random.default_rng(31)
    for i in range(3):
        for j in range(4):
            px = cx - cd / 2 + 0.1 + i * (cd - 0.2) / 2
            py = cy - cw / 2 + 0.1 + j * (cw - 0.2) / 3
            noodle_nest(K, M @ T(px + rng.normal(0, 0.005), py + rng.normal(0, 0.005), z0 + 0.012), seed=i * 7 + j)
            noodle_nest(K, M @ T(px, py, z0 + 0.232), key="rice_noodles", seed=50 + i * 7 + j)
    cylm(K["steel"], M, (cx, cy - cw / 2, z0 + ch - 0.04), (cx, cy + cw / 2, z0 + ch - 0.04), 0.004, segs=6)
    for k in range(4):
        py = cy - cw / 2 + 0.12 + k * 0.15
        tube(K["steel"], M, [(cx, py, z0 + ch - 0.04), (cx, py, z0 + ch - 0.1), (cx + 0.015, py, z0 + ch - 0.12)], 0.0025, segs=4)
        sl = rng.uniform(1.2, 1.7)
        sphere(K["meat"], M, (cx + 0.015, py, z0 + ch - 0.112 - 0.05 * sl), 0.05, 14, 9, scale=(rng.uniform(0.55, 0.8), 0.42, sl))
    # The cauldron of broth over its burner on the right half, lid ajar, the ladle in it.
    bx, by = -0.02, 0.38
    lathe(K["cast_iron"], [(0.0, 0.0), (0.2, 0.0), (0.2, 0.16), (0.18, 0.17), (0.0, 0.17)], M @ T(bx, by, z0), segs=20)
    lathe(K["steel"], [(0.0, 0.0), (0.19, 0.0), (0.21, 0.02), (0.22, 0.3), (0.235, 0.31), (0.23, 0.32), (0.21, 0.31),
                       (0.2, 0.04), (0.0, 0.03)], M @ T(bx, by, z0 + 0.17), segs=24, cap_bottom=True)
    lathe(K["soy"], [(0.0, 0.25), (0.205, 0.25), (0.0, 0.252)], M @ T(bx, by, z0 + 0.17), segs=20, cap_bottom=False)
    lathe(K["steel"], [(0.0, 0.03), (0.21, 0.0), (0.225, 0.004), (0.0, 0.05)], M @ T(bx + 0.05, by + 0.04, z0 + 0.49, tilt=(0.25, 0)),
          segs=24)
    cylm(K["steel"], M, (bx - 0.1, by - 0.05, z0 + 0.2), (bx - 0.16, by - 0.1, z0 + 0.6), 0.006, segs=6)
    lathe(K["steel"], [(0.0, 0.0), (0.04, 0.005), (0.045, 0.03)], M @ T(bx - 0.08, by - 0.04, z0 + 0.38), segs=14, cap_bottom=False)
    # Bowls stacked, chopsticks and spoons, the condiment jars at the front edge.
    bowl_stack(K, M @ T(0.18, 0.06, z0), 6)
    bowl_stack(K, M @ T(0.18, 0.22, z0), 5)
    chopsticks(K, M @ T(0.24, -0.72, z0))
    jar(K, M @ T(0.26, 0.62, z0), 0.04, 0.1, label="chili", contents="chili")
    bottle(K, M @ T(0.26, 0.72, z0), "sauce", label="fish_sauce")
    bottle(K, M @ T(0.17, 0.72, z0), "sauce", liquid="soy", label="soy_sauce")
    tin(K, M @ T(0.12, 0.6, z0), 0.035, 0.08, label="palm_sugar", open_top=True)


# ------------------------------------------------------------------ the tailor's and salon's

def sewing_machine(K, M):
    """A treadle sewing machine (front +x): cast-iron legs with the treadle and band wheel, a
    wooden top with a drawer, the black machine head, its balance wheel and a spool."""
    for y in (-0.36, 0.36):
        pts = [(-0.18, y, 0.0), (-0.12, y, 0.25), (-0.18, y, 0.72)]
        tube(K["cast_iron"], M, pts, 0.016, segs=8)
        tube(K["cast_iron"], M, [(0.18, y, 0.0), (0.12, y, 0.25), (0.18, y, 0.72)], 0.016, segs=8)
        cylm(K["cast_iron"], M, (-0.18, y, 0.3), (0.18, y, 0.3), 0.012, segs=6)
        cylm(K["cast_iron"], M, (0.0, y, 0.12), (0.0, y, 0.72), 0.011, segs=6)
        cylm(K["cast_iron"], M, (-0.15, y, 0.31), (0.15, y, 0.7), 0.008, segs=5)
        cylm(K["cast_iron"], M, (0.15, y, 0.31), (-0.15, y, 0.7), 0.008, segs=5)
        cylm(K["cast_iron"], M, (-0.18, y, 0.72), (0.18, y, 0.72), 0.012, segs=6)
    cylm(K["cast_iron"], M, (0, -0.36, 0.12), (0, 0.36, 0.12), 0.012, segs=6)
    boxm(K["cast_iron"], M, (0.04, 0, 0.12), (0.3, 0.5, 0.012), bevel=0.004)
    torus(K["cast_iron"], M, (0, 0.3, 0.38), (0, 1, 0), 0.16, 0.012, n=24, m=5)
    cylm(K["steel"], M, (0, 0.28, 0.38), (0, 0.37, 0.38), 0.012, segs=8)
    for k in range(4):
        a = k * math.pi / 2
        cylm(K["cast_iron"], M, (0, 0.3, 0.38), (math.cos(a) * 0.16, 0.3, 0.38 + math.sin(a) * 0.16), 0.008, segs=5)
    boxm(K["shop_table_wood"], M, (0, 0, 0.75), (0.44, 0.92, 0.035), bevel=0.006)
    boxm(K["shop_table_wood"], M, (0.0, -0.32, 0.69), (0.36, 0.22, 0.08), bevel=0.005)
    sphere(K["brass"], M, (0.19, -0.32, 0.69), 0.008, 8, 5)
    # The head: bed, pillar, arm, needle bar head; balance wheel; spool pin and thread.
    H = M @ T(0, 0, 0.768)
    boxm(K["black_paint"], H, (0, 0, 0.025), (0.17, 0.36, 0.05), bevel=0.01)
    boxm(K["black_paint"], H, (0, 0.12, 0.15), (0.09, 0.08, 0.22), bevel=0.02)
    boxm(K["black_paint"], H, (0, 0.0, 0.25), (0.08, 0.3, 0.07), bevel=0.025)
    boxm(K["black_paint"], H, (0.0, -0.15, 0.17), (0.08, 0.06, 0.17), bevel=0.02)
    cylm(K["chrome"], H, (0.01, -0.16, 0.08), (0.01, -0.16, 0.04), 0.002, segs=5)
    boxm(K["chrome"], H, (0.0, -0.08, 0.052), (0.09, 0.07, 0.004))
    lathe(K["chrome"], [(0.0, 0.0), (0.07, 0.0), (0.072, 0.02), (0.06, 0.025), (0.0, 0.025)], H @ T(0, 0.15, 0.22, tilt=(-math.pi / 2, 0)),
          segs=20)
    cylm(K["chrome"], H, (0.0, 0.06, 0.285), (0.0, 0.06, 0.33), 0.003, segs=5)
    lathe(K["thread_red"], [(0.0, 0.0), (0.012, 0.0), (0.012, 0.004), (0.01, 0.004), (0.01, 0.036), (0.012, 0.036),
                            (0.012, 0.04), (0.0, 0.04)], H @ T(0.0, 0.06, 0.286), segs=12)
    for k in range(5):
        boxm(K["gold_paint"], H, (0.041, -0.06 + k * 0.03, 0.25), (0.002, 0.016, 0.03))


def dress_form(K, M, silk="shop_hol_silk"):
    """A tailor's dress form on its tripod, a length of silk pinned round its waist."""
    torso = [(0.0, 0.0), (0.12, 0.0), (0.135, 0.06), (0.125, 0.16), (0.105, 0.24), (0.125, 0.32), (0.14, 0.4),
             (0.13, 0.46), (0.09, 0.5), (0.045, 0.52), (0.04, 0.58), (0.045, 0.6), (0.0, 0.61)]
    lathe(K["vinyl_cream"], torso, M @ T(0, 0, 0.92) @ Matrix.Diagonal((0.78, 1.0, 1.0, 1.0)), segs=24, cap_bottom=True)
    lathe(K[WOOD], [(0.0, 0.0), (0.05, 0.0), (0.05, 0.02), (0.0, 0.02)], M @ T(0, 0, 1.53), segs=14)
    cylm(K[WOOD], M, (0, 0, 0.3), (0, 0, 0.93), 0.013, segs=8)
    for k in range(3):
        a = k * math.tau / 3
        cylm(K[WOOD], M, (0, 0, 0.32), (math.cos(a) * 0.28, math.sin(a) * 0.28, 0.0), 0.012, segs=6)
    skirt = [(0.135, 0.18), (0.145, 0.1), (0.17, -0.1), (0.2, -0.32), (0.22, -0.5)]
    for k, (r, z) in enumerate(skirt[:-1]):
        band_mesh = skirt[k:k + 2]
        lathe(K[silk], [(band_mesh[0][0], band_mesh[0][1]), (band_mesh[1][0], band_mesh[1][1])],
              M @ T(0, 0, 0.92) @ Matrix.Diagonal((0.82, 1.0, 1.0, 1.0)), segs=24, cap_bottom=False)
    torus(K["thread_red"], M @ Matrix.Diagonal((0.8, 1.0, 1.0, 1.0)), (0, 0, 0.92 + 0.18), (0, 0, 1), 0.137, 0.006, n=24, m=4)
    torus(K["thread_yellow"], M @ Matrix.Diagonal((0.8, 1.0, 1.0, 1.0)), (0, 0, 0.92 + 0.44), (0, 0, 1), 0.13, 0.004, n=24, m=4)


def hood_dryer(K, M):
    """A standing hood hair dryer: five-legged foot, the pole, its arm and the hood."""
    for k in range(5):
        a = k * math.tau / 5
        cylm(K["chrome"], M, (0, 0, 0.06), (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.03), 0.012, segs=6)
        sphere(K["plastic_black"], M, (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.025), 0.025, 8, 5)
    cylm(K["chrome"], M, (0, 0, 0.04), (0, 0, 1.1), 0.018, segs=10)
    cylm(K["chrome"], M, (0, 0, 1.1), (0.22, 0, 1.25), 0.014, segs=8)
    H = M @ T(0.3, 0, 1.18, tilt=(0, -0.5))
    lathe(K["plastic_pink"], [(0.0, 0.32), (0.08, 0.31), (0.16, 0.27), (0.2, 0.18), (0.21, 0.04), (0.2, 0.0),
                              (0.185, 0.0), (0.195, 0.04), (0.185, 0.17), (0.15, 0.25), (0.0, 0.29)], H, segs=28, cap_bottom=False)
    lathe(K["chrome"], [(0.0, 0.32), (0.06, 0.32), (0.06, 0.38), (0.0, 0.38)], H, segs=16)
    boxm(K["plastic_white"], M, (0, 0, 1.0), (0.1, 0.08, 0.14), bevel=0.02)
    sphere(K["plastic_black"], M, (0.05, 0, 1.03), 0.012, 8, 5)


# ------------------------------------------------------------------ electrics

def crt_tv(K, M, w=0.5, on=True):
    """A box television, screen to +x: wood-grain cabinet, curved screen showing snow, the
    knobs and the speaker slots beside it, rabbit-ear aerial."""
    h, d = w * 0.82, w * 0.86
    boxm(K[WOOD], M, (0, 0, h / 2), (d * 0.62, w, h), bevel=0.02)
    boxm(K["plastic_black"], M, (-d * 0.42, 0, h * 0.48), (d * 0.36, w * 0.72, h * 0.72), bevel=0.04)
    boxm(K["plastic_black"], M, (d * 0.31, -w * 0.11, h * 0.52), (0.03, w * 0.72, h * 0.78), bevel=0.02)
    sw, sh = w * 0.62, h * 0.6
    rows, cols = 6, 8
    bm = K["crt_static" if on else "plastic_black"]
    uvl = bm.loops.layers.uv.verify() if on else None
    grid = []
    for i in range(rows + 1):
        row = []
        for j in range(cols + 1):
            u, v = j / cols, i / rows
            y = -w * 0.11 - sw / 2 + u * sw
            z = h * 0.52 - sh / 2 + v * sh
            bulge = 0.018 * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2)
            row.append((bm.verts.new(M @ Vector((d * 0.33 + bulge, y, z))), (u, v)))
        grid.append(row)
    for i in range(rows):
        for j in range(cols):
            quad_v = (grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j])
            f = bm.faces.new([q[0] for q in quad_v])
            if uvl is not None:
                for loop, (_v, uv) in zip(f.loops, quad_v):
                    loop[uvl].uv = uv
    for k in range(7):
        boxm(K["plastic_black"], M, (d * 0.315, w * 0.36, h * 0.3 + k * 0.03), (0.006, w * 0.14, 0.008))
    for k, z in enumerate((h * 0.72, h * 0.6)):
        lathe(K["plastic_white"], [(0.0, 0.0), (0.016, 0.0), (0.016, 0.016), (0.012, 0.02), (0.0, 0.02)],
              M @ T(d * 0.32, w * 0.36, z, tilt=(0, math.pi / 2)), segs=12)
    sphere(K["led_red"], M, (d * 0.32, w * 0.4, h * 0.18), 0.004, 6, 4)
    for s in (-1, 1):
        cylm(K["chrome"], M, (-0.05, 0, h), (-0.12, s * w * 0.5, h + w * 0.8), 0.003, segs=5)
    sphere(K["plastic_black"], M, (-0.05, 0, h + 0.01), 0.03, 10, 6)


def radio(K, M, w=0.42):
    """A cassette radio, front to +x: two speaker cones behind grilles, the cassette door,
    the lit tuning dial, keys, knobs, carrying handle, telescopic aerial."""
    h, d = w * 0.52, w * 0.28
    boxm(K["plastic_black"], M, (0, 0, h / 2), (d, w, h), bevel=0.012)
    for y in (-w * 0.32, w * 0.32):
        lathe(K["rubber"], [(0.0, 0.0), (0.03, 0.005), (0.075, 0.02), (0.08, 0.02)], M @ T(d / 2 - 0.022, y, h * 0.46, tilt=(0, math.pi / 2)),
              segs=18, cap_bottom=False)
        torus(K["chrome"], M, (d / 2 + 0.001, y, h * 0.46), (1, 0, 0), 0.082, 0.004, n=20, m=4)
        for k in range(7):
            boxm(K["chrome"], M, (d / 2 + 0.002, y, h * 0.46 - 0.06 + k * 0.02), (0.002, 0.15, 0.0025))
    boxm(K["plastic_black"], M, (d / 2 + 0.001, 0, h * 0.42), (0.004, w * 0.28, h * 0.42))
    boxm(K["glass"], M, (d / 2 + 0.004, 0, h * 0.42), (0.003, w * 0.24, h * 0.3))
    boxm(K["dial_glow"], M, (d / 2 + 0.002, 0, h * 0.84), (0.003, w * 0.8, 0.02))
    for k in range(6):
        boxm(K["chrome"], M, (0, -w * 0.12 + k * 0.024, h + 0.006), (d * 0.4, 0.018, 0.012), bevel=0.002)
    for y in (-w * 0.42, w * 0.42):
        cylm(K["chrome"], M, (0, y, h), (0, y, h + 0.07), 0.006, segs=6)
    cylm(K["chrome"], M, (0, -w * 0.42, h + 0.07), (0, w * 0.42, h + 0.07), 0.007, segs=8)
    cylm(K["chrome"], M, (-d / 2, w * 0.4, h), (-d / 2 - 0.05, w * 0.45, h + 0.45), 0.003, segs=5)


def desk_fan(K, M, s=1.0):
    """A desk fan: round foot, stand, motor, four blades in their wire cage."""
    S = M @ Matrix.Scale(s, 4)
    lathe(K["plastic_cream"], [(0.0, 0.0), (0.12, 0.0), (0.12, 0.03), (0.05, 0.05), (0.0, 0.05)], S, segs=24)
    cylm(K["chrome"], S, (0, 0, 0.05), (0, 0, 0.3), 0.012, segs=8)
    H = S @ T(0, 0, 0.36, tilt=(0, math.pi / 2 - 0.1))
    lathe(K["plastic_cream"], [(0.0, -0.1), (0.05, -0.09), (0.055, 0.0), (0.02, 0.03), (0.0, 0.03)], H, segs=16)
    for k in range(4):
        a = k * math.pi / 2
        R = H @ Matrix.Translation((0, 0, 0.05)) @ Matrix.Rotation(a, 4, "Z")
        extrude_outline(K["plastic_blue"], R, [(0.02, -0.02), (0.13, -0.05), (0.15, 0.0), (0.12, 0.04), (0.02, 0.02)], 0.003)
    for z, r in ((0.03, 0.17), (0.08, 0.17), (0.11, 0.1)):
        torus(K["chrome"], H, (0, 0, z), (0, 0, 1), r, 0.0025, n=28, m=4)
    for k in range(16):
        a = k / 16 * math.tau
        tube(K["chrome"], H, [(math.cos(a) * 0.17, math.sin(a) * 0.17, 0.03), (math.cos(a) * 0.17, math.sin(a) * 0.17, 0.08),
                              (math.cos(a) * 0.1, math.sin(a) * 0.1, 0.11), (0, 0, 0.12)], 0.0015, segs=3)


def wall_clock(K, M, r=0.15, pendulum=False):
    """A wall clock facing local +x: a wooden case (round, or a pendulum box), the dial with its
    hour marks, hands and glass."""
    if pendulum:
        boxm(K[WOOD], M, (-0.04, 0, -0.18), (0.08, r * 2.2, r * 4.4), bevel=0.012)
        boxm(K["glass"], M, (0.002, 0, -0.32), (0.004, r * 1.6, r * 1.8))
        cylm(K["brass"], M, (-0.01, 0, -0.08), (-0.01, 0, -0.42), 0.003, segs=5)
        lathe(K["brass"], [(0.0, 0.0), (0.04, 0.0), (0.04, 0.006), (0.0, 0.006)], M @ T(-0.01, 0, -0.42, tilt=(0, math.pi / 2)), segs=16)
    else:
        lathe(K[WOOD], [(0.0, 0.0), (r + 0.02, 0.0), (r + 0.025, 0.03), (r + 0.01, 0.05), (r, 0.05)], M @ T(-0.05, 0, 0, tilt=(0, math.pi / 2)),
              segs=32, cap_bottom=True)
    lathe(K["porcelain"], [(0.0, 0.0), (r, 0.0), (r, 0.002), (0.0, 0.002)], M @ T(0.0, 0, 0, tilt=(0, math.pi / 2)), segs=32)
    for k in range(12):
        a = k / 12 * math.tau
        boxm(K["black_paint"], M @ Matrix.Rotation(a, 4, "X"), (0.003, 0, r * 0.84), (0.002, 0.006 if k % 3 else 0.012, 0.022))
    for a, length, wdt in ((0.9, r * 0.55, 0.008), (-2.2, r * 0.8, 0.005)):
        boxm(K["black_paint"], M @ Matrix.Rotation(a, 4, "X"), (0.005, 0, length / 2), (0.002, wdt, length))
    lathe(K["glass"], [(0.0, 0.025), (r, 0.0), (r + 0.002, 0.0)], M @ T(0.004, 0, 0, tilt=(0, math.pi / 2)), segs=32, cap_bottom=False)


def balance_scale(K, M):
    """A shop's pan balance: iron foot, pillar, beam, the two brass pans on chains, weights."""
    boxm(K["cast_iron"], M, (0, 0, 0.02), (0.18, 0.42, 0.04), bevel=0.01)
    cylm(K["cast_iron"], M, (0, 0, 0.04), (0, 0, 0.3), 0.012, segs=10)
    boxm(K["brass"], M, (0, 0, 0.31), (0.02, 0.5, 0.014), bevel=0.003)
    for y in (-0.24, 0.24):
        for k in range(3):
            a = k * math.tau / 3
            cylm(K["brass"], M, (0, y, 0.305), (math.cos(a) * 0.08, y + math.sin(a) * 0.08, 0.1), 0.0012, segs=3)
        lathe(K["brass"], [(0.0, 0.0), (0.06, 0.004), (0.095, 0.02), (0.1, 0.024)], M @ T(0, y, 0.08), segs=24, cap_bottom=False)
    for k, (wr, wh) in enumerate(((0.015, 0.02), (0.012, 0.016), (0.009, 0.012))):
        lathe(K["brass"], [(0.0, 0.0), (wr, 0.0), (wr, wh * 0.7), (wr * 0.4, wh * 0.8), (wr * 0.4, wh), (0.0, wh)],
              M @ T(-0.05 + k * 0.035, 0.12, 0.04), segs=12)


def lpg_cylinder(K, M, paint="plastic_red"):
    lathe(K[paint], [(0.0, 0.02), (0.14, 0.02), (0.15, 0.06), (0.15, 0.46), (0.12, 0.54), (0.05, 0.57), (0.0, 0.57)], M, segs=24)
    lathe(K[paint], [(0.13, 0.0), (0.14, 0.0), (0.14, 0.05), (0.13, 0.05)], M, segs=24, cap_bottom=False)
    lathe(K["brass"], [(0.0, 0.57), (0.02, 0.57), (0.02, 0.62), (0.012, 0.64), (0.0, 0.64)], M, segs=12)
    torus(K[paint], M, (0, 0, 0.66), (0, 1, 0), 0.07, 0.01, n=16, m=5)
    tube(K["rubber"], M, [(0.02, 0, 0.62), (0.1, 0, 0.6), (0.25, 0.1, 0.4), (0.35, 0.2, 0.62)], 0.007, segs=6)


def drum(K, M, paint="plastic_blue", r=0.29, h=0.88):
    """A 200 litre steel drum: rolled hoops, the chime at each end, the bung on top."""
    prof = [(0.0, 0.0), (r - 0.01, 0.0), (r, 0.012), (r + 0.004, 0.02), (r, 0.03)]
    for z in (h * 0.33, h * 0.67):
        prof += [(r, z - 0.02), (r + 0.012, z), (r, z + 0.02)]
    prof += [(r, h - 0.03), (r + 0.004, h - 0.02), (r, h - 0.012), (r - 0.01, h), (0.0, h - 0.004)]
    lathe(K[paint], prof, M, segs=32)
    lathe(K["steel"], [(0.0, 0.0), (0.03, 0.0), (0.03, 0.012), (0.0, 0.012)], M @ T(r * 0.55, 0, h - 0.004), segs=10)


def tyre(K, M, r=0.29, w=0.075):
    """A loose tyre, lying flat at M (axis up)."""
    torus(K["tyre"], M, (0, 0, w / 2), (0, 0, 1), r - w * 0.5, w * 0.5, n=40, m=10)
    for k in range(40):
        a = k / 40 * math.tau
        boxm(K["tyre"], M @ Matrix.Rotation(a, 4, "Z"), (r - 0.003, 0, w / 2), (0.014, 0.018, w * 0.85))


def soda_crate(K, M, key="plastic_red", label="orange"):
    """A moulded bottle crate of a dozen sodas."""
    sx, sy, sz = 0.42, 0.3, 0.27
    for z in (0.012, sz * 0.5, sz - 0.012):
        for y in (-sy / 2, sy / 2):
            boxm(K[key], M, (0, y, z), (sx, 0.014, 0.024), bevel=0.003)
        for x in (-sx / 2, sx / 2):
            boxm(K[key], M, (x, 0, z), (0.014, sy, 0.024), bevel=0.003)
    for x in np.linspace(-sx / 2, sx / 2, 5):
        boxm(K[key], M, (x, -sy / 2, sz / 2), (0.016, 0.014, sz))
        boxm(K[key], M, (x, sy / 2, sz / 2), (0.016, 0.014, sz))
    boxm(K[key], M, (0, 0, 0.006), (sx, sy, 0.012))
    for x in np.linspace(-0.15, 0.15, 4):
        for y in np.linspace(-0.1, 0.1, 3):
            bottle(K, M @ T(x, y, 0.012), "soda", label=label, segs=12)


def cooler(K, M, key="plastic_blue"):
    """An ice box on the floor, lid open a little, sodas and ice in it."""
    boxm(K[key], M, (0, 0, 0.2), (0.4, 0.62, 0.4), bevel=0.03)
    boxm(K["plastic_white"], M, (0.0, 0, 0.392), (0.34, 0.56, 0.02))
    boxm(K[key], M @ T(-0.2, 0, 0.405, tilt=(0, -0.35)), (0.2, 0, 0.022), (0.42, 0.64, 0.05), bevel=0.02)
    for y in (-0.22, 0.22):
        cylm(K["steel"], M, (-0.205, y - 0.04, 0.4), (-0.205, y + 0.04, 0.4), 0.008, segs=6)
    for k in range(5):
        boxm(K["glass"], M @ T(0, 0, 0, yaw=k), (0.05 * math.cos(k * 1.3), 0.12 * math.sin(k * 2.1), 0.405), (0.04, 0.04, 0.03),
             bevel=0.006)
