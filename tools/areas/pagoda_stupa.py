"""Family ash stupas (chedey) of a neglected Khmer wat, in metres, X east, Y north.

Every memorial shares the old square pedestal, open niche chamber and lotus bands
(pagoda_architecture.stupa), now in mould-streaked lime and exposed brick, and is
crowned by one of four upper forms seen at Cambodian and Thai wats: a ringed Khmer
spire, a Thai bell chedi, a lotus-bud tower and a stepped prang-like crown. Most lean,
crack and lose their tips; figs seed in a few; old cloth, incense and dead garlands
remain from the last time anyone came. Everything stays inside the 1.4 m collision
footprint the ghosts' navigation assumes, and the family stupas' fronts stay clear.
"""
import math

import numpy as np

from kit import lathe, tube
from pagoda_architecture import Craft
from pagoda_ruin import candles, dead_garland, erode, fig_roots, incense_pot, lean, sash

FAMILY = ('chea', 'wife', 'chhun', 'kanha')


def memorial(coll, m, x, y, k, height, ident, rng):
    family = ident in FAMILY
    made = set(coll.objects)
    roll = rng.random()
    if family:
        stone = m['mould_white'] if k % 2 else m['mould_ochre']
    else:
        stone = m[['mould_white', 'mould_grey', 'mould_ochre', 'burnt', 'mould_grey', 'mould_white'][k % 6]]
    trim = m['mould_gold'] if k % 3 == 0 else stone
    c = Craft()
    for z, w, h in [(0, 1.38, .11), (.11, 1.27, .09), (.2, 1.12, .16), (.36, 1.2, .07), (.43, 1.08, .09), (.52, .94, .25), (.77, 1.1, .08), (.85, .98, .08)]:
        c.block(stone, x, y, z, w, w, h)
    for dx in (-.32, .32):
        for dy in (-.32, .32):
            c.block(stone, x + dx, y + dy, .93, .22, .22, .62)
    c.block(m['void'], x, y, .94, .5, .5, .63)
    for side in range(4):
        a = side * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)

        def p(t, h, depth=.45):
            return (x + ca * t - sa * depth, y + sa * t + ca * depth, h)
        for r in (0, .045, .085):
            pts = [p(-.19 - r, .97), p(-.19 - r, 1.27), p(-.14 - r, 1.43), p(0, 1.66 + r), p(.14 + r, 1.43), p(.19 + r, 1.27), p(.19 + r, .97)]
            tube(f'stupa_niche_{k}', coll, pts, .018, trim, sides=5)
        for petal in range(5):
            t = (petal - 2) * .055
            c.face(trim, [p(t - .035, 1.02, .455), p(t, 1.15 - abs(t) * .5, .47), p(t + .035, 1.02, .455)])
        # Plaster fallen from the pedestal faces shows the brick behind.
        if not (family and side == 2) and rng.random() < .55:
            t, w = rng.uniform(-.3, .3), rng.uniform(.15, .35)
            if rng.random() < .5:
                d, z0, hh = .566, .21, rng.uniform(.08, .14)
            else:
                d, z0, hh = .476, rng.uniform(.53, .6), rng.uniform(.1, .17)
            c.face(m['brick'], [p(t - w / 2, z0, d), p(t + w / 2, z0, d), p(t + w * .3, z0 + hh, d), p(t - w * .4, z0 + hh * .8, d)][::-1])
    for z, w, h in [(1.55, 1.02, .08), (1.63, 1.1, .07), (1.7, .94, .09), (1.79, .8, .1)]:
        c.block(stone, x, y, z, w, w, h)
    for base, r in [(.55, .53), (1.82, .46)]:
        c.ring(stone, x, y, base, r, .14, 32, top=r * .76)
        for j in range(20):
            if not family and rng.random() < .15:
                continue  # chipped petals
            a = j * math.tau / 20
            pts = [(x + math.cos(a + da) * rr, y + math.sin(a + da) * rr, base + hh) for da, rr, hh in [(-.12, r, 0), (0, r + .035, .09), (.12, r, 0), (0, r * .83, .2)]]
            c.face(trim, [pts[i] for i in (0, 1, 3)])
            c.face(trim, [pts[i] for i in (1, 2, 3)])
    scale = max(.6, height - 2.0)
    form = k % 4
    broken = not family and rng.random() < .32
    upper = []
    if form == 0:      # ringed Khmer spire
        profile = [(.34, 0), (.38, .08), (.3, .16), (.26, .35), (.16, .48), (.17, .54), (.12, .6)]
    elif form == 1:    # Thai bell chedi on a round cushion
        profile = [(.36, 0), (.38, .05), (.33, .1), (.4, .2), (.41, .3), (.37, .4), (.28, .5), (.17, .56), (.12, .6)]
    elif form == 2:    # lotus-bud tower
        profile = [(.3, 0), (.34, .1), (.25, .18), (.3, .3), (.32, .4), (.26, .5), (.15, .57), (.12, .6)]
    else:              # stepped prang-like crown
        profile = [(.36, 0), (.36, .1), (.3, .1), (.3, .2), (.25, .2), (.25, .3), (.2, .3), (.2, .4), (.16, .4), (.16, .5), (.12, .6)]
    upper.append(lathe(f'stupa_drum_{k}', coll, [(r, h * scale) for r, h in profile], x, y, 1.93, stone, segments=32))
    bottom = 1.93 + .6 * scale
    rings = 7 if not broken else int(rng.integers(1, 4))
    for j in range(rings):
        r = .13 * (1 - j / 9)
        h = .055 * scale
        c.ring(trim, x, y, bottom + j * h, r, h * .5, 24, top=r * .82)
    if not broken:
        c.ring(stone, x, y, bottom + .36 * scale, .054, .44 * scale, 16, top=.002)
    else:
        # A snapped tip: brick core at the break, the lost top lying on the pedestal.
        tip = bottom + rings * .055 * scale
        c.ring(m['brick'], x, y, tip, .1, .04, 10, top=.04)
        side = rng.choice([-1, 1])
        piece = lathe(f'stupa_fallen_tip_{k}', coll, [(.1, 0), (.11, .06), (.08, .16), (.05, .3), (.002, .42)], 0, 0, 0, stone, segments=12)
        piece.location = (x + side * .36, y + rng.uniform(-.05, .3), .42)
        piece.rotation_euler = (0, side * rng.uniform(1.3, 1.5), rng.uniform(0, math.tau))
        upper.append(piece)
    for j in range(9):
        a = j * math.tau / 9 + k
        c.block(m['moss'], x + .56 * math.cos(a), y + .56 * math.sin(a), .012, .18, .14, .035)
    built = c.build(f'memorial_{k}', coll)
    dressing = []
    if not family:
        if rng.random() < .35:
            dressing += sash(coll, m, f'stupa_sash_{k}', x, y, 1.89, .5, m[['saffron', 'white_cloth', 'red_cloth'][k % 3]], rng, tail=rng.uniform(.4, 1.1))
        if rng.random() < .45:
            dressing += incense_pot(coll, m, f'stupa_incense_{k}', x + rng.uniform(-.25, .25), y - .8, 0, rng)
        if rng.random() < .3:
            dressing += dead_garland(coll, m, f'stupa_garland_{k}', x + rng.uniform(-.3, .3), y - .86, .02, .16, rng)
        if rng.random() < .3:
            dressing += candles(coll, m, f'stupa_candle_{k}', x + rng.uniform(-.4, .4), y - .76, 0, rng)
        if roll < .12:
            dressing += fig_roots(coll, m, f'stupa_fig_{k}', x, y, bottom + .1, lambda z: .58 if z < 1.9 else .42, rng, n=6,
                                  spread=.08, crown=rng.uniform(1.1, 1.8))
    else:
        # The family still comes: a fresh-ish cloth, kept candle stubs at the side.
        dressing += sash(coll, m, f'stupa_sash_{k}', x, y, 1.89, .5, m['white_cloth'], rng, tail=.5)
        dressing += candles(coll, m, f'stupa_candle_{k}', x - .45, y - .8, 0, rng)
    objs = built + [o for o in coll.objects if o not in made and o not in built]
    erode(objs, .006 if family else .011, 5.5, k)
    if not family:
        lean([o for o in objs if not o.name.startswith('stupa_fallen_tip')], x, y, rng.normal(0, .022), rng.normal(0, .022))
    return objs
