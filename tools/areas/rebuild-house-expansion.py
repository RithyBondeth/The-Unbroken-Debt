"""Focused pass: deepen the family house to 12 x 12 m without touching other village art.

The house grows north from y = 18 to y = 22 (a third bay of posts): Yay Mey's room
runs the full depth of the west side, Vuthy's room is new behind Sok's, the hall
(the family's living room) keeps the ancestral altar on the new back wall, and a
screened bathing corner stands under the back of the house by the rear stairs.
The back fence moves to y = 27 and the yard is cleared of growth only where the
house, its rear stairs and the new yard now stand.

blender -b art-source/blender/ep1/ep1_area_village.blend \
    -P tools/areas/rebuild-house-expansion.py -- art-export/ep1/house-expansion.glb
npm run assets -- ep1/house-expansion.glb
node tools/areas/update-house-expansion-glb.mjs public/assets/ep1/ep1_area_village.glb \
    public/assets/ep1/house-expansion.glb art-export/ep1/house-expansion.glb.json \
    public/assets/ep1/ep1_area_village.glb

Saves the patched village .blend in place. The focused public export is
intermediate and can be removed after merging.
"""
import ast
import json
import os
import re
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
source = os.path.join(os.path.dirname(__file__), 'ep1_area_village.py')
with open(source) as stream:
    tree = ast.parse(stream.read())
# Load builder definitions without executing its full-world factory reset.
tree.body = [node for node in tree.body if not (
    isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    and isinstance(node.value.func, ast.Name) and node.value.func.id == 'build')]
ns = {'__file__': source, '__name__': 'house_expansion'}
exec(compile(tree, source, 'exec'), ns)
coll = bpy.data.collections['ep1_area_village']
ns['AREA'] = coll
ns['rng'] = np.random.default_rng(1910)

fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'materials')
dictionary = next(n.value for n in fn.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict))
m = {}
ns['lib'], ns['img'] = ns['library_material'], ns['image_material']
for key, value in zip(dictionary.keys, dictionary.values):
    names = [a.value for a in value.args if isinstance(a, ast.Constant)
             and isinstance(a.value, str) and a.value.startswith('M_')]
    if names and names[0] in bpy.data.materials:
        m[key.value] = bpy.data.materials[names[0]]
    elif names:
        m[key.value] = eval(compile(ast.Expression(value), source, 'eval'), ns)

from house_decay import house_decay
from rural_detail import stairs_detail, material, bounds

DY = ns['ALTAR_DY']
assert DY == 4.0


def tree_of(obj):
    return [obj] + [d for c in obj.children for d in tree_of(c)]


def centre(obj):
    if obj.type != 'MESH' or not obj.data.vertices:
        return obj.matrix_world.translation.copy()
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return sum(bb, Vector()) / 8


top = [o for o in coll.all_objects if o.parent is None]
removed, moved = set(), set()


def drop(obj):
    for o in tree_of(obj):
        removed.add(o.name)
    for o in reversed(tree_of(obj)):
        bpy.data.objects.remove(o, do_unlink=True)


# 1. The house's own structure (house()), its weathering and the hall mat, rebuilt below.
#    The front stairs do not change and keep their close-view detail.
HOUSE = re.compile(r'^(col_)?(footing_|pillar_|girder_|joist_|floor_board_|upper_floor$|'
                   r'wall_(front|back|west|east|kitchen_hall|yaymey_hall|kitchen_yaymey|sok_hall)_\d+$|'
                   r'batten_(front|back|west|east)_|win_|door_frame_|door_head_|door_front_leaf|door_back_leaf|'
                   r'interact_door_(yaymey|sok)$|door_(yaymey|sok)$|door_sok_padlock$|veranda_|light_flame_veranda$|'
                   r'rail_|roof_|rafter_|purlin_|ridge_|tie_beam_|king_post_|gable|bargeboard_|barge_hook_|'
                   r'stairs_rear|hall_mat$|patrol_roamer_)')
for obj in top:
    name = obj.name
    if HOUSE.match(name) or (name.startswith('house_decay_') and not name.startswith('house_decay_stored_trap')):
        drop(obj)
    elif name.startswith('prop_Lantern_01') and (obj.location - Vector((-0.9, 10.7, ns['FLOOR'] + 1.7))).length < 0.01:
        drop(obj)  # the veranda lantern, placed by house()
    elif re.match(r'^(col_)?fence_[enw]_', name):
        drop(obj)

# 2. The altar and what stands round it move with the back wall; the rain jars and the
#    north eave's drip line move with the eave.
F = ns['FLOOR']
ALTAR = re.compile(r'^(interact_altar$|interact_kanha_drawing$|interact_incense_bundle$|interact_altar_candle$|'
                   r'interact_betel_tray$|col_offering_stand$|offering_stand$|marker_betel_tray$|light_flame_hall$|'
                   r'clock_shelf$|prop_mantel_clock_01$|family_(frame|print)_\d$|hall_altar_|hall_slathor$|hall_spittoon$|'
                   r'rain_jar_[01]$|col_rain_jar_[01]$|marker_eave_3_[ab]$)')
place_at = {'hall_spittoon': (0.8, 20.65), 'prop_wicker_basket_02.001': (-1.6, 21.45), 'prop_wicker_basket_02.002': (-2.05, 21.25)}
for obj in [o for o in coll.all_objects if o.parent is None]:
    if obj.name in place_at and obj.name.startswith('prop_'):
        assert abs(obj.location.z - F) < 0.01 and obj.location.y > 17, obj.name
    if ALTAR.match(obj.name) or obj.name in place_at:
        if obj.name in place_at:
            c = centre(obj)
            x, y = place_at[obj.name]
            obj.location += Vector((x - c.x, y - c.y, 0))
        else:
            obj.location.y += DY
        moved.update(o.name for o in tree_of(obj))
bpy.context.view_layer.update()

# 3. Clear growth where the deeper house, the rear stairs and their foot now stand.
REGIONS = [(-7.0, 7.0, 18.2, 23.2), (1.3, 3.4, 22.0, 26.4)]


def in_region(p, pad=0.0):
    return any(x0 - pad < p.x < x1 + pad and y0 - pad < p.y < y1 + pad for x0, x1, y0, y1 in REGIONS)


GROWTH = re.compile(r'(grass|sedge|understory|litter|moss|fern|shrub|pachira|root_cluster|dry_branches|banana)')
trimmed = set()
for obj in [o for o in coll.all_objects if o.parent is None]:
    if obj.name in removed or obj.name in moved or not GROWTH.search(obj.name):
        continue
    if obj.type == 'EMPTY':
        if in_region(obj.location):
            drop(obj)
        continue
    if obj.type != 'MESH':
        continue
    if obj.name.startswith('banana_'):
        bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        lo = Vector([min(p[i] for p in bb) for i in range(3)])
        hi = Vector([max(p[i] for p in bb) for i in range(3)])
        stem = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0))
        if in_region(stem, 0.8):
            drop(obj)
        continue
    # Joined clumps: drop each loose plant whose footprint centre falls in the cleared ground.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    world = obj.matrix_world
    seen, doomed = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        island, stack = [], [v]
        seen.add(v.index)
        while stack:
            u = stack.pop()
            island.append(u)
            for e in u.link_edges:
                w = e.other_vert(u)
                if w.index not in seen:
                    seen.add(w.index)
                    stack.append(w)
        c = world @ (sum((u.co for u in island), Vector()) / len(island))
        if in_region(c):
            doomed += island
    if doomed:
        if len(doomed) == len(bm.verts):
            bm.free()
            drop(obj)
            continue
        bmesh.ops.delete(bm, geom=doomed, context='VERTS')
        bm.to_mesh(obj.data)
        obj.data.update()
        trimmed.update(o.name for o in tree_of(obj))
    bm.free()

# 4. Build the new house, its rooms, the bathing corner and the fence.
before = set(bpy.data.objects)
ns['house'](m)
# The front flight keeps its existing close-view build.
for obj in [o for o in bpy.data.objects if o not in before and re.match(r'^(col_)?stairs_front', o.name)]:
    bpy.data.objects.remove(obj, do_unlink=True)
made = house_decay(coll, m)
# The rags and stored traps were already replaced by their close-view versions (rural_detail.py).
for obj in [o for o in made if o.name in ('house_decay_stored_traps', 'house_decay_mourning_rags')]:
    bpy.data.objects.remove(obj, do_unlink=True)
box, empty, collider = ns['box'], ns['empty'], ns['collider']
box('hall_mat', coll, -1.8, 1.8, 12.4, 18.6, F, F + 0.006, m['mat'])
collider('altar_ancestral', coll, -0.8, 0.8, 17.4 + DY, 17.92 + DY, F, F + 1.1)
ns['yaymey_room'](m)
ns['vuthy_room'](m)
ns['bathing_corner'](m)
for k, (x, y) in enumerate([(-6, 10), (6, 10), (6, 22), (-6, 22), (0, 16)]):
    empty(f'patrol_roamer_{k:02d}', coll, (x * 0.7, y + (0.6 if y == 10 else -0.6 if y == 22 else 0), 0))
Y = ns['YARD']
ns['bamboo_fence'](coll, m, 'fence_w', (Y['x0'], Y['y0']), (Y['x0'], Y['y1']))
ns['bamboo_fence'](coll, m, 'fence_e', (Y['x1'], Y['y0']), (Y['x1'], Y['y1']))
ns['bamboo_fence'](coll, m, 'fence_n', (Y['x0'], Y['y1']), (Y['x1'], Y['y1']))

# The close-view rural finish (rural_detail.py) for what house() made new: the rear
# flight with notched stringers, and the weathered stone footings.
for obj in [o for o in bpy.data.objects if o not in before and re.match(r'^stairs_rear_(tread|stringer|newel|rail)_', o.name)]:
    bpy.data.objects.remove(obj, do_unlink=True)
h = ns['HOUSE']
stairs_detail(coll, 'stairs_rear', 1.95, 2.75, h['y1'] + 3.0, h['y1'], 0, F, 11, 'y')
stone = material('clay_plaster', 'M_house_detail_weathered_footing', (.48, .43, .34))
for obj in [o for o in bpy.data.objects if o not in before and re.match(r'^footing_', o.name)]:
    name, spec = obj.name, bounds(obj)
    bpy.data.objects.remove(obj, do_unlink=True)
    foot = box(name, coll, *spec, stone, edge=.018)
    foot['support_kind'] = 'ground_footing'

created = [o for o in bpy.data.objects if o not in before]
bpy.context.view_layer.update()

# Checks: the new parts exist, the altar stands at the new back wall and nothing
# growing is left inside the house or on the rear stairs.
for obj in created:
    if obj.type == 'MESH':
        assert all(c == c for v in obj.data.vertices for c in v.co), obj.name
for name in ('wall_vuthy_hall_0', 'wall_sok_vuthy_0', 'door_vuthy_leaf', 'vuthy_table', 'yaymey_shelf', 'bath_jar',
             'pillar_6_22', 'girder_22', 'stairs_rear_detailed', 'fence_n_0_post_0'):
    assert name in bpy.data.objects, f'Missing: {name}'
for name in ('interact_altar', 'interact_betel_tray', 'marker_betel_tray'):
    assert abs(bpy.data.objects[name].location.y - 17.4 - DY) < 0.6, name
for obj in coll.all_objects:
    if obj.parent is None and obj.type == 'EMPTY' and GROWTH.search(obj.name):
        assert not in_region(obj.location), f'Growth left in the house: {obj.name}'

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

export = sorted({o.name for o in created} | moved | trimmed)
remove = sorted(removed | moved | trimmed)
if '--' in sys.argv:
    output = sys.argv[sys.argv.index('--') + 1]
    os.makedirs(os.path.dirname(output), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for name in export:
        bpy.data.objects[name].select_set(True)
    bpy.ops.export_scene.gltf(filepath=output, export_format='GLB', use_selection=True,
                              export_extras=True, export_yup=True, export_apply=True,
                              export_cameras=False, export_lights=False)
    with open(output + '.json', 'w') as stream:
        json.dump({'remove': remove, 'required': export}, stream, indent=2)
faces = sum(len(bpy.data.objects[n].data.polygons) for n in export if bpy.data.objects[n].type == 'MESH')
print(f'PASS house expansion: removed {len(removed)}, moved {len(moved)}, trimmed {len(trimmed)}, '
      f'created {len(created)} ({faces} faces exported)', flush=True)
