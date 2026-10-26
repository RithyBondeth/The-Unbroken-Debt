"""Add/refresh only the house's weathering (house_decay.py) in the current village.

blender -b art-source/blender/ep1/ep1_area_village.blend \
    -P tools/areas/rebuild-house-decay.py -- art-export/ep1/house-decay.glb
npm run assets -- ep1/house-decay.glb
node tools/areas/update-house-details-glb.mjs public/assets/ep1/ep1_area_village.glb \
    public/assets/ep1/house-decay.glb art-export/ep1/house-decay.glb.json \
    public/assets/ep1/ep1_area_village.glb

Everything it makes is named house_decay_* and nothing collides, so gameplay and
the hunt's navigation under the house are untouched.
"""
import ast
import json
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
source = os.path.join(os.path.dirname(__file__), 'ep1_area_village.py')
with open(source) as stream:
    tree = ast.parse(stream.read())
tree.body = [node for node in tree.body if not (
    isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    and isinstance(node.value.func, ast.Name) and node.value.func.id == 'build')]
ns = {'__file__': source, '__name__': 'house_decay_rebuild'}
exec(compile(tree, source, 'exec'), ns)
coll = bpy.data.collections['ep1_area_village']
ns['AREA'] = coll
ns['lib'], ns['img'] = ns['library_material'], ns['image_material']
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'materials')
dictionary = next(n.value for n in fn.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict))
m = {}
for key, value in zip(dictionary.keys, dictionary.values):
    if key.value not in ('post', 'tiles', 'rope'):
        continue
    names = [a.value for a in value.args if isinstance(a, ast.Constant)
             and isinstance(a.value, str) and a.value.startswith('M_')]
    m[key.value] = bpy.data.materials.get(names[0]) or eval(compile(ast.Expression(value), source, 'eval'), ns)

from house_decay import house_decay

remove = {o for o in coll.objects if o.name.startswith('house_decay_')}
old_names = sorted(o.name for o in remove)
untouched = {o.name: (o.matrix_world.copy(), o.data) for o in bpy.data.objects if o not in remove}
for obj in remove:
    bpy.data.objects.remove(obj, do_unlink=True)
# This pass's own materials (and the stain atlas) are made afresh every time; the
# dusty silk is shared with the house finish pass and stays.
OWN = ('weather_stains', 'moss', 'lichen', 'wasp_paper', 'termite_mud', 'thorn_wood',
       'mourning_rag', 'roof_void', 'old_cane')
for material in list(bpy.data.materials):
    if material.name.split('.')[0] in {f'M_house_detail_{k}' for k in OWN}:
        bpy.data.materials.remove(material, do_unlink=True)
created = house_decay(coll, m)
bpy.context.view_layer.update()
for name, (matrix, data) in untouched.items():
    obj = bpy.data.objects.get(name)
    assert obj and obj.matrix_world == matrix and obj.data == data, f'Unrelated art changed: {name}'
for obj in created:
    assert obj.name.startswith('house_decay_'), obj.name
    assert obj.type == 'MESH' and not obj.name.startswith('col_')
faces = sum(len(o.data.polygons) for o in created)
assert faces < 120000, f'House decay budget exceeded: {faces}'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(f'House decay: {len(created)} nodes, {faces} faces; preserved {len(untouched)} objects.', flush=True)
if '--' in sys.argv:
    destination = sys.argv[sys.argv.index('--') + 1]
    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in created:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=destination, export_format='GLB', use_selection=True,
                             export_extras=True, export_yup=True, export_apply=True,
                             export_cameras=False, export_lights=False)
    with open(destination + '.json', 'w') as stream:
        json.dump({'remove': old_names, 'required': sorted(o.name for o in created)}, stream, indent=2)
    print(f'Focused export: {destination}', flush=True)
