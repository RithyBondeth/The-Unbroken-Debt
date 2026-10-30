"""Stage only rural props and construction; preserve gameplay and unrelated art.

blender -b art-source/blender/ep1/ep1_area_village.blend \\
  -P tools/areas/rebuild-rural-details.py -- art-export/ep1/rural-details.glb
Then compress and merge with update-house-details-glb.mjs, and use
apply-house-details.py to install this staged source into the latest village.
"""
import json
import math
import os
import sys

import bpy
sys.path.insert(0,os.path.dirname(__file__))
from rural_detail import rural_details, bounds

coll=bpy.data.collections['ep1_area_village']
snapshot={o.name:(o.matrix_world.copy(),o.data) for o in bpy.data.objects}
old_names,created=rural_details(coll)
changed=set(old_names)|{o.name for o in created}
bpy.context.view_layer.update()
for name,(matrix,data) in snapshot.items():
    if name in changed: continue
    obj=bpy.data.objects[name]
    assert obj.matrix_world==matrix and obj.data==data, f'Unrelated art changed: {name}'
faces=sum(len(o.data.polygons) for o in created if o.type=='MESH')
assert faces<65000, f'Rural detail geometry budget exceeded: {faces}'
for obj in created:
    assert obj.type=='MESH',obj.name
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    print('DETAIL',obj.name,'faces',len(obj.data.polygons),'support',obj.get('support_kind'), 'bounds',bounds(obj),flush=True)
bpy.context.preferences.filepaths.save_version=0
stage='/tmp/rural-details-source.blend'
bpy.ops.wm.save_as_mainfile(filepath=stage)
output=sys.argv[sys.argv.index('--')+1]
os.makedirs(os.path.dirname(os.path.abspath(output)),exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
for obj in created: obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=output,export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False)
with open(output+'.json','w') as stream:
    json.dump({'remove':old_names,'required':sorted(o.name for o in created)},stream,indent=2)
print(f'PASS {len(created)} detailed objects, {faces} faces; all gameplay nodes and unrelated art preserved',flush=True)
