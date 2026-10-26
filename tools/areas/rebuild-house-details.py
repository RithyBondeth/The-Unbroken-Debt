"""Focused house finish update, preserving all unrelated art and gameplay nodes.

blender -b art-source/blender/ep1/ep1_area_village.blend \
  -P tools/areas/rebuild-house-details.py -- /tmp/house-details.glb
Then compress the focused export and merge with update-house-details-glb.mjs.
"""
import json
import os
import re
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
from house_detail import board_panel, corner_web, gathered_hammock

coll = bpy.data.collections['ep1_area_village']
walls = [o for o in coll.objects if re.match(r'^wall_(front|back|west|east|kitchen_hall|yaymey_hall|kitchen_yaymey|sok_hall)_\d+$', o.name)]
webs = [o for o in coll.objects if re.match(r'^(house|tent)_web_\d+$', o.name)]
hammock = [o for o in coll.objects if o.name == 'hammock' or o.name.startswith('hammock_rope_')]
assert walls and len(webs) == 9 and hammock
webs_only = '--webs-only' in sys.argv
if webs_only:
    walls, hammock = [], []
remove = walls+webs+hammock
old_names = [o.name for o in remove]
unchanged = {o.name:(o.matrix_world.copy(),o.data) for o in bpy.data.objects if o not in remove}
wall_specs = []
for obj in walls:
    pts = [obj.matrix_world@v.co for v in obj.data.vertices]
    bounds = [f(p[i] for p in pts) for i in range(3) for f in (min,max)]
    wall_specs.append((obj.name,bounds,bpy.data.materials['M_house_boards']))
web_specs=[]
for obj in webs:
    if 'web_corner' in obj:
        corner,right,down = [tuple(obj[k]) for k in ('web_corner','web_right','web_down')]
    else:
        pts=[obj.matrix_world@v.co for v in obj.data.vertices]
        corner,right,down = tuple(pts[0]),tuple(pts[1]-pts[0]),tuple(pts[3]-pts[0])
    web_specs.append((obj.name,corner,right,down))
for obj in remove:
    bpy.data.objects.remove(obj,do_unlink=True)
before = set(bpy.data.objects)
for name,bounds,mat in wall_specs:
    board_panel(name,coll,*bounds,mat)
    print(f'Rebuilt boards: {name}',flush=True)
for name,corner,right,down in web_specs:
    obj=corner_web(name,coll,corner,right,down,1)
    print(f'Rebuilt silk: {name}',flush=True)
if not webs_only:
    gathered_hammock(coll, {'cotton':bpy.data.materials['M_tent_cotton'], 'rope':bpy.data.materials['M_rope']})
created = set(bpy.data.objects)-before
bpy.context.view_layer.update()
for name,(matrix,data) in unchanged.items():
    obj=bpy.data.objects[name]
    assert obj.matrix_world == matrix and obj.data == data, f'Unrelated art changed: {name}'
for obj in created:
    assert obj.type == 'MESH'
    assert all(all(math_value == math_value for math_value in v.co) for v in obj.data.vertices)
    print(f'PASS {obj.name}: {len(obj.data.polygons)} faces')
body=bpy.data.objects['hammock']
pts=[body.matrix_world@v.co for v in body.data.vertices]
assert min(p.z for p in pts) > .6
assert max(p.x for p in pts) < -5.5, 'Hammock intrudes into the patrol path'
assert min(p.y for p in pts) > 9.8 and max(p.y for p in pts) < 14.2
bpy.context.preferences.filepaths.save_version=0
# Stage separately: other art tasks may save the shared village during a rebuild.
# Install only these objects into the latest source with apply-house-details.py.
bpy.ops.wm.save_as_mainfile(filepath='/tmp/house-details-source.blend')
if '--' in sys.argv:
    output=sys.argv[sys.argv.index('--')+1]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in created: obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=output,export_format='GLB',use_selection=True,
                              export_extras=True,export_yup=True,export_apply=True,
                              export_cameras=False,export_lights=False)
    with open(output+'.json','w') as stream:
        json.dump({'remove':old_names,'required':sorted(o.name for o in created)},stream,indent=2)
print(f'PASS rebuilt {len(created)} house details; preserved {len(unchanged)} unrelated objects')
