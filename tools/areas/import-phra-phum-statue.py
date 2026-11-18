"""Prepares the figure for the Preah Phum's chamber (November 2026).

The source is the user's own Tripo model (~/Downloads/khmer-phraphum-status.glb,
made on a paid Tripo plan, so the studio owns it): a lacquered and gilt
figurine of a kneeling woman beckoning with her raised right hand, a money bag
at her side, on a round lotus pedestal (the beckoning lady of shop and house
shrines; advisor review).

    blender -b --factory-startup --python-exit-code 1 -P tools/areas/import-phra-phum-statue.py -- \\
        ~/Downloads/khmer-phraphum-status.glb

Nothing is cut: she keeps her pedestal. tools/areas/statue_prep.py decimates
her to about 14k triangles and bakes her aged for a spirit house that has had
candles burning in it for sixty years: the shop-new orange and gold faded,
rubbed through to the gesso, black with soot toward her crown and in every
fold. Writes art-source/library/scans/phra_phum_lady.glb, 0.30 m tall, the
foot of her pedestal at the origin, facing -Y (Blender).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from statue_prep import prepare  # noqa: E402

SRC = os.path.expanduser(sys.argv[sys.argv.index("--") + 1])

prepare(
    SRC, "phra_phum_lady", .30, tris=14000, bake_px=1024,
    look=dict(saturation=.55, value=.55, bare=((.2, .175, .14), (.33, .3, .25)), rise=(.05, .98, .25, .8)),
    extras={
        "title": "Beckoning lady on a lotus pedestal (the Preah Phum's figure)",
        "author": "The Unbroken Debt (made by the studio with Tripo AI, paid plan)",
        "source": "user-supplied khmer-phraphum-status.glb",
        "license": "Studio-owned (Tripo paid plan: commercial use, no attribution required)",
        "adapted": ("decimated to {tris} triangles on new UVs; colour (aged: faded, rubbed, soot, dust) and normals "
                    "baked from the original at {px} px; scaled to {height} m"),
    })
