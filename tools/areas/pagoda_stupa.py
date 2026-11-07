"""Family ash stupas (chedey) of a neglected Khmer wat, in metres, X east, Y north.

Each is a placed copy of a sculpted, baked form (tools/areas/pagoda_stupa_kit.py, built by
tools/ep2/build-stupas.py): a ringed spire, a bell, a lotus bud, a stepped prang, or one
snapped through its drum. They lean; figs have seeded in many; old cloth, incense and dead
garlands remain from the last time anyone came. Some still hold the dead's photograph,
and on some of those someone has scratched the eyes or the whole face away.

Everything stays inside the 1.4 m collision footprint the ghosts' navigation assumes, and
the family stupas' fronts stay clear for their interactions.

Portraits, red cord and opened urns are advisor-review items.
"""
import math

import numpy as np

import fit

from kit import lathe, tube
from pagoda_kit import material, piece
from pagoda_photos import plaque
from pagoda_ruin import candles, dead_garland, fig_roots, incense_pot, lean, place_object, tied_cloth

FAMILY = ('chea', 'wife', 'chhun', 'kanha')
FORMS = ('stupa_spire', 'stupa_bell', 'stupa_bud', 'stupa_prang')
BROKEN = ('stupa_spire_broken', 'stupa_bell_broken')
# The kit's masonry, in metres before a stupa is scaled to its height.
DADO_Z, CHAMBER_Z, NICHE_Z, TIER_Z, FULL_HEIGHT = .57, .85, 1.14, 1.72, 3.4
# Portraits on the sheet (pagoda_photos.SHEET), by what has happened to them.
INTACT = (0, 1, 2, 3, 6, 7)
DEFACED = (4, 5, 8, 10)
ROTTED = (9, 11)
FAMILY_PORTRAIT = {'chea': 1, 'wife': 0, 'kanha': 6}  # Chhun's oval was empty long ago

def memorial(coll, m, x, y, k, height, ident, rng):
    family = ident in FAMILY
    broken = not family and rng.random() < .3
    name = BROKEN[k % 2] if broken else FORMS[k % 4]
    stretch = 1.0 if broken else min(1.12, max(.8, height / (FULL_HEIGHT * .94)))
    # Non-family stupas are turned any way; each form's weathering then reads differently.
    turn = 0 if family else int(rng.integers(0, 4))
    body = piece(coll, name, f'memorial_{k}', x, y, 0, turn * math.pi / 2, (1, 1, stretch))
    objs = [body]
    dressing = []

    def photo(cell, in_niche, face=0):
        yaw = face * math.pi / 2
        out = (math.sin(yaw), -math.cos(yaw))
        reach, z = (.325, NICHE_Z * stretch) if in_niche else (.515, DADO_Z * stretch)
        o = plaque(coll, material('M_ep2_funeral_photo'), material('M_ep2_funeral_photo_rim'), f'stupa_photo_{k}',
                   (x + out[0] * reach, y + out[1] * reach, z), yaw, cell, height=.24 if in_niche else .2)
        o['kit_piece'] = True
        dressing.append(o)

    roll = rng.random()
    if family:
        cell = FAMILY_PORTRAIT.get(ident)
        if cell is not None:
            photo(cell, True)
        # The family still comes: a fresh-ish cloth, kept candle stubs at the side.
        dressing += tied_cloth(coll, m, f'stupa_sash_{k}', [body], x, y, 1.15 * stretch, 2.0 * stretch, m['white_cloth'], rng)
        dressing += candles(coll, m, f'stupa_candle_{k}', x - .45, y - .86, 0, rng)
    else:
        if rng.random() < .4:
            r = rng.random()
            pool = DEFACED if r < .4 else ROTTED if r < .6 else INTACT
            photo(int(rng.choice(pool)), rng.random() < .5, int(rng.integers(0, 4)))
        if rng.random() < .35:
            dressing += tied_cloth(coll, m, f'stupa_sash_{k}', [body], x, y, 1.15 * stretch, (2.0 if not broken else 1.85) * stretch,
                                   m[['saffron', 'white_cloth', 'red_cloth'][k % 3]], rng)
        if rng.random() < .45:
            dressing += incense_pot(coll, m, f'stupa_incense_{k}', x + rng.uniform(-.25, .25), y - .86, 0, rng)
        if rng.random() < .3:
            dressing += dead_garland(coll, m, f'stupa_garland_{k}', x + rng.uniform(-.3, .3), y - .9, .02, .16, rng)
        if rng.random() < .3:
            dressing += candles(coll, m, f'stupa_candle_{k}', x + rng.uniform(-.4, .4), y - .84, 0, rng)
        if roll < .3:
            # Figs seed high up and send their roots down over the masonry.
            # Only a snapped stupa has a top a fig tree can stand on; on a whole one the
            # roots alone pour down the masonry, the tree that sent them long dead.
            crown = rng.uniform(1.1, 1.8)
            dressing += fig_roots(coll, m, f'stupa_fig_{k}', x, y, (TIER_Z + .5) * stretch, lambda z: .62 if z < 1.5 else .46, rng, n=7,
                                  spread=.08, crown=crown if broken else 0, support=[body])
    if not family and 'red_thread' in m:
        horror = rng.random()
        if horror < .16:
            # Cracked open: the clay urn pulled out and tipped at the foot, ash and bone spilt
            # on the plinth. Each piece is settled onto whatever is really under it (fit.rest).
            urn = lathe(f'stupa_urn_{k}', coll, [(0, 0), (.07, 0), (.11, .07), (.1, .16), (.05, .2), (.06, .22), (0, .22)], 0, 0, 0, m['clay'], segments=12)
            place_object(urn, x + .05, y - .9, .11, rng.uniform(0, math.tau), (1.45, .2))
            # Bake its place into the mesh: lean() below tilts world-space vertices.
            urn.data.transform(urn.matrix_basis)
            urn.matrix_basis.identity()
            dressing += fit.rest([urn])
            for b in range(int(rng.integers(5, 10))):
                bx, by = x + rng.uniform(-.35, .35), y - rng.uniform(.62, .72)
                length = rng.uniform(.04, .14)
                a = rng.uniform(0, math.tau)
                dressing += fit.rest([tube(f'stupa_bone_{k}', coll, [(bx, by, .36), (bx + math.cos(a) * length, by + math.sin(a) * length * .3, .36)],
                                           rng.uniform(.006, .012), m['bone'], sides=5)])
            dressing += fit.rest([lathe(f'stupa_ash_{k}', coll, [(0, 0), (.22, 0), (.12, .012), (0, .015)], x, y - .66, .34, m['ash'], segments=12)])
        elif horror < .36:
            # Bound with red cord, round and round the plinth, a paper tag knotted in.
            # Laid round a nominal circle, then pulled onto the plinth's real faces after the build
            # (fit.wrap), measured against the stupa alone.
            pts = [(x + math.cos(t) * .62, y + math.sin(t) * .62, .36 + t / math.tau * .05) for t in np.linspace(0, math.tau * 6, 140)]
            dressing.append(fit.wrap(tube(f'stupa_red_cord_{k}', coll, pts, .004, m['red_thread'], sides=3), x, y, .62))
            from pagoda_rituals import talisman
            dressing += [fit.wrap(o, x, y, math.hypot(.68, .3) - .02) for o in talisman(coll, m, f'stupa_tag_{k}', (x - .68, y - .3, .55), rng)]
    objs += dressing
    if not family:
        lean(objs, x, y, rng.normal(0, .022), rng.normal(0, .022))
    return objs
