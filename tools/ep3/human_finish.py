"""Loosely fitted clothes, layered wet hair and complete faces for every actor."""
import math

import bpy
import numpy as np
from mathutils import Vector
from kit import plain
from cinematic_scene import hair_material


def remove(obj):
    bpy.data.objects.remove(obj, do_unlink=True)


def lower_garment(c, body, material, child):
    h = max(v.co.z for v in body.data.vertices)
    hem = h*.23 if child else .1
    profiles = ([(-1, -.058), (1, .058)] if child else [(0, 0)])
    for side, centre in profiles:
        def surface(u, v):
            angle = u*math.tau
            height = hem+(h*.59-hem)*v
            radius = (.078+.025*v) if child else (.23-.065*v**5)
            fold = (.004 if child else .012)*(1-v*.6)*math.sin(angle*19+v*1.7)
            radius += fold+.003*math.sin(angle*37-v*7)
            return centre+(radius*math.cos(angle)), height+.006*math.sin(angle*5)*(1-v), -radius*math.sin(angle)*(.88 if child else 1)
        skirt = c.grid('ep3_human_'+body.name+'_shorts' if child else 'ep3_human_'+body.name+'_sampot', 64, 35, surface, material)
        skirt.parent = body
    return hem


def relax_shirt(body, shirt):
    h = max(v.co.z for v in body.data.vertices)
    scale = h/1.65
    basis = shirt.data.shape_keys.key_blocks[0]
    offsets = []
    for vertex in basis.data:
        p = vertex.co.copy()
        # Cloth spans the chest and abdomen instead of outlining bare anatomy.
        torso = math.sqrt(max(0, 1-(p.x/(.235*scale))**2))
        if h*.47 < p.z < h*.84 and torso > 0:
            front = (-.135 if p.z > h*.66 else -.125)*scale
            if p.y < 0:
                p.y = min(p.y, front*torso)
            else:
                p.y = max(p.y, .105*scale*torso)
        waist = math.exp(-((p.z/h-.51)/.07)**2)
        elbow = math.exp(-((abs(p.x)-.29)/.08)**2)
        p.y += (.004*math.sin(p.x*73+p.z*21)+.003*math.sin(p.x*31-p.z*39))*(.25+waist+elbow)
        offsets.append(p-vertex.co)
    for key in shirt.data.shape_keys.key_blocks:
        points = np.empty(len(key.data)*3, dtype=np.float32)
        key.data.foreach_get('co', points)
        points = points.reshape(-1,3)+np.asarray(offsets)
        key.data.foreach_set('co', points.ravel())
    points = np.empty(len(basis.data)*3, dtype=np.float32)
    basis.data.foreach_get('co', points)
    shirt.data.vertices.foreach_set('co', points)
    shirt.data.update()


def skin_only(body, hem):
    # Rebuild topology with the same indexed vertices and morphs. The underlying
    # painted shirt/legs must not poke through the actual loose cloth shell.
    old = body.data
    kept = [p for p in old.polygons if p.material_index == 0 or (p.material_index == 2 and p.center.z < hem)]
    data = bpy.data.meshes.new(body.name+'_visible_skin')
    data.from_pydata([v.co[:] for v in old.vertices], [], [list(p.vertices) for p in kept])
    for material in old.materials: data.materials.append(material)
    layer = data.uv_layers.new(name='MakeHumanUV')
    source = old.uv_layers.active
    for new, original in zip(data.polygons, kept):
        new.material_index = 0
        new.use_smooth = True
        for a,b in zip(new.loop_indices,original.loop_indices): layer.data[a].uv = source.data[b].uv
    poses = [(key.name,[v.co.copy() for v in key.data]) for key in old.shape_keys.key_blocks]
    body.data = data
    for name, points in poses:
        key = body.shape_key_add(name=name, from_mix=False)
        key.value = 0
        key.data.foreach_set('co', np.asarray(points,dtype=np.float32).ravel())


def hair(c, body, long):
    h = max(v.co.z for v in body.data.vertices)
    root = body
    for obj in list(body.children_recursive):
        if 'hair' in obj.name or 'milky_eye' in obj.name or 'scalp' in obj.name:
            remove(obj)
    material = bpy.data.materials.get('M_ep3_human_wet_hair') or plain('M_ep3_human_wet_hair', (.009,.011,.009),rough=.31)
    faces = []
    for poly in body.data.polygons:
        p = poly.center
        threshold = h*(.955+.008*math.cos(p.x*26)) if p.y < -.01 else h*.907
        if p.z > threshold or (abs(p.x) > .067 and p.z > h*.93): faces.append(list(poly.vertices))
    mesh = bpy.data.meshes.new('fitted_hairline')
    mesh.from_pydata([v.co+v.normal*.002 for v in body.data.vertices], [], faces)
    mesh.materials.append(material)
    cap = bpy.data.objects.new('ep3_human_'+body.name+'_hair_cap',mesh)
    c.coll.objects.link(cap)
    cap.parent = root
    for p in mesh.polygons: p.use_smooth = True
    if not long:
        return
    strands = bpy.data.materials.get('M_ep3_real_fine_wet_hair') or hair_material()
    for k in range(56):
        a = k*math.tau/56
        if math.sin(a) < -.22:
            continue
        def surface(u,v,a=a,k=k):
            angle = a+(u-.5)*.56
            radius = .014+.108*math.sin(min(1,v/.23)*math.pi/2)+.025*v*v
            radius += .006*math.sin(v*5+k)*v
            z = h*(1.003-.33*v)-v*v*(.09+(k%4)*.023)
            return radius*math.cos(angle), z, -radius*math.sin(angle)+.025*v
        lock = c.grid('ep3_human_kanha_wet_lock',7,30,surface,strands)
        lock.parent = body


def finish_people(c, collection):
    bodies = [o for o in collection.objects if o.type == 'MESH' and o.name.endswith('_body')]
    for body in bodies:
        if body.get('ep3_finished_human'):
            continue
        child = body.name.startswith('pich')
        shirts = [o for o in body.children if o.name.startswith('ep3_finish_') and o.name.endswith('_blouse')]
        if not shirts:
            continue
        shirt = shirts[0]
        relax_shirt(body,shirt)
        wrap = next(m for m in bpy.data.materials if m.name.startswith('M_ep3_real_drowned_indigo_wrap') and m.users)
        for obj in list(body.children):
            if obj.name.endswith('_sampot') or obj.name.startswith('pich_wrapped'): remove(obj)
        hem = lower_garment(c,body,wrap,child)
        skin = body.data.materials[0]
        bsdf = skin.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Roughness'].default_value = .62
        bsdf.inputs['Coat Weight'].default_value = .07
        bsdf.inputs['Coat Roughness'].default_value = .35
        hair(c,body,body.name.startswith('kanha'))
        skin_only(body,hem)
        body['ep3_finished_human'] = True
        print('EP3 actor dressed:',body.name,flush=True)
    finish_faces(c, collection)


def finish_faces(c, collection):
    # The previous composition pass put a second hair curtain on the actor
    # root. The fitted crown/locks replace it, including during incremental builds.
    for obj in list(collection.objects):
        if obj.name.startswith('ep3_finish_kanha_hair'):
            remove(obj)
    for body in [o for o in collection.objects if o.type == 'MESH' and o.name.endswith('_body')]:
        keys = body.data.shape_keys
        if not keys or keys.key_blocks.get('blink'):
            continue
        eyes = [o for o in body.children if '_eye_' in o.name and o.type == 'MESH']
        centres = [sum((v.co for v in eye.data.vertices),Vector())/len(eye.data.vertices) for eye in eyes]
        blink = body.shape_key_add(name='blink',from_mix=False)
        blink.value = 0
        for vertex in blink.data:
            p = vertex.co
            for eye in centres:
                if abs(p.x-eye.x)<.018 and abs(p.z-eye.z)<.014 and abs(p.y-eye.y)<.021:
                    weight = max(0,1-abs(p.x-eye.x)/.018)**.5
                    p.z += (-.011 if p.z>eye.z else .003)*weight
                    break
    lok = bpy.data.objects.get('npc_lok_body')
    if lok and not bpy.data.objects.get('ep3_human_lok_woven_hat'):
        for obj in [o for o in collection.objects if o.name.startswith('lok_hat')]: remove(obj)
        height = max(v.co.z for v in lok.data.vertices)
        def hat(u,v):
            a = u*math.tau
            radius = v*.29
            return radius*math.cos(a), height+.1*(1-v)**1.8-.045*v*v, -radius*math.sin(a)
        mat = c.m['bamboo'].copy()
        mat.name = 'M_ep3_palm_fibre_hat'
        mat.use_backface_culling = False
        obj = c.grid('ep3_human_lok_woven_hat',72,20,hat,mat)
        obj.parent = lok
