"""Exports Episode 1's studio (the shophouse floor) for the Unreal Engine 5 test room.

Unreal lights the room itself (Lumen), so the Babylon bake is dropped: the `_LM`
lightmap materials go back to their originals, the collision proxies (`col_*`) and
objects hidden from render are left out, and the bake lights are written to a JSON
file that tools/ue5/build_test_room.py turns into Unreal lights.
Run:
    blender -b art-source/blender/ep1/ep1_area_studio.blend -P tools/ue5/export_studio_for_ue.py
Output: ../UnbrokenDebtUE5/Import/studio.glb and studio_lights.json
Blender axes: X east, Y north, Z up, metres.
"""

import json
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(os.path.dirname(ROOT), "UnbrokenDebtUE5", "Import")
os.makedirs(OUT, exist_ok=True)

mats = bpy.data.materials
for o in bpy.context.scene.objects:
    if o.type != "MESH":
        continue
    for slot in o.material_slots:
        m = slot.material
        if m and m.name.endswith("_LM") and mats.get(m.name[:-3]):
            slot.material = mats[m.name[:-3]]

lights = []
for o in bpy.context.scene.objects:
    if o.type == "LIGHT":
        lights.append({
            "name": o.name.replace("bake_", ""),
            "location_m": list(o.matrix_world.translation),
            "watts": o.data.energy,
            "color": list(o.data.color),
            "radius_m": getattr(o.data, "shadow_soft_size", 0.05),
        })
json.dump(lights, open(os.path.join(OUT, "studio_lights.json"), "w"), indent=2)

bpy.ops.object.select_all(action="DESELECT")
n = 0
for o in bpy.context.scene.objects:
    keep = (o.type == "MESH" and not o.name.startswith("col_") and not o.hide_render
            and o.visible_get())
    o.select_set(keep)
    n += keep
print("UE export:", n, "meshes,", len(lights), "lights")

bpy.ops.export_scene.gltf(
    filepath=os.path.join(OUT, "studio.glb"),
    use_selection=True,
    export_format="GLB",
    export_apply=True,
    export_yup=True,
    export_lights=False,
    export_cameras=False,
    export_image_format="AUTO",
)
