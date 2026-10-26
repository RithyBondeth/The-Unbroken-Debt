"""Apply staged house objects to the latest shared village without replacing other art.

blender -b art-source/blender/ep1/ep1_area_village.blend \
  -P tools/areas/apply-house-details.py -- /tmp/house-details-source.blend /tmp/house-details.glb.json
"""
import json
import os
import sys
import bpy

source, manifest_path = sys.argv[sys.argv.index('--')+1:]
with open(manifest_path) as stream:
    manifest = json.load(stream)
remove = set(manifest['remove']) | set(manifest['required'])
path = bpy.data.filepath
stamp = os.stat(path).st_mtime_ns
unchanged = {o.name:(o.matrix_world.copy(),o.data) for o in bpy.data.objects if o.name not in remove}
for name in remove:
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
with bpy.data.libraries.load(source,link=False) as (src,dst):
    assert set(manifest['required']) <= set(src.objects)
    dst.objects = manifest['required']
coll = bpy.data.collections['ep1_area_village']
for obj in dst.objects:
    coll.objects.link(obj)
    # Reuse original library surfaces rather than duplicate large texture trees.
    for slot in obj.material_slots:
        material=slot.material
        if not material or material.name.startswith('M_house_detail_'):
            continue
        base=material.name.rsplit('.',1)[0] if material.name[-3:].isdigit() else material.name
        if base in bpy.data.materials:
            slot.material=bpy.data.materials[base]
bpy.context.view_layer.update()
for name,(matrix,data) in unchanged.items():
    obj=bpy.data.objects[name]
    assert obj.matrix_world == matrix and obj.data == data, f'Unrelated art changed: {name}'
assert os.stat(path).st_mtime_ns == stamp, 'Village was edited during merge; rerun against the latest file'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=path)
print(f'PASS applied {len(dst.objects)} house objects; preserved {len(unchanged)} current village objects')
