"""Prepares the user's Neak Ta statue for the banyan shrine (November 2026).

The source is the user's own Tripo model (~/Downloads/neak-ta-shrine-status.glb,
made on a paid Tripo plan, so the studio owns it): a painted three-faced guardian
seated cross-legged with a mace, on a stone slab with tins of joss sticks, a
lotus incense holder, a wooden box and a rock round him.

    blender -b --factory-startup --python-exit-code 1 -P tools/areas/import-neakta-statue.py -- \\
        ~/Downloads/neak-ta-shrine-status.glb

Keeps only the figure: everything below his seat, the box and rock to his
right, the tins and the incense holder in front of him are cut away (and the
holder's red rim where it touched his shin). tools/areas/statue_prep.py then
decimates him to about 36k triangles and bakes him aged (paint faded and
flaking to grey cement, soot toward the heads and in every crease); the black
blotch the generator left on his chest is painted over like the rest of him.
Writes art-source/library/scans/neakta_guardian.glb, 0.66 m tall, the bottom
of his crossed legs at the origin, facing -Y (Blender).
"""
import os
import sys

import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
from statue_prep import prepare  # noqa: E402

SRC = os.path.expanduser(sys.argv[sys.argv.index("--") + 1])
SEAT = .275          # top of the source's stone slab: everything below goes


def offerings(cen, col):
    """Faces that are not the figure, by where they are (source coordinates)."""
    x, y, z = cen[:, 0], cen[:, 1], cen[:, 2]
    # The box stands askew at his right: its inner edge runs (-.285, .22) -> (-.14, -.2).
    p1, p2 = np.array((-.285, .22)), np.array((-.14, -.2))
    d = p2 - p1
    side = d[0] * (y - p1[1]) - d[1] * (x - p1[0])
    ref = d[0] * (.15 - p1[1]) - d[1] * (.11 - p1[0])
    red = (col[:, 0] > .3) & (col[:, 1] < .12)
    rim = red & (y < 0) & (z < .40) & (x > .03) & (x < .19)
    return (z < SEAT) | (x < -.225) | (y < -.06) | (side * ref < 0) | rim


prepare(
    SRC, "neakta_guardian", .66, cut=offerings,
    blotch=(Vector((.104, .07, .60)), Vector((.08, .08, .085)), ((.2, .215, .23), (.29, .305, .315))),
    extras={
        "title": "Neak Ta guardian (three-faced seated figure with a mace)",
        "author": "The Unbroken Debt (made by the studio with Tripo AI, paid plan)",
        "source": "user-supplied neak-ta-shrine-status.glb",
        "license": "Studio-owned (Tripo paid plan: commercial use, no attribution required)",
        "adapted": ("offerings, slab, box and rock cut away; decimated to {tris} triangles on new UVs; "
                    "colour (aged: faded, flaking, soot, dust) and normals baked from the original at {px} px; "
                    "scaled to {height} m"),
    })
