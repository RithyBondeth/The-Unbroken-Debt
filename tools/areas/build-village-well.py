"""Builds the well inside the south gate (village_well.py) into the built village file and
saves it:

    blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/build-village-well.py --python-exit-code 1

rebuild-farmstead.py builds it too (village_review.well). `-- --no-save` builds without saving.
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import village_expansion as VE  # noqa: E402
import village_well as VW  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
old = bpy.data.objects.get("well_rv_well_plaster") or bpy.data.objects.get("well_plaster")
coll = old.users_collection[0] if old else bpy.context.scene.collection
VW.build(coll, VE.Ground())
if "--no-save" not in ARGS:
    bpy.ops.wm.save_mainfile()
    print("[village_well] saved", bpy.data.filepath, flush=True)
