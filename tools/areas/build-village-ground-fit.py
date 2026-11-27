"""Lifts what lies flat on the village's ground onto the terrain as the game draws it, in the
built village file, and saves it:

    blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/build-village-ground-fit.py --python-exit-code 1

The paddy floors, the harvested stubble and loose straw on them, the drying mats and their
grain, and the byre's floor were laid 1.2 cm over a bilinear reading of the 1 m terrain grid
(village_expansion.Ground until Nov 26, 2026), which parts from the terrain's triangles by up
to 5.5 cm: in patches the terrain lay over them, and the game drew dark blots in the fields
(the user, Nov 26, 2026: "Make everything single of it inside this village scene for more
realistic"). Each vertex moves by the difference, the floors 0.8 cm more (2 cm over the
terrain, as village_fields and west_yard now lay them). A mesh shared by several objects
moves whole, by the difference under its middle. Runs once: fitted objects are marked.
`-- --no-save` fits without saving.
"""
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import village_expansion as VE  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

FLOORS = ("paddy_floor_", "yard_drying_", "wy_byre_floor")
ON_FLOORS = ("paddy_cut_",)
WISPS = "paddy_straw_wisp"


def fit():
    ground = VE.Ground()
    moved, shared, verts = 0, 0, 0
    for o in list(bpy.data.objects):
        if o.type != "MESH" or o.get("ground_fit"):
            continue
        floor = o.name.startswith(FLOORS)
        if not (floor or o.name.startswith(ON_FLOORS) or WISPS in o.name):
            continue
        extra = 0.008 if floor else 0.0
        mw = o.matrix_world
        if o.data.users > 1:
            c = mw @ (sum((Vector(b) for b in o.bound_box), Vector()) / 8)
            o.location.z += ground(c.x, c.y) - ground.bilinear(c.x, c.y) + extra
            shared += 1
        else:
            inv = mw.inverted()
            for v in o.data.vertices:
                w = mw @ v.co
                w.z += ground(w.x, w.y) - ground.bilinear(w.x, w.y) + extra
                v.co = inv @ w
            o.data.update()
            verts += len(o.data.vertices)
        o["ground_fit"] = 1
        moved += 1
    print(f"[ground_fit] {moved} objects fitted ({shared} shared meshes moved whole, {verts} vertices)", flush=True)


fit()
if "--no-save" not in ARGS:
    bpy.ops.wm.save_mainfile()
    print("[ground_fit] saved", bpy.data.filepath, flush=True)
