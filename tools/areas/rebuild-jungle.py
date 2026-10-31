"""Old-growth jungle pass (31 October 2026): the forest round the village becomes
an enclosed, ancient lowland forest. Rebuilds every broadleaf giant (forest.py),
clears the banana plants out of the forest to the houses, yard and paddy bank,
leaves grass only in the clearings and lays a fern and litter floor under the
canopy. Preserves all props, sacred cloth, gameplay nodes and other colliders.

blender -b art-source/blender/ep1/ep1_area_village.blend \
    -P tools/areas/rebuild-jungle.py -- art-export/ep1/forest-detail.glb
npm run assets -- ep1/forest-detail.glb
node tools/areas/update-forest-glb.mjs public/assets/ep1/ep1_area_village.glb \
    public/assets/ep1/forest-detail.glb art-export/ep1/forest-detail.glb.json \
    public/assets/ep1/ep1_area_village.glb

The focused public export is intermediate and can be removed after merging.
"""
import ast
import json
import math
import os
import re
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from forest import tropical_tree, banyan, grass_patch
from forest_detail import forest_materials, understory

source = os.path.join(os.path.dirname(__file__), 'ep1_area_village.py')
with open(source) as stream:
    tree = ast.parse(stream.read())
tree.body = [node for node in tree.body if not (
    isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    and isinstance(node.value.func, ast.Name) and node.value.func.id == 'build')]
ns = {'__file__': source, '__name__': 'forest_rebuild'}
exec(compile(tree, source, 'exec'), ns)
coll = bpy.data.collections['ep1_area_village']
ns['AREA'] = coll
ns['rng'] = np.random.default_rng(6241910)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'materials')
dictionary = next(n.value for n in fn.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict))
m = {}
for key, value in zip(dictionary.keys, dictionary.values):
    names = [a.value for a in value.args if isinstance(a, ast.Constant)
             and isinstance(a.value, str) and a.value.startswith('M_')]
    if names and names[0] in bpy.data.materials:
        m[key.value] = bpy.data.materials[names[0]]

# Locate old trees through their preserved foot colliders, including the far bank.
specs = []
for obj in coll.objects:
    if not re.fullmatch(r'tree_\d+', obj.name):
        continue
    k = int(obj.name.split('_')[1])
    if k >= 600:
        continue  # additional trees are deterministically regenerated below
    foot = bpy.data.objects['col_' + obj.name].location
    height = max((obj.matrix_world @ v.co).z for v in obj.data.vertices)
    # Store the intended height for idempotent future rebuilds.
    height = float(obj.get('forest_height', min(17., max(10., height * .92))))
    specs.append((k, foot.x, foot.y, height))

prefixes = ('grove_grass', 'forest_grass', 'yard_edge_grass', 'road_grass', 'house_forest_',
            'paddy_stubble', 'forest_understory_', 'forest_litter_', 'forest_edge_sedge_',
            'jungle_understory_', 'jungle_litter_')
in_yard = ns['in_yard']


def kampong(x, y):
    """Where banana plants belong: round the houses and yard, and along the paddy bank."""
    return in_yard(x, y, 8) or y < -84


def foot(obj):
    """A joined plant's origin is not its foot: the centre of its lowest vertices is."""
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    low = min(p.z for p in points)
    base = [p for p in points if p.z < low + 0.3]
    return sum(p.x for p in base) / len(base), sum(p.y for p in base) / len(base)


bananas = [o for o in coll.objects if re.fullmatch(r'banana_\d+', o.name)]
cleared = [o for o in bananas if not kampong(*foot(o))]
remove = {o for o in coll.objects if o.name.startswith(prefixes)
          or re.fullmatch(r'tree_\d+', o.name) or o.name == 'banyan'
          or re.fullmatch(r'col_tree_[67]\d\d', o.name)} | set(cleared)
floor_spots = [foot(o) for o in cleared]
print(f'Clearing {len(cleared)} of {len(bananas)} banana plants from the forest', flush=True)
old_names = sorted(o.name for o in remove)
def props(obj):
    """Custom properties as plain values: ID property arrays never compare equal as read."""
    return {k: v.to_list() if hasattr(v, 'to_list') else v.to_dict() if hasattr(v, 'to_dict') else v
            for k, v in obj.items()}


untouched = {o.name: (o.matrix_world.copy(), o.data, props(o))
             for o in bpy.data.objects if o not in remove}
for obj in remove:
    bpy.data.objects.remove(obj, do_unlink=True)
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
# The night palette is new: every forest surface is regenerated, never reused.
for material in list(bpy.data.materials):
    if material.name.startswith('M_forest_'):
        assert material.users == 0, f'{material.name} still used'
        bpy.data.materials.remove(material)
for image in list(bpy.data.images):
    if image.name.startswith('T_ep1_forest_'):
        bpy.data.images.remove(image)
forest_materials()
before = set(bpy.data.objects)
for k, x, y, height in sorted(specs):
    obj = tropical_tree(coll, m, x, y, height, k, np.random.default_rng(6241910+k), collision=False)
    obj['forest_height'] = height
print(f'Rebuilt {len(specs)} broadleaf trees', flush=True)
banyan(coll, m, *ns['BANYAN'], np.random.default_rng(6241940), dressing=False)

land, path_distance, clear_of = (ns[key] for key in ('land', 'path_distance', 'clear_of'))
scatter = ns['scatter']
rng = np.random.default_rng(6241950)


def clearing(x, y):
    """Grass grows only where light reaches the ground: the trodden verges, the yard's
    surroundings and the open bank above the road; under the old canopy, ferns."""
    return path_distance(x, y) < 5.5 or in_yard(x, y, 5) or y < -57


floor_rng = np.random.default_rng(6242150)


def sow(n, test, spacing=0.0, tries=60000):
    """Like the village's scatter, on this pass's own random stream, so the trees the
    village script places afterwards land exactly where they did before."""
    spots = []
    for _ in range(tries):
        if len(spots) >= n:
            break
        x, y = floor_rng.uniform(-39.5, 39.5), floor_rng.uniform(-91.5, 39.5)
        if test(x, y) and all((x - a) ** 2 + (y - b) ** 2 >= spacing ** 2 for a, b in spots):
            spots.append((x, y))
    return spots


spots = [(x, y, 0.) for x, y in scatter(6500, lambda x, y: land(x, y, -.6), tries=60000)
         if clearing(x, y)]
grass_patch('forest_grass', coll, m, spots, rng, size=(.4, .95))
edge = []
for _ in range(12000):
    x, y = rng.uniform(-16, 16), rng.uniform(-60, -4)
    if 1.65 < path_distance(x, y) < 4.6 and clear_of(x, y):
        edge.append((x, y, 0.))
        if len(edge) >= 520:
            break
grass_patch('grove_grass', coll, m, edge, rng, size=(.35, .85))
# Ferns and litter where the bananas stood, and in drifts under the giants near the walk.
floor = [(x, y) for x, y in floor_spots if land(x, y, .2)]
for x, y in sow(520, lambda x, y: land(x, y, .4) and not clearing(x, y) and path_distance(x, y) < 22,
                spacing=1.6):
    floor.append((x, y))
understory(coll, floor, floor_rng, prefix='jungle')
yard = [(x, y, 0.) for x, y in scatter(400, lambda x, y: in_yard(x, y) and not in_yard(x, y, -1.2))]
grass_patch('yard_edge_grass', coll, m, yard, rng, size=(.2, .45))
# Road/paddy tufts retain their previous footprints, sampled from the road rules.
road = []
for _ in range(1200):
    x, y = rng.uniform(-38, 38), rng.uniform(-67, -60.8)
    if abs(y - ns['ROAD_Y']) > 1.8:
        road.append((x, y, -.03))
grass_patch('road_grass', coll, m, road, rng, size=(.25, .65))
stubble = [(rng.uniform(-38, 38), rng.uniform(-85, -68), -.09) for _ in range(600)]
grass_patch('paddy_stubble', coll, m, stubble, rng, size=(.2, .45))
ns['forest_enrichment'](m)

bpy.context.view_layer.update()
changed = []
for name, (matrix, data, kept) in untouched.items():
    obj = bpy.data.objects.get(name)
    if not (obj and obj.matrix_world == matrix and obj.data == data and props(obj) == kept):
        changed.append((name, obj is None, obj is not None and obj.matrix_world != matrix,
                        obj is not None and obj.data != data,
                        obj is not None and props(obj) != kept,
                        obj.parent.name if obj is not None and obj.parent else None))
for row in changed[:20]:
    print('CHANGED', row, flush=True)
assert not changed, f'{len(changed)} unrelated objects changed'
created = set(coll.objects) - before
required = ['marker_neakta', 'banyan_cloth', 'interact_thread', 'coffin_body', 'coffin_lid',
            'neakta_shrine', 'spirit_house']
for name in required:
    assert bpy.data.objects.get(name), f'Missing gameplay node: {name}'
# New colliders and trunk centres stay well outside the worn path and courtyard.
for obj in created:
    if re.fullmatch(r'col_tree_[67]\d\d', obj.name):
        assert path_distance(obj.location.x, obj.location.y) > 3.5, obj.name
        assert not in_yard(obj.location.x, obj.location.y, 2), obj.name
faces = sum(len(o.data.polygons) for o in created if o.type == 'MESH')
assert faces < 1700000, f'Forest detail budget exceeded: {faces} faces'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(f'Forest: {len(created)} nodes, {faces} faces; preserved {len(untouched)} unrelated objects.', flush=True)
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
                   'treeColliders': sorted(o.name for o in created if re.fullmatch(r'col_tree_[67]\d\d', o.name)),
                   'required': required}, stream, indent=2)
    print(f'Focused export: {destination}', flush=True)
