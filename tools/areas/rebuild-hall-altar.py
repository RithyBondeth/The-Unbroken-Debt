"""Update only the upstairs altar; export a focused GLB and replacement manifest.

blender -b art-source/blender/ep1/ep1_area_village.blend \
  -P tools/areas/rebuild-hall-altar.py -- /tmp/hall-altar.glb
node tools/areas/update-hall-altar-glb.mjs village.glb /tmp/hall-altar.glb \
  /tmp/hall-altar.glb.json village.glb

For public/assets, first resize and KTX2/meshopt-compress the focused GLB using
the same steps as tools/build-assets.mjs. Merge the raw focused export only
into art-export; merging preserves compressed textures on unrelated objects.
"""
import ast
import json
import os
import sys
import bpy
sys.path.insert(0,os.path.dirname(__file__))
from hall_altar import build_hall_altar
from kit import collider

source=os.path.join(os.path.dirname(__file__),'ep1_area_village.py')
tree=ast.parse(open(source).read())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='materials')
dictionary=next(n.value for n in fn.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Dict))
m={}
for key,value in zip(dictionary.keys,dictionary.values):
    names=[a.value for a in value.args if isinstance(a,ast.Constant) and isinstance(a.value,str) and a.value.startswith('M_')]
    if names and names[0] in bpy.data.materials:m[key.value]=bpy.data.materials[names[0]]
coll=bpy.data.collections['ep1_area_village']
def owns(o):
    n=o.name
    if n=='interact_altar' or n=='altar_mesh' or n=='offering_stand':return True
    if n.startswith(('offering_stand_leg_','hall_altar_','hall_candle_','hall_lotus_','hall_incense_','hall_slathor')):return True
    if n.startswith('prop_') and not o.parent:
        x,y,z=o.location
        return abs(x)<=.6 and 17.7<y<17.9 and 3.9<z<4.05
    return False
remove={o for o in coll.objects if owns(o)}
for o in list(remove):remove.update(o.children_recursive)
old_names=sorted(o.name for o in remove)
unchanged={o.name:(o.matrix_world.copy(),o.data) for o in bpy.data.objects if o not in remove}
for o in remove:bpy.data.objects.remove(o,do_unlink=True)
for mesh in list(bpy.data.meshes):
    if mesh.users==0 and mesh.name.startswith(('hall_altar_','hall_slathor','offering_stand')):
        bpy.data.meshes.remove(mesh)
for mat in list(bpy.data.materials):
    if mat.name.startswith('M_hall_altar_') and mat.users==0:bpy.data.materials.remove(mat)
before=set(bpy.data.objects)
build_hall_altar(coll,m)
if 'col_altar_ancestral' not in bpy.data.objects:
    collider('altar_ancestral',coll,-.8,.8,17.4,17.92,2.5,3.6)
created={o for o in coll.objects if o not in before}
bpy.context.view_layer.update()
for name,(matrix,data) in unchanged.items():
    o=bpy.data.objects[name]
    assert o.matrix_world==matrix and o.data==data,f'Unrelated object changed: {name}'
root=bpy.data.objects['interact_altar']
assert root['action']=='place' and root['accepts']=='betel_tray'
assert tuple(round(v,3) for v in root.location)==(0,17.4,3.65)
for name in ('col_altar_ancestral','col_offering_stand','marker_betel_tray','interact_incense_bundle','interact_altar_candle','light_flame_hall'):
    assert name in unchanged or name in {o.name for o in created},f'Missing gameplay node: {name}'
for name,base in (('hall_altar_cabinet',2.5),('offering_stand',2.5),('hall_altar_brassware',3.95),('hall_slathor',3.6),('hall_altar_lamp',3.6)):
    o=bpy.data.objects[name];low=min((o.matrix_world@v.co).z for v in o.data.vertices)
    assert abs(low-base)<.001,(name,low,base)
    print(f'PASS {name}: {len(o.data.polygons)} faces; base {low:.4f}m')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
if '--' in sys.argv:
    output=sys.argv[sys.argv.index('--')+1]
    bpy.ops.object.select_all(action='DESELECT')
    for o in created:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=output,export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False)
    json.dump({'remove':old_names,'required':sorted(o.name for o in created)},open(output+'.json','w'),indent=2)
print(f'PASS rebuilt {len(created)} altar objects; preserved {len(unchanged)} unrelated objects and all gameplay anchors')
