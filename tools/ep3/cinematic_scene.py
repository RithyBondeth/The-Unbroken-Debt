"""Episode 3's close-view silhouettes, working market and ritual composition.
Uses the same CC0 photographed kit and real dimensions as Episode 1.
"""
import math, random
import bpy, bmesh
import numpy as np
from mathutils import Vector
from kit import plain
from realism_materials import mapped, cotton

def hair_material():
    n=512;r=np.random.default_rng(171);y,x=np.mgrid[:n,:n]/n
    alpha=np.zeros((n,n));height=np.zeros_like(alpha)
    for _ in range(86):
        at=r.random();width=r.uniform(.0008,.004)
        strand=np.exp(-((x-at-.004*np.sin(y*9+at*25))/width)**2)
        strand*=np.clip((r.uniform(.72,1.15)-y)*22,0,1)
        alpha=np.maximum(alpha,strand);height+=strand*.008
    rgb=np.ones((n,n,3))*[.019,.023,.02]
    rgb*=1+(height*12)[:,:,None]
    return mapped('fine_wet_hair',rgb,height,.32+np.minimum(height*3,.12),alpha=(alpha>.19).astype(float),tile=.2,normal_strength=.12)

def clothe_people(c,collection,reuse_materials=False):
    # Separate cloth shells relax anatomical contours. Original skin remains
    # beneath them; cloth no longer consists of colours painted onto bare bodies.
    hair=(bpy.data.materials.get('M_ep3_real_fine_wet_hair') if reuse_materials else None) or hair_material();cloth=c.m['cotton']
    child=bpy.data.objects.get('pich_body')
    if child and not child.get('ep3_child_proportions'):
        h=max(v.co.z for v in child.data.vertices)
        def youth(p):
            w=max(0,min(1,(p.z/h-.80)/.075));center=h*.91
            p.x*=1+w*.5;p.y*=1+w*.25;p.z+=(p.z-center)*w*.28
        for key in child.data.shape_keys.key_blocks:
            for vertex in key.data:youth(vertex.co)
        for vertex in child.data.vertices:youth(vertex.co)
        for obj in child.children:
            if obj.type=='MESH' and 'hair' in obj.name:
                for vertex in obj.data.vertices:youth(vertex.co)
        child['ep3_child_proportions']=True
    for obj in list(collection.objects):
        if obj.name.startswith(('pich_wrapped_sampot','pich_cotton_shirt')):bpy.data.objects.remove(obj,do_unlink=True)
    jacket=(next((m for m in bpy.data.materials if m.name.startswith('M_ep3_real_charcoal_work_coat') and m.users),None) if reuse_materials else None) or cotton('charcoal_work_coat',1981)
    bsdf=jacket.node_tree.nodes.get('Principled BSDF')
    # Dark dye is baked into the base map so glTF retains it.
    tex=next(n.image for n in jacket.node_tree.nodes if n.type=='TEX_IMAGE' and '_BC' in n.image.name)
    px=np.empty(len(tex.pixels),dtype=np.float32);tex.pixels.foreach_get(px)
    px=px.reshape(-1,4)
    if not reuse_materials:
        px[:,:3]*=[.22,.27,.28];tex.pixels.foreach_set(px.ravel());tex.save()
    wrap=(next((m for m in bpy.data.materials if m.name.startswith('M_ep3_real_drowned_indigo_wrap') and m.users),None) if reuse_materials else None) or cotton('drowned_indigo_wrap',1941)
    wt=next(n.image for n in wrap.node_tree.nodes if n.type=='TEX_IMAGE' and '_BC' in n.image.name)
    colors=np.empty(len(wt.pixels),dtype=np.float32);wt.pixels.foreach_get(colors)
    colors=colors.reshape(-1,4)
    if not reuse_materials:
        colors[:,:3]*=[.3,.38,.42];wt.pixels.foreach_set(colors.ravel());wt.save()
    for obj in collection.objects:
        if obj.name.startswith('kanha_wet_sampot') and obj.type=='MESH':obj.data.materials.clear();obj.data.materials.append(wrap)
    people=[o for o in collection.objects if o.type=='MESH' and (o.name.endswith('_body') or o.name.startswith('market_resident_') and o.data.shape_keys)]
    for body in people:
        if not body.data.vertices or not body.data.materials:continue
        ghost=body.name.startswith(('kanha','pich'));male='vuthy' in body.name or 'lok' in body.name
        mat=jacket if 'vuthy' in body.name or body.name.startswith('kanha') else cloth
        if body.name.startswith('kanha'):
            body.data.materials[1]=jacket;body.data.materials[2]=wrap
        h=max(v.co.z for v in body.data.vertices)
        if body.name.startswith('pich'):
            body.data.materials[2]=wrap
            for poly in body.data.polygons:
                if poly.center.z<h*.41:
                    poly.material_index=2 if poly.center.z>h*.21 else 0
        selected=[]
        for poly in body.data.polygons:
            p=poly.center
            # Bone-region material assignment distinguishes the torso and upper
            # arms from hands held in front of the abdomen. A height/width box
            # accidentally made a second cloth copy of the hands.
            if poly.material_index==1:
                selected.append(poly)
        used=sorted({i for poly in selected for i in poly.vertices});remap={v:i for i,v in enumerate(used)}
        verts=[body.data.vertices[i].co+body.data.vertices[i].normal*.013 for i in used]
        data=bpy.data.meshes.new('tailored_blouse');data.from_pydata(verts,[],[[remap[i] for i in p.vertices] for p in selected]);data.materials.append(mat);data.update()
        bm=bmesh.new();bm.from_mesh(data)
        for _ in range(5):bmesh.ops.smooth_vert(bm,verts=list(bm.verts),factor=.55,use_axis_x=True,use_axis_y=True,use_axis_z=True)
        bm.to_mesh(data);bm.free()
        for v in data.vertices:
            p=v.co
            p.y+=.0025*math.sin(p.z*62+p.x*17)*math.sin(p.x*31)
        uv=data.uv_layers.new(name='Cloth_metres')
        for poly in data.polygons:
            poly.use_smooth=True
            for li in poly.loop_indices:
                p=data.vertices[data.loops[li].vertex_index].co;uv.data[li].uv=(p.x/.7,p.z/.7)
        shirt=bpy.data.objects.new('ep3_finish_'+body.name+'_blouse',data);collection.objects.link(shirt);shirt.parent=body
        # Copy each authored motion to the same cloth vertices so talking poses
        # cannot poke a bare arm through a static garment.
        shirt.shape_key_add(name='Basis')
        if body.data.shape_keys:
            basis=body.data.shape_keys.key_blocks[0]
            for key in list(body.data.shape_keys.key_blocks)[1:]:
                out=shirt.shape_key_add(name=key.name,from_mix=False);out.value=0
                points=[rest.co+key.data[idx].co-basis.data[idx].co for idx,rest in zip(used,data.vertices)]
                out.data.foreach_set('co',np.asarray(points,dtype=np.float32).ravel())
        # The buttoned placket and a real collar break the painted-body silhouette.
        for k in range(4):
            z=h*(.59+k*.055)
            near=[v.co.y for v in body.data.vertices if abs(v.co.x)<.025 and abs(v.co.z-z)<.025]
            front=min(near,default=-.1)-.023
            c.pipe('ep3_finish_'+body.name+'_button',[(0,z,-front),(.001,z,-front+.003)],.0035,c.m['edge'],8).parent=body
        # Old hair is retained for living villagers; the drowned mother's hair
        # becomes layered fine cards, with an irregular fringe across one eye.
        if body.name.startswith('kanha'):
            root=body.parent
            for o in list(collection.objects):
                if o.name.startswith('kanha_hair_strand'):bpy.data.objects.remove(o,do_unlink=True)
            for k in range(34):
                a=k*math.tau/34
                if math.sin(a)<-.5 and k%4:continue
                def card(u,v,a=a,k=k):
                    angle=a+(u-.5)*.30
                    radius=.102+.013*math.sin(v*4+k)*v+.034*v
                    z=h*(1.008-.39*v)-v*v*(.16+(k%5)*.035)
                    return radius*math.cos(angle),z,-radius*math.sin(angle)+.035*v
                o=c.grid('ep3_finish_kanha_hair',7,26,card,hair)
                o.parent=root
        # Living shoulders carry folded cloth rather than identical blank torsos.
        if not ghost:
            for side in [-1,1] if male else [-1]:
                def scarf(u,v,side=side):
                    z=h*.83-v*.33;return side*(.12+u*.07),z,.115+.018*math.sin(v*5+u*8)
                o=c.grid('ep3_finish_'+body.name+'_shoulder_cloth',10,24,scarf,c.m['curtain']);o.parent=body

def market_depth(c):
    m=c.m;r=random.Random(7301)
    # Foliage and submerged roots frame the playable docks without occupying
    # their collision routes. These are main's photographed, decimated models.
    for x,z,s in [(-89,-16,3.2),(-86,17,2.8),(-43,-18,3.3),(-39,9,3.1),(-81,-35,3.4),(-51,-37,3.6),(-66,-40,4)]:
        c.prop('island_tree_02',x,-.35,z,s,rotation=r.uniform(-180,180),name='ep3_finish_flooded_tree')
        c.prop('root_cluster_01',x,-.4,z,s*.8,name='ep3_finish_submerged_roots')
    for x,z in [(-82,0),(-46,-8),(-83,-27),(19,-16),(-25,-25),(23,9)]:
        c.prop('dead_tree_trunk_02',x,-.5,z,1.1,rotation=r.uniform(-180,180),name='ep3_finish_drowned_snag')
    for index,(x,z) in enumerate([(-72,-5),(-56,-6),(-72,4),(-56,3),(-64,-13)]):
        # Overlapping shutters, threshold trims, gable boards and lifted roof hems.
        for side in [-1,1]:
            for k in range(8):
                o=c.box('ep3_finish_market_louver',x+side*3.23,1.6+k*.11,z-.15,.08,.075,1.2,m['bamboo'],.004)
                o.rotation_euler.y=.12*side
            c.pipe('ep3_finish_awning_rope',[(x+side*1.9,2.68,z+.4),(x+side*2.3,1.1,z+2.65)],.008,m['rope'],7)
        for k in range(16):
            xx=x-3.2+(k+.5)*.4;top=4.47-abs(xx-x)*.275
            c.box('ep3_finish_market_gable',xx,(3.26+top)/2,z-2.85,.37,max(.05,top-3.26),.07,m['wood'],.003)
        for px,pz in [(x-1.8,z+1.4),(x+1.7,z+1.65)]:
            c.prop('wooden_bowl_01',px,1.5,pz,.35,name='ep3_finish_market_meal')
        c.prop('vintage_suitcase',x+2.2,.72,z-1.6,.65,rotation=13,name='ep3_finish_market_luggage')
        c.prop('wooden_ladder_02',x+3.45,-.12,z+2,.8,rotation=12,name='ep3_finish_water_ladder')
        # Sagging, fine fishing net hangs from real supports. Uneven wet hems
        # and a few missing strands avoid a perfect repeated lattice.
        for j in range(19):
            xx=x-2.2+j*.1
            pts=[(xx+.035*math.sin(t*5+j),2.55-t*(1.2+.2*math.sin(j)),z-1.8+.12*math.sin(t*math.pi)) for t in [k/8 for k in range(9)]]
            c.pipe('ep3_finish_hanging_net_warp',pts,.0018,m['rope'],5)
        for j in range(12):
            t=j/12
            c.pipe('ep3_finish_hanging_net_weft',[(x-2.2+k*.1,2.55-t*(1.2+.2*math.sin(k)),z-1.8+.12*math.sin(t*math.pi)) for k in range(19)],.0018,m['rope'],5)
        # Several old repairs have different grain and small iron nail heads.
        for j in range(20):
            xx=x+r.uniform(-3,3);zz=z+r.uniform(-2.5,2.5)
            c.pipe('ep3_finish_dock_nail',[(xx,.705,zz),(xx,.713,zz)],.004,m['metal'],6)
    # Piles, reeds and small floating tangles give the water a scale at the docks.
    for j in range(85):
        x,z=r.choice([-84,-44])+r.uniform(-3,3),r.uniform(-25,19)
        for k in range(3):
            h=r.uniform(.2,1.1)
            c.pipe('ep3_finish_flood_reed',[(x,-.13,z),(x+.05,h*.5,z+.06),(x+.12,h,z+.1)],.004,m['mould'],5,end=.001)

def ritual_craft(c,collection):
    m=c.m
    c.prop('vintage_oil_lamp',-11.35,5.2,2.3,.7,name='ep3_finish_ritual_hanging_lamp')
    c.pipe('ep3_finish_ritual_lamp_chain',[(-11.35,5.65,2.3),(-11.35,6.1,2.3)],.005,m['metal'],6)
    marker=bpy.data.objects.new('light_flame_ritual_key',None);collection.objects.link(marker);marker.parent=c.root;marker.location=(-11.35,-2.3,5.43)
    # A human-scale, sheltered tableau. Actual candles remain at their original
    # interaction coordinates; the small light cards are replaced with flames.
    vessel=c.prop('brass_pot_01',-12,3.36,5,.22,name='ep3_finish_ritual_water_vessel')
    target=bpy.data.objects.get('interact_purify')
    if target:
        bpy.context.view_layer.update();world=vessel.matrix_world.copy();vessel.parent=target;vessel.matrix_world=world
    c.prop('wooden_bowl_01',-13.1,3.37,5.6,.4,name='ep3_finish_ritual_offering')
    c.prop('wicker_basket_01',-13.2,3.36,6.7,.5,name='ep3_finish_ritual_basket')
    for j,(x,z) in enumerate([(-12.45,4.5),(-11.6,4.5),(-12,5.3),(-12,3.8)]):
        c.prop('brass_candleholders',x,3.35,z,.17,name='ep3_finish_ritual_candle_foot')
        for k in range(7):
            a=k*math.tau/7
            c.pipe('ep3_finish_candle_wax_run',[(x+.04*math.cos(a),3.5-(k%3)*.017,z+.04*math.sin(a)),(x+.041*math.cos(a),3.39,z+.041*math.sin(a))],.004,m['ivory'],6)
        c.pipe('ep3_finish_blackened_wick',[(x,3.54,z),(x+.002,3.57,z)],.0018,m['void'],6)
    # A wax pillar has parallel sides and a melted crown, rather than the old
    # bottle-shaped primitive. Keep each interaction's own mesh and parent.
    for obj in list(collection.objects):
        if not obj.name.startswith('yellow_candle') or obj.type!='MESH':continue
        n=40;verts=[]
        for j in range(6):
            for k in range(n):
                a=k*math.tau/n;radius=.029*(1+.035*math.sin(a*7+j*.8))
                h=.19*j/5-(.004*math.sin(a*3)**2 if j==5 else 0)
                verts.append((radius*math.cos(a),radius*math.sin(a),h))
        faces=[(j*n+k,j*n+(k+1)%n,(j+1)*n+(k+1)%n,(j+1)*n+k) for j in range(5) for k in range(n)]
        verts.append((0,0,.178));faces += [(5*n+k,5*n+(k+1)%n,len(verts)-1) for k in range(n)]
        data=bpy.data.meshes.new('hand_poured_wax');data.from_pydata(verts,[],faces);data.materials.append(m['ivory'])
        for poly in data.polygons:poly.use_smooth=True
        obj.data=data
        obj.location=(0,0,-.12);obj.rotation_euler=(0,0,0);obj.scale=(1,1,1)
    # A worn woven mat and its frayed ends anchor the vessels to the floor.
    for k in range(35):
        x=-12.7+k*.04
        c.pipe('ep3_finish_ritual_mat',[(x,3.356,4),(x,3.359,5.8)],.012,m['rope'],6)
    for k in range(14):
        z=4+k*.135;c.pipe('ep3_finish_ritual_mat_weft',[(-12.7,3.366,z),(-11.3,3.366,z)],.003,m['bamboo'],5)
    for k in range(9):
        x=-12.9+k*.02
        c.pipe('ep3_finish_spent_incense',[(x,3.36,5.8),(x+.03,3.362,6.12)],.0015,m['edge'],5)
    # Broken shutters at the far end compose a dark recess behind the mother.
    for side in [-1,1]:
        for k in range(4):
            c.box('ep3_finish_veranda_shutter',-12.5+side*.85,4.35,1.5+k*.19,.08,1.85,.16,m['dark'],.005)
    for obj in collection.objects:
        if obj.name.startswith('ritual_flame_') and obj.type=='MESH':
            # Keep each named production toggle, replacing its cuboid geometry.
            from kit import texture,glow_material
            mat=glow_material('M_ep3_ritual_flame',texture('T_ep1_flame_BC'),strength=2.2)
            data=bpy.data.meshes.new('ritual_flame_card');data.from_pydata([(-.012,0,-.027),(.012,0,-.027),(.009,0,.034),(-.009,0,.034),(0,-.012,-.027),(0,.012,-.027),(0,.009,.034),(0,-.009,.034)],[],[(0,1,2,3),(4,5,6,7)]);data.materials.append(mat)
            uv=data.uv_layers.new(name='UVMap')
            for i,d in enumerate(uv.data):d.uv=[(0,0),(1,0),(1,1),(0,1)][i%4]
            obj.data=data

def apply_cinematic_finish(c,collection):
    for obj in list(collection.objects):
        if obj.name.startswith(('ep3_finish_','drowned_tree','drowned_branch')):bpy.data.objects.remove(obj,do_unlink=True)
    clothe_people(c,collection)
    market_depth(c)
    ritual_craft(c,collection)
