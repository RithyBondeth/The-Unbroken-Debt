"""Add/refresh only the forest belt round the house in the current village.

blender -b art-source/blender/ep1/ep1_area_village.blend \
    -P tools/areas/rebuild-house-forest.py -- art-export/ep1/house-forest.glb
npm run assets -- ep1/house-forest.glb
node tools/areas/update-forest-glb.mjs public/assets/ep1/ep1_area_village.glb \
    public/assets/ep1/house-forest.glb art-export/ep1/house-forest.glb.json \
    public/assets/ep1/ep1_area_village.glb
"""
import ast
import json
import os
import re
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
source = os.path.join(os.path.dirname(__file__), 'ep1_area_village.py')
with open(source) as stream:
    tree = ast.parse(stream.read())
tree.body = [node for node in tree.body if not (
    isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    and isinstance(node.value.func, ast.Name) and node.value.func.id == 'build')]
ns = {'__file__': source, '__name__': 'house_forest_rebuild'}
exec(compile(tree, source, 'exec'), ns)
coll = bpy.data.collections['ep1_area_village']
ns['AREA'] = coll
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'materials')
dictionary = next(n.value for n in fn.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict))
m = {}
for key, value in zip(dictionary.keys, dictionary.values):
    names = [a.value for a in value.args if isinstance(a, ast.Constant)
             and isinstance(a.value, str) and a.value.startswith('M_')]
    if names and names[0] in bpy.data.materials:
        m[key.value] = bpy.data.materials[names[0]]

remove = {o for o in coll.objects if o.name.startswith('house_forest_')
          or re.fullmatch(r'(col_)?tree_7\d\d', o.name)}
old_names = sorted(o.name for o in remove)
untouched = {o.name: (o.matrix_world.copy(), o.data, dict(o.items()))
             for o in bpy.data.objects if o not in remove}
for obj in remove:
    bpy.data.objects.remove(obj, do_unlink=True)
before = set(bpy.data.objects)
ns['house_forest'](m)
bpy.context.view_layer.update()
created = set(coll.objects) - before
trunks = [o for o in created if re.fullmatch(r'col_tree_7\d\d', o.name)]
assert len(trunks) == 10
for obj in trunks:
    assert not ns['in_yard'](obj.location.x, obj.location.y, 2), obj.name
    assert ns['path_distance'](obj.location.x, obj.location.y) > 3.5, obj.name
for name, (matrix, data, props) in untouched.items():
    obj = bpy.data.objects.get(name)
    assert obj and obj.matrix_world == matrix and obj.data == data and dict(obj.items()) == props, name
required = ['interact_shed_door', 'coffin_body', 'banyan_cloth', 'tree_0']
assert all(bpy.data.objects.get(name) for name in required)
faces = sum(len(o.data.polygons) for o in created if o.type == 'MESH')
assert faces < 180000, f'House forest budget exceeded: {faces}'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(f'House forest: {len(created)} nodes, {faces} faces; preserved {len(untouched)} unrelated objects.', flush=True)
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
        json.dump({'remove': old_names, 'created': sorted(o.name for o in created),
                   'treeColliders': sorted(o.name for o in trunks), 'required': required,
                   'reuseForestMaterials': True}, stream, indent=2)
    print(f'Focused export: {destination}', flush=True)
