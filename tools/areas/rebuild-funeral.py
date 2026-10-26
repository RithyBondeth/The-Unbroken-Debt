"""Rebuild only the funeral ensemble in the existing authored village.

blender -b art-source/blender/ep1/ep1_area_village.blend \
    -P tools/areas/rebuild-funeral.py -- /tmp/funeral.glb

The adjacent JSON manifest is consumed by update-funeral-glb.mjs. The rest of
the current .blend, including work from other art passes, is preserved.
"""
import ast
import json
import os
import re
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
source = os.path.join(os.path.dirname(__file__), 'ep1_area_village.py')
with open(source) as stream:
    tree = ast.parse(stream.read())
# Load builder definitions without executing its full-world factory reset.
tree.body = [node for node in tree.body if not (
    isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    and isinstance(node.value.func, ast.Name) and node.value.func.id == 'build')]
ns = {'__file__': source, '__name__': 'funeral_rebuild'}
exec(compile(tree, source, 'exec'), ns)
coll = bpy.data.collections['ep1_area_village']
ns['AREA'] = coll
ns['rng'] = np.random.default_rng(1910)

fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'materials')
dictionary = next(n.value for n in fn.body if isinstance(n, ast.Assign)
                  and isinstance(n.value, ast.Dict))
m = {}
ns['lib'], ns['img'] = ns['library_material'], ns['image_material']
for key, value in zip(dictionary.keys, dictionary.values):
    names = [a.value for a in value.args if isinstance(a, ast.Constant)
             and isinstance(a.value, str) and a.value.startswith('M_')]
    if names and names[0] in bpy.data.materials:
        m[key.value] = bpy.data.materials[names[0]]
    elif names:
        # Materials the saved scene no longer holds (pruned when unused) are made
        # again from the builder's own definition.
        m[key.value] = eval(compile(ast.Expression(value), source, 'eval'), ns)

prefixes = ('tent_', 'dais', 'coffin_', 'portrait_', 'altar_', 'monk_',
            'incense_burner_', 'main_burner', 'skor_', 'flag_pole',
            'flag_crossbar', 'crocodile_flag', 'flag_guy', 'umbrella_',
            'betel_pot_', 'tea_cup_', 'folded_cloth_', 'scattered_petals',
            'scattered_rice', 'candle_stub_', 'footprints_', 'streamer_',
            'banner_', 'baysei_', 'step_candle_', 'step_lotus_',
            'lantern_flame_', 'lantern_cord_', 'water_jar_', 'funeral_',
            'light_flame_tent_', 'light_flame_altar_', 'light_flame_coffin',
            'marker_eave_0_', 'marker_eave_1_')
exact = {'betel_tray', 'betel_box', 'teapot', 'teapot_lid', 'teapot_spout',
         'teapot_handle', 'tea_spill', 'bangskol_cord', 'oil_tent',
         'interact_thread', 'interact_portrait', 'interact_oil_tent',
         'marker_main_burner', 'marker_yay_mey', 'marker_vuthy',
         'marker_lightning', 'marker_flies_tent', 'coffin', 'skor'}

def owns(obj):
    name = obj.name.removeprefix('col_')
    if name.startswith('tent_web_'):
        return False  # the house finish pass owns the silk cobwebs (rebuild-house-details.py)
    if name.startswith(prefixes) or name in exact:
        return True
    if re.fullmatch(r'(interact_incense_[0-3]|thread_[0-3]|sandal_\d+.*)', name):
        # Other rooms reuse these names with Blender suffixes; select by location.
        if name.startswith('sandal_'):
            return -3 < obj.location.x < 3 and 0 < obj.location.y < 1.2
        return True
    if obj.name.startswith('prop_') and obj.parent is None:
        x, y, _ = obj.location
        return -5.5 <= x <= 5.5 and 1 <= y <= 7.5
    return False

remove = {obj for obj in coll.objects if owns(obj)}
for obj in list(remove):
    remove.update(obj.children_recursive)
old_names = sorted(obj.name for obj in remove)
unchanged = {obj.name: (obj.matrix_world.copy(), obj.data)
             for obj in bpy.data.objects if obj not in remove}
required = ['interact_thread', 'interact_portrait', 'interact_oil_tent',
            'marker_main_burner', 'marker_yay_mey', 'marker_vuthy',
            'marker_lightning', 'marker_flies_tent', 'coffin_body', 'coffin_lid']
required += [f'interact_incense_{i}' for i in range(4)]
required += [f'altar_candle_{i}_flame' for i in range(2)]
anchors = {name: bpy.data.objects[name].matrix_world.translation.copy()
           for name in required if name.startswith(('interact_incense_', 'marker_', 'interact_oil_'))}
for obj in remove:
    bpy.data.objects.remove(obj, do_unlink=True)

# Remove orphaned old funeral materials before rebuilding to keep stable names.
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
for mat in list(bpy.data.materials):
    if mat.name.startswith('M_funeral_') and mat.users == 0:
        bpy.data.materials.remove(mat)
before = set(bpy.data.objects)
print(f'Rebuilding {len(old_names)} funeral nodes', flush=True)
ns['funeral'](m)
ns['funeral_details'](m)
created = {obj for obj in coll.objects if obj not in before}
# funeral_details() also draws the plain tent cobwebs; keep the finished silk ones.
for obj in [o for o in created if re.fullmatch(r'tent_web_\d+\.\d+', o.name)]:
    created.discard(obj)
    bpy.data.objects.remove(obj, do_unlink=True)
# Imported library copies need funeral-specific IDs; other rooms use the same props.
prop_roots = sorted((o for o in created if o.name.startswith('prop_')), key=lambda o: o.name)
for i, root in enumerate(prop_roots):
    for j, obj in enumerate([root] + list(root.children_recursive)):
        obj.name = f'funeral_prop_{i:02d}_{j:02d}'
bpy.context.view_layer.update()
for name, (matrix, data) in unchanged.items():
    obj = bpy.data.objects.get(name)
    assert obj and obj.matrix_world == matrix and obj.data == data, f'Unrelated art changed: {name}'
for name in required:
    assert bpy.data.objects.get(name), f'Missing gameplay node: {name}'
for name, point in anchors.items():
    assert (bpy.data.objects[name].matrix_world.translation-point).length < .001, f'Anchor moved: {name}'
assert bpy.data.objects['coffin_body']['hollow']
assert bpy.data.objects['interact_portrait']['action'] == 'examine'
slats=bpy.data.objects['tent_floor_visible_slats']
assert max((slats.matrix_world @ v.co).z for v in slats.data.vertices) < .056, 'Slats cover the seating mats'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(f'Funeral rebuilt: {len(created)} nodes; {len(unchanged)} unrelated objects preserved.', flush=True)

if '--' in sys.argv:
    destination = sys.argv[sys.argv.index('--') + 1]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in created:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=destination, export_format='GLB', use_selection=True,
                             export_extras=True, export_yup=True, export_apply=True,
                             export_cameras=False, export_lights=False)
    with open(destination + '.json', 'w') as stream:
        json.dump({'remove': old_names, 'required': required,
                   'created': sorted(obj.name for obj in created)}, stream, indent=2)
    print(f'Focused export: {destination}', flush=True)
