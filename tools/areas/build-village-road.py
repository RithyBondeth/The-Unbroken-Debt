"""Builds the village road (village_road.py) into the built village file and saves it:

    blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/build-village-road.py --python-exit-code 1

rebuild-farmstead.py builds it too (last), so a full rebuild from the Nov 20 file gives the
same; this is the quick way after it. `-- --no-save` builds without saving (for previews).
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import village_expansion as VE  # noqa: E402
import village_road as VR  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


VR.build(collection("village_road"), VE.Ground())
if "--no-save" not in ARGS:
    bpy.ops.wm.save_mainfile()
    print("[village_road] saved", bpy.data.filepath, flush=True)
