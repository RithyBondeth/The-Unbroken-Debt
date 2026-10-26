"""Rebuild shrine and verge offerings without regenerating other village art.

blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/rebuild-shrine.py
npm run export -- ep1/ep1_area_village
npm run assets -- ep1/ep1_area_village.glb

Append `-- /tmp/shrine.glb` to the Blender command for a focused export.
When textures are unchanged, update-shrine-glb.mjs copies that geometry into
an existing compressed village. Use the full pipeline for texture changes.
"""
import ast
import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from shrine import make_leaf_textures, ground_offering, tree_bindings
from forest import neak_ta_shrine

make_leaf_textures()
print("Leaf texture maps generated", flush=True)
# Resolve the full builder's existing materials by their stable authored names.
source = os.path.join(os.path.dirname(__file__), 'ep1_area_village.py')
with open(source) as stream:
    tree = ast.parse(stream.read())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'materials')
dictionary = next(n.value for n in fn.body if isinstance(n, ast.Assign)
                  and isinstance(n.value, ast.Dict))
m = {}
for key, value in zip(dictionary.keys, dictionary.values):
    names = [a.value for a in value.args if isinstance(a, ast.Constant)
             and isinstance(a.value, str) and a.value.startswith('M_')]
    if names and names[0] in bpy.data.materials:
        m[key.value] = bpy.data.materials[names[0]]
coll = bpy.data.objects['neakta_shrine'].users_collection[0]
remove = {'neakta_shrine', 'neakta_stone_watch', 'spirit_house', 'col_neakta_shrine',
          'col_spirit_house', 'light_flame_shrine', 'marker_neakta', 'marker_flies',
          'ground_offering_0', 'ground_offering_1', 'banyan_cloth'}
# Snapshot unrelated art so a focused rebuild cannot silently move it.
unchanged = {o.name: o.matrix_world.copy() for o in bpy.data.objects if o.name not in remove}
for name in remove:
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
# Joined source meshes may still own material slots after their objects are gone.
for mesh in list(bpy.data.meshes):
    if mesh.users == 0 and mesh.name.startswith(('neakta_', 'spirit_', 'offering_', 'ground_offering_')):
        bpy.data.meshes.remove(mesh)
for material in list(bpy.data.materials):
    if material.name.startswith('M_shrine_') and material.users == 0:
        bpy.data.materials.remove(material)
print("Rebuilding shrine", flush=True)
neak_ta_shrine(coll, m, -3.9, -34.9, math.pi/2, np.random.default_rng(3409))
tree_bindings(coll, m, bpy.data.objects['banyan'], -7.0, -35.5)
print("Rebuilding verge packets", flush=True)
# Use the authored placements; the packets remain beyond the path edge.
placements = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Name) and n.func.id == 'ground_offering']
for call in placements:
    x,y,k = [ast.literal_eval(arg) for arg in call.args[2:5]]
    ground_offering(coll,m,x,y,k,np.random.default_rng(1910+k))
bpy.context.view_layer.update()
for name, matrix in unchanged.items():
    assert bpy.data.objects[name].matrix_world == matrix, f'Unrelated art moved: {name}'
assert abs(bpy.data.objects['neakta_stone_watch']['front']) < .001
for name in remove:
    assert bpy.data.objects.get(name), f'Missing gameplay node: {name}'
path = ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id == 'PATH' for t in n.targets)))
def path_distance(x, y):
    nearest = math.inf
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        dx, dy = bx-ax, by-ay
        t = max(0, min(1, ((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
        nearest = min(nearest, math.hypot(x-ax-dx*t, y-ay-dy*t))
    return nearest
for k in range(2):
    obj = bpy.data.objects[f'ground_offering_{k}']
    clearance = min(path_distance(*(obj.matrix_world @ v.co)[:2]) for v in obj.data.vertices)
    assert clearance > 1.7, f'{obj.name} intrudes into the mud path: {clearance}'
for name in ('ground_offering_0','ground_offering_1','neakta_shrine','spirit_house'):
    obj=bpy.data.objects[name]
    assert len(obj.data.polygons)>500
    print(f'{name}: {len(obj.data.polygons)} faces, {len(obj.data.materials)} material slots')
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Shrine rebuilt; unrelated art transforms and gameplay nodes verified.')

# Optional focused export for copying only these updated meshes into the game asset.
if '--' in sys.argv:
    destination = sys.argv[sys.argv.index('--') + 1]
    bpy.ops.object.select_all(action='DESELECT')
    for name in remove:
        bpy.data.objects[name].select_set(True)
    bpy.ops.export_scene.gltf(filepath=destination, export_format='GLB', use_selection=True,
                              export_extras=True, export_yup=True, export_apply=True,
                              export_cameras=False, export_lights=False)
    print(f'Focused shrine export: {destination}')
