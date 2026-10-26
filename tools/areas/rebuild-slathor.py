"""Rebuild only the corrected sla thor; optionally export a focused replacement.

blender -b art-source/blender/ep1/ep1_area_village.blend \
  -P tools/areas/rebuild-slathor.py -- /tmp/slathor.glb
The adjacent manifest works with update-hall-altar-glb.mjs. Compress the focused
export with the regular KTX2/meshopt steps before merging into public/assets.
"""
import json
import os
import sys
import bpy
sys.path.insert(0,os.path.dirname(__file__))
from slathor import folded_offering
old=bpy.data.objects['hall_slathor'];coll=old.users_collection[0]
unchanged={o.name:(o.matrix_world.copy(),o.data) for o in bpy.data.objects if o!=old}
bpy.data.objects.remove(old,do_unlink=True)
for mesh in list(bpy.data.meshes):
    if mesh.users==0 and mesh.name.startswith(('hall_slathor','slathor_')):bpy.data.meshes.remove(mesh)
for mat in list(bpy.data.materials):
    if mat.name.startswith('M_hall_altar_slathor_') and mat.users==0:bpy.data.materials.remove(mat)
obj=folded_offering(coll,{ },2.5)
bpy.context.view_layer.update()
points=[obj.matrix_world@v.co for v in obj.data.vertices]
low=[min(v[i] for v in points) for i in range(3)];high=[max(v[i] for v in points) for i in range(3)]
assert abs(low[2]-3.6)<1e-5
assert high[2]-low[2]<.21,(low,high)
assert .085<high[0]-low[0]<.19,(low,high)
assert low[1]>17.4 and high[1]<17.63,(low,high)
assert obj['leaf_count']==3
cut_faces=[p for p in obj.data.polygons if obj.data.materials[p.material_index].name.startswith('M_hall_altar_slathor_cut')]
assert cut_faces and all(p.normal.z>.95 for p in cut_faces),'Cut stem must have a closed, upward-facing top'
for name,(matrix,data) in unchanged.items():
    other=bpy.data.objects[name]
    assert other.matrix_world==matrix and other.data==data,f'Unrelated art changed: {name}'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(f'PASS compact sla thor: bounds {low} to {high}; {len(obj.data.polygons)} faces; all {len(unchanged)} other objects unchanged')
if '--' in sys.argv:
    out=sys.argv[sys.argv.index('--')+1]
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=out,export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False)
    json.dump({'remove':['hall_slathor'],'required':['hall_slathor']},open(out+'.json','w'))
