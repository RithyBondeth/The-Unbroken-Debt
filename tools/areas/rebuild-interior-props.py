"""Focused update of the kitchen hearth and Sok's palm-leaf manuscripts in the
shipped village, preserving every other object (interior_props.py builds them).

blender -b art-source/blender/ep1/ep1_area_village.blend \
  -P tools/areas/rebuild-interior-props.py -- /tmp/interior-props.glb
Then compress the focused export, merge it with update-house-details-glb.mjs and
install the objects into the source with apply-house-details.py, staged from
/tmp/interior-props-source.blend.
"""
import json
import os
import re
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
from interior_props import kitchen_hearth, palm_leaf_manuscripts

F = 2.5
coll = bpy.data.collections["ep1_area_village"]
old = [o for o in coll.objects
       if re.match(r"^(kitchen_hearth(_.*)?|hearth_.*|palm_leaf_manuscript_\d|manuscript_.*)$", o.name)]
# The original nine placeholders, or this script's own earlier output.
assert len(old) >= 9 and "col_kitchen_hearth" not in {o.name for o in old}, sorted(o.name for o in old)
m = {key: bpy.data.materials[name] for key, name in {
    "worn": "M_worn_wood", "stone": "M_stone", "ash": "M_ash", "embers": "M_hearth_embers",
    "lacquer": "M_red_lacquer", "rope": "M_rope", "teak": "M_house_teak",
}.items()}
old_names = [o.name for o in old]
unchanged = {o.name: (o.matrix_world.copy(), o.data) for o in bpy.data.objects if o not in old}
for obj in old:
    bpy.data.objects.remove(obj, do_unlink=True)

before = set(bpy.data.objects)
kitchen_hearth(coll, m, -5.8, -4.6, 11.7, 12.6, F, F + 0.61, (-5.2, 12.08))
palm_leaf_manuscripts(coll, m, 5.02, 17.2, F + 0.765)
created = set(bpy.data.objects) - before
bpy.context.view_layer.update()

for name, (matrix, data) in unchanged.items():
    obj = bpy.data.objects[name]
    assert obj.matrix_world == matrix and obj.data == data, f"Unrelated art changed: {name}"
for obj in created:
    assert obj.type == "MESH"
    assert all(c == c for v in obj.data.vertices for c in v.co), f"NaN in {obj.name}"
# The pot's base must rest on the stones, and nothing may reach the patrol path.
stones = [bpy.data.objects[f"hearth_stone_{k}"] for k in range(3)]
for s in stones:
    top = max((s.matrix_world @ v.co).z for v in s.data.vertices)
    assert abs(top - (F + 0.61)) < 0.002, f"{s.name} top {top:.4f}"
for obj in created:
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if obj.name.startswith(("kitchen_hearth", "hearth_")):
        assert min(p.x for p in pts) > -6.0 and max(p.x for p in pts) < -4.4, obj.name
        assert min(p.y for p in pts) > 11.0 and max(p.y for p in pts) < 12.75, obj.name
    else:
        assert min(p.z for p in pts) >= F + 0.764, f"{obj.name} sinks into the desk"
    print(f"PASS {obj.name}: {len(obj.data.polygons)} faces")

bpy.context.preferences.filepaths.save_version = 0
# Stage separately; apply-house-details.py installs these into the latest source.
bpy.ops.wm.save_as_mainfile(filepath="/tmp/interior-props-source.blend")
if "--" in sys.argv:
    output = sys.argv[sys.argv.index("--") + 1]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in created:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=output, export_format="GLB", use_selection=True,
                              export_extras=True, export_yup=True, export_apply=True,
                              export_cameras=False, export_lights=False)
    with open(output + ".json", "w") as stream:
        json.dump({"remove": old_names, "required": sorted(o.name for o in created)}, stream, indent=2)
print(f"PASS rebuilt {len(created)} interior props; preserved {len(unchanged)} unrelated objects")
