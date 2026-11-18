"""Village expansion patch (Episode 1, November 2026; plan in village_layout.py).

    blender -b --factory-startup --python-exit-code 1 art-source/blender/ep1/ep1_area_village.blend \\
        -P tools/areas/rebuild-village-expansion.py
    npm run export -- ep1/ep1_area_village && npm run assets -- ep1/ep1_area_village.glb

Widens the ground to the expansion's terrain (old heights kept exactly, see
village_expansion.extend_ground), takes the forest's own plants out of the built
areas' clearings and lanes, opens the compound fence where a lane leaves it, and
(re)builds each built area (village_layout.BUILT) in its own collection,
`expansion_<area>`, cleared each run. Saves the file.

The forest on the new ground is not authored here: ForestBorder.ts grows it at
runtime from the village's own trees (data/forestBorder.ts, data/villageAreas.ts).
"""
import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import village_layout as L  # noqa: E402
import village_expansion as VE  # noqa: E402
import house_rooms  # noqa: E402
from kit import collider  # noqa: E402

# Ground kept free of forest round each area's buildings: (layout key, radius).
KEEP_OUT = {"west": [("house", 5.5), ("granary", 3.0), ("byre", 4.5)], "east": [("sala", 3.6)]}
# Where each side lane passes the compound fence: (fence prefix, axis, from, to).
GAPS = {"west": ("fence_w_0", "y", 9.75, 12.65), "east": ("fence_e_0", "y", 6.6, 9.55)}
BUILDERS = {"west": "west_yard", "east": "east_pond"}
SEEDS = {"west": 1900, "east": 1931}

village = bpy.data.collections["ep1_area_village"]


def area_collection(key):
    name = f"expansion_{key}"
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        village.children.link(coll)
    for o in list(coll.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
    return coll


house_rooms._complete_gltf_group()
house_rooms._protos_from_file()
print("Built areas:", sorted(L.BUILT), flush=True)
VE.extend_ground()
keep_out = []
for key in L.BUILT:
    for part, r in KEEP_OUT.get(key, []):
        x, y = L.AREAS[key][part][:2]
        keep_out.append((x, y, r))
removed = VE.clear_open_ground(keep_out=keep_out)
for key in sorted(L.BUILT):
    if key in GAPS:
        VE.open_fence(*GAPS[key])
ground = VE.Ground()
for key in sorted(L.BUILT):
    module = __import__(BUILDERS[key])
    coll = area_collection(key)
    print(f"Building {key} into {coll.name}", flush=True)
    module.build(coll, ground, np.random.default_rng(SEEDS[key]))
    # Library copies and scans land in the scene's collections too: keep them in the area's.
    for o in list(coll.all_objects):
        for c in list(o.users_collection):
            if c != coll and not c.name.startswith("_"):
                c.objects.unlink(o)
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(f"Saved {bpy.data.filepath}; removed {len(removed)} plants", flush=True)
