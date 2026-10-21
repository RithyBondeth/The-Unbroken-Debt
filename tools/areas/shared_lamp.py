"""Builds Sora's hurricane lamp as held in her left hand (Controls and Interface,
section 6: "Glass gauge on the lamp; raise the lamp to read it"): the library
lantern, a flame card on the wick, and a small glass gauge on the tank whose
amber column the game scales with the oil left.

Named nodes the game drives (src/player/HeldLamp.ts):
    lamp_flame      emissive flame card, origin at the wick
    lamp_oil        oil column in the gauge, origin at its bottom (scale Z = oil)
    marker_flame    where the lamp's light sits

Run (repository root), after `npm run fetch-library`:
    blender -b --factory-startup -P tools/areas/shared_lamp.py
then `npm run export -- shared && npm run assets -- shared`.
"""

import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
from kit import ROOT, box, empty, glow_material, import_model, mesh_object, plain, texture  # noqa: E402

BLEND = os.path.join(ROOT, "art-source", "blender", "shared", "shared_lamp.blend")


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = bpy.data.collections.new("shared_lamp")
    bpy.context.scene.collection.children.link(coll)
    lantern = import_model(coll, "Lantern_01", (0, 0, 0), collide=False, name="lamp_body")
    bpy.context.view_layer.update()
    glass = [o for o in lantern.children_recursive if o.type == "MESH" and "glass" in o.name.lower()]
    pts = [o.matrix_world @ v.co for o in glass for v in o.data.vertices]
    z0, z1 = min(p.z for p in pts), max(p.z for p in pts)
    wick = z0 + (z1 - z0) * 0.22
    flame_mat = glow_material("M_lamp_flame", texture("T_ep1_flame_BC"), strength=3.0)
    s = 0.03
    # Two crossed cards of the painted flame (tools/drawings/village.mjs), wick at the origin.
    w, h, lo = s * 0.45, s * 1.6, -s * 0.08
    flame = mesh_object("lamp_flame", coll,
                        [(-w, 0, lo), (w, 0, lo), (w, 0, h), (-w, 0, h), (0, -w, lo), (0, w, lo), (0, w, h), (0, -w, h)],
                        [(0, 1, 2, 3), (4, 5, 6, 7)], flame_mat, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)] * 2)
    flame.location = (0, 0, wick)
    empty("marker_flame", coll, (0, 0, wick + s * 0.6))
    # The gauge: a glass slot on the front of the tank with the amber oil inside.
    body = [o.matrix_world @ v.co for o in lantern.children_recursive if o.type == "MESH" for v in o.data.vertices]
    front = min(p.y for p in body)
    g0, g1 = 0.008, min(0.06, z0 - 0.004) if z0 > 0.03 else 0.05
    brass = plain("M_gauge_rim", (0.55, 0.4, 0.18), rough=0.35, metal=1.0)
    box("lamp_gauge_rim", coll, -0.018, 0.018, front - 0.006, front + 0.002, g0 - 0.004, g1 + 0.004, brass)
    window = plain("M_gauge_glass", (0.03, 0.025, 0.02), rough=0.08)
    box("lamp_gauge_glass", coll, -0.012, 0.012, front - 0.0075, front - 0.0055, g0, g1, window)
    oil_mat = plain("M_gauge_oil", (0.75, 0.42, 0.08), rough=0.2, emission=(0.9, 0.45, 0.08), strength=1.5)
    oil = box("lamp_oil", coll, -0.01, 0.01, front - 0.0082, front - 0.0076, 0.0, g1 - g0, oil_mat)
    # Origin at the bottom of the column, so scaling Z lowers it from the top.
    oil.location.z = g0
    for v in oil.data.vertices:
        v.co.z += (g1 - g0) / 2
    print(f"glass z {z0:.3f}..{z1:.3f}, wick {wick:.3f}, gauge {g0:.3f}..{g1:.3f}, front {front:.3f}")
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print(f"Saved {BLEND}")


build()
