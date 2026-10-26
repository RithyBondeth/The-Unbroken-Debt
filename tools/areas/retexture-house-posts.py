"""Re-surface the house's posts, beams and trim as weathered teak in the village.

blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/retexture-house-posts.py
node tools/areas/update-house-posts-glb.mjs public/assets/ep1/ep1_area_village.glb \
    public/assets/ep1/ep1_area_village.glb

The material keeps its name, so every object using it changes without being
re-exported; the shipped GLB borrows the weathered_planks maps it already holds.
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
from kit import library_material

old = bpy.data.materials['M_house_posts']
users = [o for o in bpy.data.objects if o.type == 'MESH' and any(s.material == old for s in o.material_slots)]
new = library_material('weathered_planks', 'M_house_posts_weathered', tint=(0.66, 0.6, 0.54))
old.user_remap(new)
bpy.data.materials.remove(old)
new.name = 'M_house_posts'
assert all(any(s.material == new for s in o.material_slots) for o in users)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(f'PASS re-surfaced M_house_posts on {len(users)} objects', flush=True)
