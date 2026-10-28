"""Update only Sok's packed photograph in an existing village source scene.
blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/update-sok-photo.py
"""
from pathlib import Path
import bpy

path = Path.cwd() / "art-source/textures/ep1/T_ep1_photo_sok_BC.png"
images = [image for image in bpy.data.images if image.name.startswith("T_ep1_photo_sok_BC")]
assert images, "Sok photograph missing from village source"
for image in images:
    image.filepath = str(path)
    image.source = "FILE"
    image.reload()
    image.pack()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("Updated Sok photograph only:", [image.name for image in images])
