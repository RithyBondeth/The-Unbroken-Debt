"""Rooted flooded forest, supported period props and broken market shelter.

Coordinates are game X/Y-up/Z until Craft converts them to Blender. No story
root or collider is replaced. Support heights are explicit authoring constraints.
"""
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector
from kit import ROOT


def bounds(root):
    meshes = [o for o in [root, *root.children_recursive] if o.type == 'MESH']
    points = [o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
    if not points:
        return None
    return tuple(min(p[i] for p in points) for i in range(3)), tuple(max(p[i] for p in points) for i in range(3))


def drop(root):
    for obj in [*root.children_recursive, root]:
        bpy.data.objects.remove(obj, do_unlink=True)


def flooded_forest(c):
    rng = random.Random(192073)
    # Replace the handful of undersized, disconnected trees with an enclosing
    # forest. The boat channel and the complete roof route retain their clearance.
    for obj in [o for o in c.coll.objects if o.type == 'EMPTY' and o.name.startswith(('ep3_finish_flooded_tree', 'ep3_finish_horizon_tree', 'ep3_finish_drowned_snag', 'ep3_finish_submerged_roots'))]:
        drop(obj)
    sites = []
    for i in range(22):
        sites.append((rng.uniform(-94, -82), rng.uniform(-35, 30)))
        sites.append((rng.uniform(-44, -35), rng.uniform(-36, 5)))
    for i in range(17):
        sites.append((rng.uniform(-87, -41), rng.uniform(-47, -25)))
        sites.append((rng.uniform(-87, -44), rng.uniform(26, 43)))
    for i in range(19):
        sites.append((rng.uniform(19, 36), rng.uniform(-38, 30)))
        sites.append((rng.uniform(-32, 25), rng.uniform(-47, -33)))
    for i in range(12):
        sites.append((rng.uniform(-25, 22), rng.uniform(29, 43)))
    for i, (x, z) in enumerate(sites):
        # Sparse gaps avoid a pasted wall of identical crowns. Each scanned
        # variant is planted by its measured lowest point, below the floodline.
        if any(math.hypot(x-a, z-b) < 3.1 for a, b in sites[:i]):
            continue
        model = 'pachira_aquatica_01' if i % 3 else 'island_tree_02'
        scale = rng.uniform(.95, 1.6) if i % 3 else rng.uniform(2.4, 3.8)
        tree = c.prop(model, x, -1.15, z, scale, rng.uniform(0, 360), 'ep3_dread_forest_tree')
        tree['ep3_forest_tree'] = True
        if i % 2 == 0:
            c.prop('root_cluster_01', x, -.36, z, rng.uniform(.55, 1), rng.uniform(0, 360), 'ep3_dread_forest_roots')
        if i % 4 == 0:
            c.prop('dead_tree_trunk_02', x+.9, -.7, z+1.3, rng.uniform(.65, 1.1), rng.uniform(0, 360), 'ep3_dread_broken_trunk')
    # A second, lower-detail belt stops the near trees standing against a void.
    for i in range(54):
        angle = i * math.tau / 54
        x, z = -40 + math.cos(angle)*rng.uniform(77, 95), math.sin(angle)*rng.uniform(64, 81)
        c.prop('island_tree_02', x, -1.3, z, rng.uniform(2.2, 3.7), rng.uniform(0, 360), 'ep3_dread_far_forest')
    # Tangled reeds follow the shore, away from every walkable surface.
    for i in range(160):
        x, z = rng.choice(sites)
        x += rng.uniform(-2, 2)
        z += rng.uniform(-2, 2)
        for j in range(rng.randint(2, 4)):
            height = rng.uniform(.45, 1.6)
            c.pipe('ep3_dread_water_reed', [(x, -.24, z), (x+.06, height*.65, z+.04), (x+.18, height, z+.13)], .006, c.m['mould'], 5, end=.001)


def shelter(c):
    m = c.m
    # Low, broken cross-beams frame the market as an inhabited place under a
    # storm, with an open 2.1m head clearance above the raised walkway.
    for z in [-7, 2, 10]:
        for x in [-67.1, -60.9]:
            c.pipe('ep3_dread_market_arch_post', [(x, -1.4, z), (x+.025, 3.45, z)], .09, m['dark'], 10)
            for y in [.83, 2.88]:
                c.pipe('ep3_dread_arch_lashing', [(x+.11*math.cos(a), y+k*.002, z+.11*math.sin(a)) for k, a in enumerate([j*math.tau/16 for j in range(44)])], .006, m['rope'], 5)
        c.pipe('ep3_dread_market_arch_beam', [(-67.3, 3.35, z), (-64, 3.24, z+.04), (-60.7, 3.32, z)], .105, m['dark'], 10)
    # Torn side screens hang from those beams, not in the middle of the path.
    for x, z in [(-67.05, -7), (-60.95, 2), (-67.05, 10)]:
        def screen(u, v, x=x, z=z):
            return x+.05*math.sin(u*17+v*5), 3.25-v*(1.25+.13*math.sin(u*13)), z+(u-.5)*1.7
        c.grid('ep3_dread_market_rag_screen', 30, 28, screen, m['curtain'], lambda u, v: v>.7 and .31<u<.4)
        c.pipe('ep3_dread_screen_hanger', [(x, 3.29, z-.9), (x, 3.29, z+.9)], .025, m['wood'], 7)
    for x, z in [(-72,-5),(-56,-6),(-72,4),(-56,3),(-64,-13)]:
        c.pipe('ep3_dread_net_hanger', [(x-2.3, 2.58, z-1.8), (x-.3, 2.58, z-1.8)], .025, m['wood'], 7)
        for dx in [-2.3, -.3]:
            c.pipe('ep3_dread_net_hanger_rope', [(x+dx, 2.58, z-1.8), (x+dx, 3.43, z-1.8)], .005, m['rope'], 5)
    # Connect the old traps to mooring stakes with a supported fishing rack.
    for obj in list(c.coll.objects):
        if obj.name.startswith('fish_trap') and obj.type == 'MESH':
            p = sum((v.co for v in obj.data.vertices), Vector())/len(obj.data.vertices)
            x, z = p.x, -p.y
            c.pipe('ep3_dread_trap_rack', [(x-.35, -1.2, z), (x-.35, .74, z), (x+.35, .74, z), (x+.35, -1.2, z)], .035, m['dark'], 7)
    # Small, warm practical lamps make human faces legible inside the cold storm.
    for index, (x, z) in enumerate([(-70.5, 4.8), (-62.8, -4.3), (-56.5, -5)]):
        c.prop('vintage_oil_lamp', x, 1.5, z, .55, name='ep3_dread_market_lamp')
        marker = bpy.data.objects.new('light_flame_market_'+str(index), None)
        c.coll.objects.link(marker)
        marker.parent = c.root
        marker.location = (x, -z, 1.7)
        c.pipe('ep3_dread_market_lamp_shelf', [(x-.2, 1.47, z), (x+.2, 1.47, z)], .025, m['wood'], 7)
        c.pipe('ep3_dread_market_lamp_bracket', [(x, .7, z), (x, 1.47, z)], .035, m['dark'], 7)


def ground_props(collection):
    bpy.context.view_layer.update()
    changes = []
    roots = [o for o in collection.objects if 'ep3_support_height' in o]
    # Older detail scenes predate the metadata; their authored location is still
    # the intended contact height and can be recovered without touching physics.
    for obj in collection.objects:
        if obj.type == 'EMPTY' and obj.name.startswith(('real_', 'ep3_finish_')) and obj.children and obj not in roots:
            obj['ep3_support_height'] = obj.matrix_world.translation.z
            roots.append(obj)
    # Exact supporting surfaces for table dressing and bedside vessels.
    furniture = [o for o in roots if any(n in o.name for n in ['WoodenTable', 'bedside_stool', 'lamp_stool'])]
    roots.sort(key=lambda obj: obj not in furniture)
    for obj in roots:
        box = bounds(obj)
        if not box:
            continue
        intended = float(obj['ep3_support_height'])
        if 'market_meal' in obj.name or 'market_bananas' in obj.name:
            intended = 1.445
        if obj.name == 'real_practical_lantern_lok_lamp':
            stool = bpy.data.objects.get('real_lok_lamp_stool')
            if stool:
                intended = bounds(stool)[1][2]+.002
        if any(n in obj.name for n in ['real_water_vessel_', 'real_clinic_ceramic_pot', 'real_clinic_book_encyclopedia']):
            p = obj.matrix_world.translation
            nearby = [(math.hypot(p.x-f.matrix_world.translation.x, p.y-f.matrix_world.translation.y), bounds(f)) for f in furniture]
            if nearby and min(nearby, key=lambda v:v[0])[0] < 1:
                intended = min(nearby, key=lambda v:v[0])[1][1][2] + .002
        delta = intended-box[0][2]
        world = obj.matrix_world.copy()
        world.translation.z += delta
        obj.matrix_world = world
        if obj.name == 'real_practical_lantern_lok_lamp':
            marker = bpy.data.objects.get('light_flame_lok_lamp')
            if marker:
                world = marker.matrix_world.copy()
                world.translation.z += delta
                marker.matrix_world = world
        obj['ep3_support_height'] = intended
        changes.append({'name': obj.name, 'support': round(intended,4), 'previousGap': round(-delta,4)})
    bpy.context.view_layer.update()
    report = {'props': changes, 'maxResidual': max((abs(bounds(o)[0][2]-float(o.get('ep3_support_height',0))) for o in roots if bounds(o)), default=0)}
    path = Path(ROOT)/'docs/production/ep3-support-audit.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print('EP3 support audit:', len(changes), 'imported props; residual', report['maxResidual'], flush=True)


def apply_dread(c, collection):
    flooded_forest(c)
    shelter(c)
    ground_props(collection)
    support_documents(c, collection)
    mature_forest(collection)
    anchor_boats(collection)


def support_documents(c, collection):
    """Story papers use measured tables, including the formerly hovering letter."""
    for obj in list(collection.objects):
        if obj.name.startswith('ep3_dread_document_stand'):
            bpy.data.objects.remove(obj,do_unlink=True)
    bpy.context.view_layer.update()
    tables = [o for o in collection.objects if o.type == 'MESH' and (o.name.endswith('_top') or '_top.' in o.name)]
    for name in ['interact_note_'+n for n in ['admission','mother','calendar','letter','return']]+['interact_calendar_key']:
        root = bpy.data.objects.get(name)
        if not root:
            continue
        box = bounds(root)
        x, y = root.matrix_world.translation[:2]
        # Ink was originally authored outside the interaction root. Keep it with
        # its page before seating the document on a real supporting surface.
        for line in list(collection.objects):
            if not line.name.startswith('written_ink_line') or (line.parent and line.parent.name!='village_axes'):
                continue
            centre = sum((line.matrix_world@Vector(p) for p in line.bound_box),Vector())/8
            if abs(centre.x-x)<.18 and abs(centre.y-y)<.24 and abs(centre.z-box[1][2])<.12:
                matrix=line.matrix_world.copy()
                matrix.translation.z += box[1][2]+.001-centre.z
                line.parent=root;line.matrix_world=matrix
        candidates = []
        for table in tables:
            low, high = bounds(table)
            if low[0]-.02<x<high[0]+.02 and low[1]-.02<y<high[1]+.02 and abs(high[2]-box[0][2])<.2:
                candidates.append((abs(high[2]-box[0][2]),table,high[2]))
        if candidates:
            _,table,top=min(candidates,key=lambda item:item[0])
        else:
            top = box[0][2]-.002
            floor = -1.6 if 'letter' in name else 0
            local = c.root.matrix_world.inverted()@Vector((x,y,top))
            local_x, z = local.x, -local.y
            table = c.box('ep3_dread_document_stand_top',local_x,top-.018,z,.56,.036,.61,c.m['wood'],.005)
            for dx in [-.23,.23]:
                for dz in [-.25,.25]:
                    c.box('ep3_dread_document_stand_leg',local_x+dx,(floor+top-.036)/2,z+dz,.052,top-.036-floor,.052,c.m['dark'],.003)
                c.pipe('ep3_dread_document_stand_brace',[(local_x+dx,floor+.22,z-.25),(local_x+dx,floor+.22,z+.25)],.022,c.m['dark'],6)
            tables.append(table)
        table['ep3_supports_document'] = name
        matrix=root.matrix_world.copy();matrix.translation.z += top+.002-box[0][2];root.matrix_world=matrix
        root['ep3_document_seated'] = True
    bpy.context.view_layer.update()


def mature_forest(collection):
    trees = [o for o in collection.objects if o.type == 'EMPTY' and (o.get('ep3_forest_tree') or o.name.startswith('ep3_dread_far_forest'))]
    bpy.context.view_layer.update()
    for tree in trees:
        low, high = bounds(tree)
        target = 7+(sum(map(ord,tree.name))%7)*.65
        tree.scale *= target/(high[2]-low[2])
        tree['ep3_canopy_height'] = target
    bpy.context.view_layer.update()
    transforms = {}
    for tree in trees:
        low, _ = bounds(tree)
        world = tree.matrix_world.copy()
        world.translation.z += float(tree['ep3_support_height'])-low[2]
        tree.matrix_world = world
        transforms[tree.name] = {'translation':[tree.location.x,tree.location.z,-tree.location.y], 'scale':[tree.scale.x,tree.scale.z,tree.scale.y]}
    bpy.context.view_layer.update()
    Path('/tmp/ep3-forest-transforms.json').write_text(json.dumps(transforms))
    print('EP3 mature canopy:',len(trees),'trees',flush=True)


def anchor_boats(collection):
    bpy.context.view_layer.update()
    drafts = []
    for name in ['market_sampan_'+str(i) for i in range(5)]+['lok_sampan','sora_moored_boat']:
        hull = bpy.data.objects.get(name+'_hull')
        if not hull:
            continue
        box = bounds(hull)
        delta = -.22-box[0][2]
        parts = [o for o in collection.objects if o.name.startswith(name)]
        for obj in parts:
            parent = obj.parent
            carried = False
            while parent:
                if parent in parts:
                    carried = True
                    break
                parent = parent.parent
            if carried:
                continue
            world = obj.matrix_world.copy()
            world.translation.z += delta
            obj.matrix_world = world
            if 'ep3_support_height' in obj:
                obj['ep3_support_height'] += delta
        bpy.context.view_layer.update()
        drafts.append({'boat': name, 'keel': round(bounds(hull)[0][2],4), 'water': -.08, 'correction': round(delta,4)})
    path = Path(ROOT)/'docs/production/ep3-support-audit.json'
    report = json.loads(path.read_text()) if path.exists() else {}
    report['boatDrafts'] = drafts
    path.write_text(json.dumps(report,indent=2)+'\n')
    print('EP3 boat drafts:',drafts,flush=True)
