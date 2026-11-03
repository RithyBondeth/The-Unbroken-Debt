"""Episode 2: The Whispering Pagoda. Metres, Blender X east/Y north/Z up.
Uses Episode 1's kit, textures, foliage builders and CC0 material library.
Run: blender -b --factory-startup -P tools/areas/ep2_area_pagoda.py
Then: npm run export -- ep2 && npm run assets -- ep2
"""
import math
import json
import os
import sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from kit import *
from khmer import place, join, pole, flame, incense_sticks, lotus_buds
from forest import tropical_tree, banyan, bamboo_clump, grass_patch
from forest_detail import understory, grass_geometry
from pagoda_architecture import painted_materials, stupa, temple_roof, temple_interior, Craft
from pagoda_gateway import build_gateway, overgrow_gateway
from pagoda_ruin import (ruin_materials, temple_wall, great_chedi, seated_image, spirit_house, sema_stone,
                         sash, incense_pot, candles, fig_roots, lean, rubble)
from pagoda_stupa import memorial
from pagoda_forest import giant, outer_forest
from pagoda_pond import build_pond, pond_materials
from pagoda_offerings import (offering_materials, sticky_rice_ball, banana_leaf_piece, lotus_bud, lotus_bunch,
                              terracotta_bowl, tray_places)
from pagoda_rituals import (ritual_materials, red_string_web, bound_trunk, boundary_stakes, sorcery_altar,
                            hanging_doll)
from pagoda_props import (prop_materials, hall_buddha, money_tree, curtain_swag, stepped_altar, offering_table,
                          footed_tray, naga_rail, family_emblem, inscribed_tablet,
                          leaf_litter, sutra_table, hall_doors, sealed_doorway, verse_board,
                          bell_pavilion, kuti_furnishings, supplies_contents, lore_contents)
from khmer import rotate_uvs

rng = np.random.default_rng(1932)
bpy.ops.wm.read_factory_settings(use_empty=True)
AREA = bpy.data.collections.new('ep2_area_pagoda')
bpy.context.scene.collection.children.link(AREA)

def materials():
    m = {}
    for key, tex, tint in [
        ('teak', 'dark_wooden_planks', None), ('boards', 'weathered_brown_planks', (.5,.38,.3)),
        ('post', 'weathered_planks', (.44,.38,.32)), ('tiles', 'clay_roof_tiles_02', (.42,.29,.23)),
        ('earth', 'forest_ground_04', (.65,.61,.52)), ('leaves', 'forest_leaves_02', (.65,.58,.44)),
        ('stone', 'clay_plaster', (.58,.6,.52)), ('moss', 'moss_wood', (.47,.53,.4)),
        ('bark', 'bark_brown_02', (.5,.45,.4)), ('bamboo_wall','bamboo_wall',(.75,.68,.58)),
        ('cloth','rough_linen',(.52,.25,.08)), ('skin','clay_plaster',(.45,.42,.32)),
    ]:
        m[key] = library_material(tex, 'M_ep2_'+key, tint=tint)
    for key, tex in [('leaf_cluster','leaf_cluster'), ('bamboo_leaves','bamboo_leaves'), ('grass','grass'), ('bamboo','bamboo')]:
        m[key] = image_material('M_'+key, texture('T_ep1_'+tex+'_BC'), rough=.7, cutout=key!='bamboo')
    for key, col, rough, metal in [('bronze',(.36,.23,.09),.46,.85), ('silver',(.55,.57,.55),.3,.95),
        ('water',(.022,.034,.036),.13,.35), ('lotus',(.48,.23,.27),.8,0), ('lotus_leaf',(.045,.09,.04),.6,0),
        ('paper',(.65,.57,.4),.95,0), ('rice',(.78,.75,.64),.95,0), ('clay',(.28,.13,.07),.9,0),
        ('void',(.006,.006,.005),1,0), ('thread',(.75,.73,.63),.9,0), ('stem_green',(.1,.17,.06),.8,0)]:
        m[key]=plain('M_ep2_'+key,col,rough=rough,metal=metal)
    # Offerings and old metal with real colour and relief: patinated bronze, fired clay.
    m.update(offering_materials())
    m['clay']=m['terracotta']
    m['flame']=glow_material('M_flame', texture('T_ep1_flame_BC'),strength=3)
    m['tiles'].use_backface_culling=False
    # Sculpted bodies use seamless maps; a character UV atlas cannot be box-projected.
    skin_base=os.path.join(LIB,'materials/clay_plaster')
    m['skin']=image_material('M_ep2_ancestor_skin',os.path.join(skin_base,'clay_plaster_BC.jpg'),rough=.9,tint=(.46,.44,.37),tile=.65)
    nodes,links=m['skin'].node_tree.nodes,m['skin'].node_tree.links
    tex=nodes.new('ShaderNodeTexImage');tex.image=image(os.path.join(skin_base,'clay_plaster_N.jpg'),True)
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.6
    links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],nodes['Principled BSDF'].inputs['Normal'])
    m['bamboo_dead']=m['bamboo']
    m['eye']=plain('M_ep2_Pret_eye',(.3,.3,.26),rough=.4,emission=(.2,.2,.17),strength=.12)
    m['hair']=plain('M_ep2_Pret_hair',(.025,.024,.022),rough=.95)
    return m
m=materials()
m.update(painted_materials())
m.update(ruin_materials())
m.update(prop_materials())
m.update(ritual_materials())
m.update(pond_materials())
m['mud']=library_material('mud_forest','M_ep2_mud',tint=(.42,.38,.3))
# Episode 1's forest builders (dead and rag trees, termite mounds) expect these.
for key,tex,tint in [('bark_dead','bark_brown_02',(.42,.41,.38)),('termite','red_dirt_mud_01',(.6,.45,.36)),
                     ('cloth_red','rough_linen',(.36,.07,.05)),('cotton_dirty','rough_linen',(.5,.47,.4)),
                     ('rag','rough_linen',(.3,.27,.22)),('bamboo_wall_2s','bamboo_wall',(.4,.36,.3))]:
    m[key]=library_material(tex,'M_ep2_'+key,tint=tint)
m['rope']=plain('M_ep2_rope',(.3,.25,.17),rough=.95)
with open(os.path.join(ROOT,"src/episodes/ep2/data/garden-layout.json")) as f: layout=json.load(f)

def cube(name,x,z,y,w,d,h,mat,collision=False,surface='stone',**props):
    o=box(name,AREA,x-w/2,x+w/2,z-d/2,z+d/2,y,y+h,mat,edge=.012,**props)
    if name.startswith('col_'):o['surface']=surface
    if collision: collider(name,AREA,x-w/2,x+w/2,z-d/2,z+d/2,y,y+h,surface)
    return o

def anchor(name,x,z,y=0): return empty(name,AREA,(x,z,y))
def adopt(root,objects):
    bpy.context.view_layer.update()
    for o in objects:
        w=o.matrix_world.copy();o.parent=root;o.matrix_world=w
    return root

def usable(name,x,z,y,build):
    before=set(AREA.objects);build()
    objects=[o for o in AREA.objects if o not in before and not o.name.startswith('col_') and o.parent is None]
    return adopt(anchor('interact_'+name,x,z,y),objects)

def sphere(name,at,size,mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=at)
    o=bpy.context.object;o.name=name;o.scale=size
    for c in list(o.users_collection):c.objects.unlink(o)
    AREA.objects.link(o);o.data.materials.append(mat)
    for f in o.data.polygons:f.use_smooth=True
    return o

def lamp(name,x,z,y):
    lathe(name+'_cup',AREA,[(0,0),(.14,0),(.17,.04),(.13,.085),(0,.07)],x,z,y,m['bronze'])
    flame(name+'_flame',AREA,x,z,y+.11,.12,m['flame'])
    empty('light_flame_'+name,AREA,(x,z,y+.18),radius=5,intensity=2.6)

def roof(name,x,z,w,d,eave,ridge):
    temple_roof(AREA,m,name,x,z,w,d,eave,ridge,gable_relief=name in ('vihear','hawtrai'))

def building(name,x,z,w,d,floor):
    cube(name+'_foundation',x,z,floor-.18,w,d,.18,m['stone'],True)
    for i in range(int(w/.2)):
        px=x-w/2+.1+i*.2
        board=cube(name+'_floorboard',px,z,floor,.19,d,.045,m['teak'])
        # Grain along each board, offset so neighbouring boards never line up into tiles.
        rotate_uvs(board);du,dv=rng.uniform(0,1,2)
        for l in board.data.uv_layers.active.data:l.uv=(l.uv[0]+du,l.uv[1]+dv)
    for px in [x-w/2+.15,x+w/2-.15]:
        for pz in np.linspace(z-d/2+.15,z+d/2-.15,4):
            cube(name+'_post',px,pz,-.3,.18,.18,floor+3.3,m['post'],True,surface='teak')
    # Window openings have deep plaster reveals, worn red dado and timber shutters.
    wallmat=m['plaster'] if name=='vihear' else m['boards']
    for px in [x-w/2,x+w/2]:
        cube(name+'_sill_wall',px,z,floor,.22,d,.95,wallmat,True,surface='stone')
        cube(name+'_wall_head',px,z,floor+2.25,.22,d,.5,wallmat,True)
        cube(name+'_red_dado',px,z,floor,.25,d,.32,m['red'])
        count=max(3,round(d/2.3));bay=d/count
        for j in range(count+1):
            pz=z-d/2+j*bay
            cube(name+'_window_pier',px,pz,floor+.95,.25,bay*.48,1.3,wallmat,True)
        for j in range(count):
            pz=z-d/2+(j+.5)*bay
            cube(name+'_window_sill',px,pz,floor+.9,.35,bay*.55,.1,m['carved'])
            # A partly closed wooden shutter leaves a narrow view into the dark nave.
            cube(name+'_shutter',px,pz-bay*.18,floor+1.01,.08,bay*.18,1.19,m['teak'])
    cube(name+'_back',x,z+d/2,floor,w,.22,2.75,wallmat,True,surface='teak')
    for px in [x-w/2+(w-2.7)/4,x+w/2-(w-2.7)/4]:
        cube(name+'_front',px,z-d/2,floor,(w-2.7)/2,.22,2.75,wallmat,True)
        cube(name+'_front_dado',px,z-d/2-.03,floor,(w-2.7)/2,.25,.32,m['red'])
    for px in [x-1.38,x+1.38]:cube(name+'_door_jamb',px,z-d/2-.06,floor,.13,.28,2.8,m['carved'])
    cube(name+'_door_lintel',x,z-d/2-.06,floor+2.7,2.9,.28,.18,m['carved'])
    roof(name,x,z,w+1.5,d+1.5,floor+2.9,2.05)
    roof(name+'_crown',x,z,w*.65,d*.78,floor+4.1,1.55)
    if name!='kuti':temple_interior(AREA,m,name,x,z,w,d,floor)
    # Individual old masonry blocks and coping around the raised plinth.
    craft=Craft()
    for side in [-1,1]:
        for j in range(round(d/.55)):
            craft.block(m['soot'],x+side*(w/2+.06),z-d/2+(j+.5)*.55,floor-.15,.2,.51,.18)
    craft.build(name+'_foundation_stones',AREA)

# A continuous ground collider, with water recessed and no invisible bridge blockers.
# One ground collider; the visible ground leaves room for the sunken pond basin.
collider('earth',AREA,-30,30,-40,42,-.18,-.01,'dirt')
for name,(gx0,gx1,gy0,gy1) in {'earth':(-30,30,-40,17.4),'earth_north':(-30,30,39.2,42),
                                'earth_west':(-30,-18.6,17.4,39.2),'earth_east':(18.6,30,17.4,39.2)}.items():
    box(name,AREA,gx0,gx1,gy0,gy1,-.18,-.01,m['earth'])
cube('col_boundary',-30,1,-.2,1,84,5,None,True)
# East of the fallen bay the forest opens into the clearing of the reclining Buddha
# (the sala, its images and its watchers are authored in tools/ep2/build-cinematics.py).
ANNEX=(28.4,44.6,-21,1.2)
cube('col_boundary',30,-30.6,-.2,1,22.8,5,None,True)
cube('col_boundary',30,21.6,-.2,1,40.8,5,None,True)
cube('col_boundary',45,-9.9,-.2,1,23.2,5,None,True)
for z in [-21.5,1.7]:cube('col_boundary',37,z,-.2,16,1,5,None,True)
collider('earth_annex',AREA,28,45,-21,1.2,-.18,-.01,'dirt')
box('earth_annex',AREA,28,45,-21,1.2,-.18,-.01,m['earth'])
for z in [-40,42]:cube('col_boundary',0,z,-.2,60,1,5,None,True)
# Low masonry compound walls and breathing foliage beyond them.
# Old lotus-crested temple walls: leaning bays, scabbed plaster, fallen sections, creepers.
wall_rng=np.random.default_rng(1767)
temple_wall(AREA,m,'compound_wall_west',(-28,-39.5),(-28,41.5),wall_rng,'mould_white',breaches=(4,13,21))
temple_wall(AREA,m,'compound_wall_east',(28,-39.5),(28,41.5),wall_rng,'mould_grey',breaches=(9,17),open_bays=(9,))
temple_wall(AREA,m,'compound_wall_north',(-28,41.5),(28,41.5),wall_rng,'mould_grey',breaches=(5,))
temple_wall(AREA,m,'gateway_boundary_west',(-28,-27),(-7.6,-27),wall_rng,'mould_red',breaches=(2,))
temple_wall(AREA,m,'gateway_boundary_east',(7.6,-27),(28,-27),wall_rng,'mould_red')
# Reference-led red-and-gold ceremonial arch and pedestrian portals, now overgrown.
build_gateway(AREA,m,walls=False)
overgrow_gateway(AREA,m)
for x in [-2.3,2.3]:
    # Naga balustrades: one fused stone carving, scaled body rising to a fan of five hoods.
    naga_rail(AREA,m,'naga_'+('west' if x<0 else 'east'),x,rng)
    lamp('gate_'+str(x),x,-26,1)
anchor('spawn_player',0,-33)
anchor('marker_kuti_spawn',-17,-17)
# Stone path from threshold, branching to the kuti and prayer hall.
for z in list(range(-30,-10,2))+list(range(14,18,2)):
    cube('processional_slab',0,z,-.005,2.4,1.9,.05,m['stone'])
for x in range(-17,24,2):cube('crossing_slab',x,-17,-.005,1.92,2,.05,m['moss'])
# The warm, modest monk's kuti.
building('kuti',-18,-12,7,7,.15)
cube('kuti_step',-18,-16,0,3,1,.08,m['stone'],True)
def threshold_ramp(name,x,z,w):
    verts=[(x-w/2,z,0),(x+w/2,z,0),(x-w/2,z+1.2,0),(x+w/2,z+1.2,0),(x-w/2,z,.01),(x+w/2,z,.01),(x-w/2,z+1.2,.2),(x+w/2,z+1.2,.2)]
    mesh_object('col_'+name,AREA,verts,[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)],surface='stone')
threshold_ramp('kuti_threshold',-18,-16.7,2.6)
place(AREA,'wicker_basket_01',(-20,-13,.2),scale=.75)
place(AREA,'ceramic_pot',(-16,-11,.2),scale=.65)
lamp('kuti',-18.28,-12.2,.64)
monk=anchor('monk_sophal',-18,-11,.2)
body=[sphere('sophal_robes',(-18,-11,.65),(.5,.35,.45),m['cloth']),sphere('sophal_head',(-18,-11,1.3),(.14,.15,.2),m['skin'])]
adopt(monk,body)
# Facial planes and closed lids of the elderly monk; saffron cloth keeps the silhouette quiet.
for side in [-1,1]:
    sphere('sophal_ear',(-18+side*.137,-11,1.29),(.035,.045,.075),m['skin'])
    tube('sophal_closed_lid',AREA,[(-18+side*.04,-11.143,1.34),(-18+side*.075,-11.15,1.338),(-18+side*.1,-11.138,1.34)],.009,m['skin'],sides=8)
    sphere('sophal_hand',(-18+side*.09,-11.26,.69),(.075,.045,.03),m['skin'])
sphere('sophal_nose',(-18,-11.155,1.3),(.026,.037,.05),m['skin'])
tube('sophal_lips',AREA,[(-18.045,-11.142,1.224),(-18,-11.157,1.22),(-17.955,-11.142,1.224)],.008,m['skin'],sides=8)
# A physical robe with cloth folds and a narrow waist, rather than a flat silhouette.
robe=lathe('sophal_robe',AREA,[(.45,0),(.4,.2),(.28,.55),(.23,.75),(.08,.8)],-18,-11,.25,m['cloth'],segments=40)
for v in robe.data.vertices:
    dx,dy=v.co.x+18,v.co.y+11;a=math.atan2(dy,dx)
    r=math.hypot(dx,dy)
    if r>.05:
        off=.018*math.sin(a*17+v.co.z*2);v.co.x+=dx/r*off;v.co.y+=dy/r*off
# A visible sutra table serves as the interaction target for the monk.
usable('monk',-18,-12,.4,lambda:sutra_table(AREA,m,'monk_sutra_table',-18,-12,.2,rng))
for k,(id,x,z) in enumerate([('supplies',-16,-14),('lore_monk',-20,-14)]):
    offering_table(AREA,m,id+'_table',x,z,.195)
    collider(id+'_table',AREA,x-.48,x+.48,z-.35,z+.35,.05,.64,'teak')
    fill=supplies_contents if id=='supplies' else lore_contents
    usable(id,x,z,.64,lambda x=x,z=z,fill=fill: fill(AREA,m,x,z,.64,rng))
# The monk's room as he lives in it.
kuti_furnishings(AREA,m,-18,-12,.195,rng)
# Shared authored plan: staggered memorial clusters and four old tree islands.
stupa_rng=np.random.default_rng(1910)
for k,monument in enumerate(layout['stupas']):
    name=monument['id'];x=monument['x'];z=-monument['z'];h=monument['height']
    memorial(AREA,m,x,z,k,h,name,stupa_rng)
    collider(name,AREA,x-.7,x+.7,z-.7,z+.7,0,h+.8,'stone')
    if name in ['chea','wife','chhun','kanha']:
        family_emblem(AREA,m,name+'_emblem',x,z-.47,1.21)
        usable('stupa_'+name,x,z-.8,.25,lambda x=x,z=z:lathe('offering_bowl',AREA,[(.15,0),(.2,.03),(.23,.1),(.21,.11),(.16,.04)],x,z-.85,.23,m['bronze']))
        inscribed_tablet(AREA,m,name+'_inscription',x,z-.5,.54,stupa_rng)
        lamp('ancestor_'+name,x+.55,z-.6,.4)
for k,p in enumerate(layout['trees']):
    giant(AREA,m,p['x'],-p['z'],12+k,300+k,rng,reach=.66,crown=1.05)
    collider('garden_tree_'+str(k),AREA,p['x']-.7,p['x']+.7,-p['z']-.7,-p['z']+.7,0,8)
    # Root collars stay inside the collision footprint; lianas hang above head height.
    # Red cord wound round the old trunks, and dolls hung high in their branches.
    bound_trunk(AREA,m,'garden_tree_cord_'+str(k),p['x'],-p['z'],.62,rng)
    for d in range(2):
        a=rng.uniform(0,math.tau)
        hanging_doll(AREA,m,f'garden_tree_doll_{k}_{d}',(p['x']+math.cos(a)*1.6,-p['z']+math.sin(a)*1.6,3.2),rng,drop=rng.uniform(.6,.9))
    for j in range(5):
        a=j*math.tau/5
        tube('garden_buttress',AREA,[(p['x'],-p['z'],1),(p['x']+.45*math.cos(a),-p['z']+.45*math.sin(a),.18),(p['x']+.68*math.cos(a),-p['z']+.68*math.sin(a),.02)],.09,m['bark'],radius_end=.015)
# A crooked, moss-set processional path threads between the memorial clusters.
# Use the same metre-grid clearance as Pret navigation, keeping stones out of bases.
from collections import deque
obstacles=layout['stupas']+layout['trees']
def walkable(p):
    return -13<=p[0]<=13 and -16<=p[1]<=14 and not any(abs(p[0]-o['x'])<1.05 and abs(p[1]-o['z'])<1.05 for o in obstacles)
start=(0,14);goal=(0,-16);queue=deque([start]);came={start:None}
while queue:
    p=queue.popleft()
    if p==goal:break
    for dx,dz in [(0,-1),(1,0),(-1,0),(0,1)]:
        n=(p[0]+dx,p[1]+dz)
        if n not in came and walkable(n):came[n]=p;queue.append(n)
p=goal
while p in came and p is not None:
    cube('winding_path',p[0],-p[1],-.008,.83,.9,.027,m['soot'])
    p=came[p]
# A ruined peripheral cloister creates a second, enclosed walk west of the garden.
# It sits outside the garden navigation domain and leaves the supply tables clear.
for z in [-3,1,5,9,13]:
    for x in [-26,-23]:
        cube('cloister_pier',x,z,0,.62,.62,2.7,m['soot'],True)
        for h in [.12,2.35,2.55]:cube('cloister_cap',x,z,h,.8,.8,.12,m['chalk'])
    cube('cloister_crossbeam',-24.5,z,2.7,3.7,.38,.25,m['carved'])
for z in [-1,7,11]:
    cube('cloister_relic_wall',-26,z,0,.3,3.4,1.1,m['plaster'],True)
    cube('cloister_dado',-25.98,z,0,.34,3.4,.3,m['red'])
# Garden leaf beds use explicit surface colliders to teach sound and footing.
for k,(x,z) in enumerate([(-8,-4),(8,3),(-4,10),(4,-9)]):
    collider('leaf_bed',AREA,x-1.3,x+1.3,z-1,z+1,.012,.03,'leaves')
    leaf_litter(AREA,m,'leaf_bed_'+str(k),x,z,1.3,1.0,np.random.default_rng(70+k))
# Small offering tables: finite puzzle supply and empty bowls for distractions.
for id,x,z in [('rice',-17,-7),('lotus',-17,7),('water',17,9),('bowls',16,-8)]:
    offering_table(AREA,m,id+'_stand',x,z)
    collider(id+'_stand',AREA,x-.5,x+.5,z-.375,z+.375,0,.45,'teak')
    def contents(id=id,x=x,z=z):
        # Three of each on a footed bronze tray (its dish at .56), spaced so none touch.
        footed_tray(AREA,m,id+'_tray',x,z,.44)
        if id=='rice':banana_leaf_piece(AREA,m,'rice_leaf',x,z,.563,rng,length=.5,width=.4,yaw=.3)
        if id=='lotus':
            for px,pz,yaw in lotus_bunch(x,z):lotus_bud(AREA,m,'lotus_bud',px,pz,.561,rng,yaw=yaw+rng.normal(0,.06))
        for px,pz in ([] if id=='lotus' else tray_places(x,z)):
            if id=='water':
                lathe('water_cup',AREA,[(0,0),(.05,0),(.04,.02),(.06,.03),(.085,.1),(.08,.11),(.07,.04),(0,.04)],px,pz,.56,m['bronze'],segments=20)
                lathe('water_surface',AREA,[(0,0),(.074,0)],px,pz,.65,m['water'],segments=16)
            elif id=='rice':sticky_rice_ball(AREA,m,'rice_ball',px,pz,.566,rng)
            else:terracotta_bowl(AREA,m,'empty_clay_bowl',px,pz,.561,rng)
    usable('pickup_'+id,x,z,.5,contents)
# Prayer hall; bell puzzle and lore remain an optional detour.
building('vihear',22,1,9,15,.15)
# Rust-red handprints on the hall's front wall and door jambs, and dolls under its eaves.
from pagoda_rituals import handprints
handprints(AREA,m,'vihear_handprints',[(19.2,-6.62,1.1,-1),(24.6,-6.62,1.4,-1),(20.66,-6.7,1.2,-1),(17.38,-2,1.3,0),(26.62,3,1.0,0)],rng)
for k,x in enumerate([18.2,20.0,24.1,25.9]):
    hanging_doll(AREA,m,'vihear_eave_doll_'+str(k),(x,-7.1,2.95),rng,drop=rng.uniform(.5,.8))
threshold_ramp('hall_threshold',22,-7.8,2.6)
# The hall image after Khmer vihara altars: stepped painted altar, red lotus throne,
# white-faced Buddha in saffron, gilded bodhi trees, small images and old offerings.
altar_top=stepped_altar(AREA,m,22,6,.15)
hall_buddha(AREA,m,22,6.15,altar_top,1.2,0)
for x in [20.85,23.15]:lamp('hall_altar_'+str(x),x,5.2,.53)
for j,(px,py) in enumerate([(21.05,5.4),(22.95,5.4),(21.05,6.6),(22.95,6.6)]):
    money_tree(AREA,m,'altar_money_tree_'+str(j),px,py,.87,.62,rng)
for j,px in enumerate([21.6,22.4]):
    for o in seated_image(AREA,m,'altar_small_image_'+str(j),px,5.25,0,.3,headless=j==1,seed=30+j):o.location.z=.53+.13*.3
candles(AREA,m,'altar_candle_stubs',22,5.15,.53,rng)
for k,x in enumerate([18.4,19.4,20.4]):
    usable('bell_'+str(k),x,-9,1.8,lambda x=x,k=k:lathe('bronze_bell',AREA,[(.23+k*.03,0),(.27+k*.03,.08),(.22,.13),(.17,.38),(.09,.48),(.03,.5)],x,-9,1.8,m['bronze'],segments=32))
# A small tiled bell pavilion on stone footings replaces the bare rack.
bell_pavilion(AREA,m,'bell_frame',17.7,21.1,-9,[18.4,19.4,20.4],rng)
# The verse stands beside the hall steps, out of the walk to the door.
usable('bell_verse',24,-8.6,1.2,lambda:verse_board(AREA,m,'bell_verse',24,-8.6,.8,rng))
# Carved doors stand ajar inside; what seals the hall is chain, cord and cloth.
hall_doors(AREA,m,22,-6.35,.195,rng)
adopt(anchor('hall_chain',22,-6.6,.15),sealed_doorway(AREA,m,'hall_chain',22,-6.6,.15,2.6,2.6,rng))
collider('hall_chain',AREA,21,23,-6.75,-6.55,0,2.65,'stone')
for i,(x,z) in enumerate([(20,3),(24,3)]):
    usable('lore_hall_'+str(i),x,z,.6,lambda x=x,z=z:cube('hall_document',x,z,.6,.45,.4,.025,m['paper']))
    cube('lectern',x,z,0,.7,.7,.6,m['teak'],True)
lamp('hall',22,0,1.2)
# A crimson curtain in a deep swag behind the image, faded and rotting at its hem.
curtain=[]
for j in range(41):
    px=20.2+j*.09
    curtain.extend([(px,7.7+.1*math.sin(j*1.8),.55),(px,7.7+.1*math.sin(j*1.8),3.12)])
mesh_object('vihear_altar_curtain',AREA,curtain,[(j*2,j*2+2,j*2+3,j*2+1) for j in range(40)],m['curtain'])
curtain_swag(AREA,m,'vihear_curtain_swag',20.1,23.9,7.3,3.28,.95,rng)
# Decay: webs in the column heads, tiles fallen through, torn banners from the beams.
from house_detail import corner_web
for j,(px,py) in enumerate([(19.3,-5),(24.7,-2),(19.3,4),(24.7,7),(19.3,1)]):
    corner_web('vihear_web_'+str(j),AREA,(px,py,3.0),(0,1,0),(0,0,-1),.7)
rubble(AREA,m,'vihear_fallen_tiles',18.4,-3.5,.7,30,rng,mats=[m['tiles']],size=(.24,.16,.015))
rubble(AREA,m,'vihear_fallen_tiles',25.6,3.2,.6,24,rng,mats=[m['tiles']],size=(.24,.16,.015))
for j,(px,py) in enumerate([(20.2,-2),(23.8,-2),(20.2,1),(23.8,1)]):
    strip=Craft();mat=m['saffron'] if j%2 else m['white_cloth'];length=rng.uniform(1.1,1.7)
    pts=[(px-.11,py,3.0),(px+.11,py,3.0),(px+.1+rng.normal(0,.02),py+.02,3.0-length),(px,py,3.0-length-.12),(px-.1,py+.02,3.0-length+.05)]
    strip.face(mat,pts);strip.face(mat,list(reversed(pts)));strip.build('vihear_banner_'+str(j),AREA)
for x in [19.5,21,22.5,24]:
    for z in [-3,-1,1]:cube('prayer_mat',x,z,.2,1.05,1.5,.015,m['bamboo_wall'])
for x in [21.23,22.77]:
    lathe('altar_vase',AREA,[(.07,0),(.12,.1),(.1,.2),(.05,.28),(.07,.3)],x,5.15,.53,m['clay'])
    for j in range(5):pole('altar_incense',AREA,(x+(j-2)*.02,5.15,.75),(x+(j-2)*.03,5.15,1.0+j*.02),.003,m['post'])
# Lotus pond and raised scripture library. Land ends at Y=18; the bridge is 2m wide.
# The pond: a sunken, silted tank with an uneven shore (pagoda_pond.py).
pond_parts,pond_reeds,_=build_pond(AREA,m,np.random.default_rng(1911))
for side in [-1,1]:
    cube('col_pond_barrier',side*9.8,28,0,17.4,21,1,None,True)
# Only bridge and library are walkable in the pond; invisible low rail prevents falls.
for x in [-1.12,1.12]:
    cube('col_bridge_safety',x,23,0,.08,10,1.7,None,True)
    pole('bridge_rail',AREA,(x,18,1),(x,28,2.15),.055,m['post'])
for k in range(35):
    y=18+k*.29;top=(y-18)*.12
    cube('bridge_plank',0,y,top,2,.27,.12,m['post'])
    if k%5==0:
        for x in [-1.05,1.05]:cube('bridge_post',x,y,-.3,.11,.11,top+1.5,m['post'])
# Walkable ramp collider matches sloping boards, with no teleport needed.
verts=[(-1,18,-.1),(1,18,-.1),(-1,28,-.1),(1,28,-.1),(-1,18,.12),(1,18,.12),(-1,28,1.32),(1,28,1.32)]
mesh_object('col_bridge_ramp',AREA,verts,[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)],surface='teak')
building('hawtrai',0,32,9,8,1.32)
handprints(AREA,m,'hawtrai_handprints',[(-2.6,27.87,2.4,-1),(2.9,27.87,2.6,-1)],rng)
cube('interact_bridge_lock',0,18,0,1.9,.16,1.5,m['bronze'])
collider('bridge_lock',AREA,-1,1,17.9,18.1,0,1.6)
for i in range(4):
    cylinder('bridge_symbol_'+str(i),AREA,-.6+i*.4,17.9,.9,1,.09,m['silver'])
# Oil lamps left floating on the black water; reeds along the shore.
for x in [-5,5]:lamp('pond_'+str(x),x,23,-.2)
grass_geometry('pond_reeds',AREA,pond_reeds,rng,size=(.7,1.4))
# Archive shelves, tied palm-leaf bundles and swivel mirrors.
for x in [-3.6,3.6]:
    for y in [30,32,34]:
        cube('archive_cabinet',x,y,1.32,.65,1.6,2.2,m['teak'],True,surface='teak')
        for h in [1.7,2.25,2.8]:
            for k in range(4):cube('palm_leaf_bundle',x-.36 if x>0 else x+.36,y-.55+k*.33,h,.25,.26,.1,m['paper'])
for k,(x,z) in enumerate([(-2,29.8),(1.6,31),(-1,33)]):
    root=usable('mirror_'+str(k),x,z,2.25,lambda x=x,z=z:lathe('mirror_stand',AREA,[(.3,0),(.22,.1),(.06,.2),(.04,.8),(.08,.9)],x,z,1.36,m['bronze']))
    mirror=sphere('mirror_disc_'+str(k),(x,z,2.45),(.34,.045,.34),m['silver']);adopt(root,[mirror])
    cube('mirror_rune',x,z-.055,2.25,.08,.02,.3,m['bronze'])
usable('archive',0,35,1.8,lambda:cube('silver_betel_box',0,35,1.8,.7,.45,.3,m['silver']))
cube('archive_table',0,35,1.32,1.2,.8,.45,m['teak'],True,surface='teak')
for k,x in enumerate([-2,2]):
    usable('lore_library_'+str(k),x,34,1.95,lambda x=x:cube('library_record',x,34,1.95,.45,.4,.025,m['paper']))
    cube('reading_stand',x,34,1.32,.7,.7,.6,m['teak'],True,surface='teak')
lamp('archive',0,33,3.4)
# Set pieces between the garden and the walls: all outside the ghosts' navigation
# domain (|X| > 16 or beyond the garden's ends) and clear of the authored routes.
ruin_rng=np.random.default_rng(1767)
great_chedi(AREA,m,16,-22.4,ruin_rng)
# Spirit houses retired under the old banyan, most still upright, some fallen.
for j in range(10):
    a=-1.35+j*.3;r=2.5+(j%3)*.5
    spirit_house(AREA,m,'retired_spirit_house_'+str(j),-23+math.cos(a)*r,-22+math.sin(a)*r,a+math.pi/2+ruin_rng.normal(0,.3),ruin_rng,fallen=j in (2,6,9))
# Damaged images set respectfully in a row on a brick terrace inside the gate wall.
terrace=Craft()
terrace.block(m['brick'],-13.4,-25.55,0,7.4,1.1,.35);terrace.block(m['mould_grey'],-13.4,-25.55,.35,7.6,1.2,.05)
terrace.build('image_terrace',AREA);collider('image_terrace',AREA,-17.1,-9.7,-26.15,-24.95,0,1.6,'stone')
for j in range(6):
    px=-16.4+j*1.2;s=.8
    for o in seated_image(AREA,m,'terrace_image_'+str(j),px,-25.5,math.pi,s,headless=j in (0,2,4),damage=j==3,seed=j):
        o.location.z=.4+.13*s
    if j%2==0:sash(AREA,m,'terrace_image_sash_'+str(j),px,-25.47,.4+.13*s+.5*s,.25*s,m['saffron'],ruin_rng,tail=.35)
    incense_pot(AREA,m,'terrace_incense_'+str(j),px+.25,-24.92,.4,ruin_rng)
    if j%3==1:candles(AREA,m,'terrace_candle_'+str(j),px-.25,-24.95,.4,ruin_rng)
# Sema boundary stones mark the hall's consecrated ground.
for j,(px,py) in enumerate([(16.4,-5.2),(16.4,3.5),(27.6,-6.8),(27.6,1),(27.6,8.6),(22,10),(17.6,10.2)]):
    sema_stone(AREA,m,'sema_'+str(j),px,py,math.atan2(py-1,px-22)+math.pi/2)
# Older, forgotten memorials beyond the garden, leaning hard and swallowed by figs.
forgotten=[(-26,16),(-21.5,16.5),(-19,19),(-26.5,19.5),(-21,27),(-26.5,25.5),(-19.5,31),(-26,33),(-20.5,36.5),(-26,38.5),(-19,39.5),
           (19,16.5),(23,17),(27,22.5),(22.5,24.5),(26.5,30),(19.5,33),(26,39.5),(19,39),(-6.2,-32.6),(5.6,-34.6),(-5.4,-38.6)]
for j,(px,py) in enumerate(forgotten):
    objs=memorial(AREA,m,px,py,200+j,ruin_rng.uniform(2.3,3.5),'forgotten_'+str(j),ruin_rng)
    lean(objs,px,py,ruin_rng.normal(0,.05),ruin_rng.normal(0,.05))
    if j%3==0:
        fig_roots(AREA,m,'forgotten_fig_'+str(j),px,py,2.4,lambda z:.6 if z<1.9 else .45,ruin_rng,n=7,spread=.9,crown=ruin_rng.uniform(1.8,3.2),hang=3)
    collider('forgotten_stupa_'+str(j),AREA,px-.7,px+.7,py-.7,py+.7,0,3.2,'stone')
spirit_house(AREA,m,'roadside_spirit_house',4.8,-37.6,math.pi,ruin_rng)
# Rituals on the approach: a boundary of stakes and red cord both sides of the track,
# cord strung overhead between the trunks, tags, bells and dolls; a sorcery altar.
rit=np.random.default_rng(3311)
for side in (-1,1):
    boundary_stakes(AREA,m,'approach_boundary_'+('w' if side<0 else 'e'),[(side*4.05+rit.normal(0,.08),-39.3+k*1.9) for k in range(6)],rit)
approach_anchors=[(-6.7,-30.2,3.2),(6.2,-29.5,3.1),(-12.5,-37,3.4),(13,-38.5,3.0),(-10.7,-33.2,2.8),(11.2,-31.4,2.9),
                  (-5.3,-35.8,2.7),(-17.5,-32.5,3.3),(17,-33,3.2),(5.3,-34.6,2.4),(-5,-32.6,2.4)]
red_string_web(AREA,m,'approach_web',approach_anchors,rit,density=1.4)
sorcery_altar(AREA,m,'approach_altar',-8.6,-37.4,-.4,rit)
for k,(x,y,r) in enumerate([(-7.2,-30.2,.55),(6.7,-29.5,.55),(-11,-33.2,.3),(11.5,-31.4,.3),(-13,-37,.55)]):
    bound_trunk(AREA,m,'approach_trunk_cord_'+str(k),x,y,r,rit)
# Forgotten yards: cord from stupa to stupa, and an altar among them.
red_string_web(AREA,m,'yard_web_w',[(x,y,2.1) for x,y in forgotten[:11]],rit,density=1.1)
red_string_web(AREA,m,'yard_web_e',[(x,y,2.1) for x,y in forgotten[11:19]],rit,density=1.1)
sorcery_altar(AREA,m,'yard_altar',-23.3,29.2,math.pi/2,rit)
# Seen through the fallen bay of the east wall: another altar under the strangler.
sorcery_altar(AREA,m,'forest_altar',30.6,-14.6,math.pi/2,rit)
# The old cloister becomes a gallery of weathered images facing its walk.
for j,(py,headless) in enumerate([(-1.85,True),(-.15,False),(6.15,False),(7.85,True),(10.15,True),(11.85,False)]):
    seated_image(AREA,m,'cloister_image_'+str(j),-25.35,py,math.pi/2,.7,headless=headless,damage=j==2,seed=10+j)
    collider('cloister_image_'+str(j),AREA,-25.75,-24.95,py-.4,py+.4,0,1.1,'stone')
    if not headless:sash(AREA,m,'cloister_image_sash_'+str(j),-25.35,py,.13*.7+.5*.7,.25*.7,m['saffron'],ruin_rng,tail=.3)
# Layered forest: three ranks of old growth outside, inner emergents, bamboo, understory.
avoid=[(x,y,1.0) for x,y in forgotten]+[(4.8,-37.6,.8)]
outer_forest(AREA,m,np.random.default_rng(6241910),avoid,clear=[(ANNEX[0],ANNEX[1]-1.6,ANNEX[2]+1.4,ANNEX[3]-1.4)])
inner=[(-24,-25),(24,-23),(-24,15),(24,20),(-12,40),(12,40),(-7,-24),(8,-22),(-21,3),(-23,22),(20,28),(-23,35),(25,35),(-9,-34),(8,-35)]
for k,(x,z) in enumerate(inner):
    giant(AREA,m,x,z,rng.uniform(10,15),120+k,rng,reach=1.8,collision=True)
banyan(AREA,m,-23,-22,rng,dressing=False)
for k,(x,z) in enumerate([(-26,-16),(26,14),(-24,30),(22,36),(-25,-31),(25,-32),(-20,23),(20,20),(-8,-37),(10,-38)]):
    bamboo_clump(AREA,m,x,z,k,rng)
spots=[]
for k in range(1400):
    x,z=rng.uniform(-29,29),rng.uniform(-39,41)
    # Hand-authored walkable pockets; avoid buildings, offering approaches and the bridge.
    if -22.4<x<-13.7 and -18<z<-7.5 or 16.5<x<27.5 and -11<z<9.5:continue
    if abs(x)<18.5 and z>17:continue
    if abs(x)<2 and z<18 or abs(z+17)<1.3:continue
    if abs(x)<18 and -15<z<16:
        # Growth hugs graves instead of swallowing their interaction targets.
        near=any(abs(x-s['x'])<.7 and .05<z+s['z']<.8 for s in layout['stupas'])
        if not near:continue
    if abs(x)<2.7 and -33<z<-24:continue
    if z<-26.6 or 12.8<x<19.2 and -25.6<z<-19.2 or -17.2<x<-9.6 and z<-24.8 or x<-24.6 and -3.4<z<13.4:continue
    if any((x-a)**2+(z-b)**2<.9 for a,b in forgotten):continue
    spots.append((x,z))
# The clearing's floor: undergrowth everywhere but the path in and the sala itself.
for k in range(420):
    x,z=rng.uniform(ANNEX[0]+.8,ANNEX[1]-.6),rng.uniform(ANNEX[2]+.6,ANNEX[3]-.6)
    if x<36 and -11.4<z<-6:continue
    if 34.6<x<41.8 and -15.6<z<-2.6:continue
    spots.append((x,z))
understory(AREA,spots,rng)
grass_geometry('pagoda_grasses',AREA,[(x,z,.015) for x,z in spots],rng,size=(.35,.85))
# Fallen boughs and roots at the forest edge, kept off playable aisles.
for k,(x,z) in enumerate(inner):
    if abs(x)>20:
        tube('fallen_bough',AREA,[(x-.8,z+.4,.1),(x+.2,z+.7,.16),(x+1.8,z+1.2,.08)],.13,m['bark'],sides=9,radius_end=.045)
# Memory space: forest-shrine walk kept outside the present's view and collision bounds.
cube('memory_ground',80,0,-.2,22,34,.2,m['earth'],True,surface='dirt')
for k in range(15):
    x,z=80+(-1 if k%2 else 1)*rng.uniform(5,10),rng.uniform(-15,15)
    tropical_tree(AREA,m,x,z,rng.uniform(8,13),100+k,rng,collision=False)
for x in [79.5,80,80.5]:lathe('memory_shrine_stone',AREA,[(.3,0),(.35,.4),(.25,.7),(.05,.9)],x,8,0,m['stone'])
usable('memory_shrine',80,7,.4,lambda:cube('memory_betel_box',80,7,.4,.5,.35,.2,m['silver']))
lamp('memory',80,8,.6)
# The hungry dead of the garden: corpses bound in their burial shrouds (the Pocong
# scan), tied at head, neck, waist and feet as the dead are wrapped for the pyre.
# Feet at each root's origin; the runtime moves and hops each root independently.
sys.path.insert(0,os.path.join(ROOT,'tools/ep2'))
from pagoda_scans import scan,instance
shroud=None
for i in range(5):
    root=anchor('pret_'+str(i),0,0)
    if shroud is None:shroud=body=scan(AREA,'pocong','pret_shroud_'+str(i),height=1.78)
    else:body=instance(AREA,shroud,'pret_shroud_'+str(i),(0,0,0),0,scale=1+.04*((i*7)%3-1))
    adopt(root,[body])
    root.location=(12+i*2,12,0)
# Babylon's glTF import mirrors X. Compensate once, on the authored world root,
# so gameplay, notebook and Blender's named coordinates all use X east/Z south.
world=empty('pagoda_axes',AREA,(0,0,0))
for obj in list(AREA.objects):
    if obj != world and obj.parent is None:obj.parent=world
world.scale.x=-1
# Keep prototyped source collections out of exports.
for o in bpy.context.selected_objects:o.select_set(False)
for o in AREA.all_objects:o.select_set(True)
path=os.path.join(ROOT,'art-source/blender/ep2/ep2_area_pagoda.blend')
os.makedirs(os.path.dirname(path),exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=path)
print('EP2 complete:',len(AREA.all_objects),'objects')
