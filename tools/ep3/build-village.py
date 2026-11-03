"""The Drowned Village: original, editable scenery in Episode 1's real-scale CC0 kit.
blender -b --factory-startup -P tools/ep3/build-village.py
Coordinates below are gameplay X/Y-up/Z; conversion happens exactly once in helpers.
"""
import bpy, json, math, sys, os
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/areas'))
from kit import box, collider, empty, library_material, plain, image_material, mesh_object, lathe, tube, cylinder
from khmer import place, flame
sys.path.insert(0,str(ROOT/'tools/ep3'))
from roof_joint import roof_joint
from lake_characters import finish_lake_characters
from realism_scene import apply_realism

# Reuse the actual MakeHuman anatomy, posing and cloth builder used in Episode 2.
source=(ROOT/'tools/ep2/build-cinematics.py').read_text().split('wood=library_material')[0]
exec(compile(source,str(ROOT/'tools/ep2/build-cinematics.py'),'exec'),globals())
COL.name='ep3_area_village'
rng=np.random.default_rng(19201931)
layout=json.loads((ROOT/'src/episodes/ep3/data/village-layout.json').read_text())
OUT=ROOT/'art-source/textures/ep3';OUT.mkdir(parents=True,exist_ok=True)

def weather(name,base,kind,size=512):
    """Original pigment, tide-lines, spalls and micro-height; normal maps are linear."""
    y,x=np.mgrid[0:size,0:size]/size
    noise=rng.random((size,size));wave=(np.sin(x*17+np.sin(y*19))*np.sin(y*23+x*5))*.5+.5
    cracks=np.exp(-np.abs(np.sin(x*55+np.sin(y*18)*.6))*65)
    mask=np.clip((wave-.46)*3,0,1)
    rgb=np.ones((size,size,3))*base
    rgb*= (.73+noise*.28+wave*.17)[:,:,None]
    if kind=='teal':
        rgb=rgb*(1-mask[:,:,None]*.56)+np.array([.32,.28,.2])*mask[:,:,None]*.56
        rgb*=1-(np.maximum(0,y-.45)*.55+cracks*.4)[:,:,None]
    elif kind=='iron':
        rgb=rgb*(1-mask[:,:,None]*.83)+np.array([.34,.13,.045])*mask[:,:,None]*.83
    else:rgb*=1-cracks[:,:,None]*.55
    rgba=np.dstack((np.clip(rgb,0,1),np.ones((size,size))))
    path=OUT/f'T_ep3_{name}_BC.png'
    img=bpy.data.images.new(name,width=size,height=size);img.pixels=rgba.astype(np.float32).ravel();img.filepath_raw=str(path);img.file_format='PNG';img.save()
    mat=image_material('M_ep3_'+name,str(path),rough=.78,metal=.72 if kind=='iron' else 0,tile=1.8)
    height=noise*.04+wave*.15+cracks*.025
    dy,dx=np.gradient(height);normal=np.dstack((-dx*9,-dy*9,np.ones_like(dx)));normal/=np.linalg.norm(normal,axis=2)[:,:,None]
    n=bpy.data.images.new(name+'_normal',width=size,height=size);n.colorspace_settings.name='Non-Color';n.pixels=np.dstack((normal*.5+.5,np.ones_like(dx))).astype(np.float32).ravel();n.filepath_raw=str(OUT/f'T_ep3_{name}_N.png');n.file_format='PNG';n.save()
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    tex=nodes.new('ShaderNodeTexImage');tex.image=n;nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.65
    links.new(tex.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],nodes['Principled BSDF'].inputs['Normal'])
    return mat

m={}
for key,tex in [('wood','weathered_brown_planks'),('dark','dark_wooden_planks'),('bamboo','bamboo_wall'),('rope','rough_linen'),('paper','clay_plaster'),('cloth','rough_linen'),('clay','red_dirt_mud_01')]:
    m[key]=library_material(tex,'M_ep3_'+key)
m['teal']=weather('tide_marked_teal',(.28,.43,.37),'teal')
m['iron']=weather('oxidised_iron',(.31,.33,.29),'iron')
m['plaster']=weather('mineral_plaster',(.62,.57,.44),'plaster')
for key,c,r,metal in [('brass',(.37,.27,.12),.55,.8),('ink',(.025,.026,.023),.9,0),('ivory',(.67,.62,.48),.88,0),('bottle',(.09,.19,.14),.22,.1),('red',(.32,.07,.035),.82,0),('yellow',(.55,.4,.12),.8,0),('blue',(.1,.21,.25),.8,0),('algae',(.06,.095,.045),.95,0)]:m[key]=plain('M_ep3_'+key,c,rough=r,metal=metal)
m['ember']=plain('M_ep3_ember',(.3,.08,.015),emission=(1,.3,.045),strength=2)
m['rope']=library_material('rough_linen','M_ep3_hemp_rope',colour=(.23,.17,.095))
for key in ['wood','iron','cloth']:m[key].use_backface_culling=False

def cube(name,x,y,z,w,h,d,mat=None,col=False,surface='teak',tilt=(0,0,0)):
    obj=box(name,COL,x-w/2,x+w/2,-z-d/2,-z+d/2,y-h/2,y+h/2,mat,edge=.007,tilt=tilt)
    if col:collider(name,COL,x-w/2,x+w/2,-z-d/2,-z+d/2,y-h/2,y+h/2,surface)
    return obj
def anchor(name,x,y,z,**props):return empty(name,COL,(x,-z,y),**props)
def pipe(name,pts,r,mat):return tube(name,COL,[(x,-z,y) for x,y,z in pts],r,mat,sides=9)
def pot(name,x,y,z,r=.15,h=.3,mat=None):
    return lathe(name,COL,[(0,0),(r*.75,0),(r,.08*h),(r*1.06,.55*h),(r*.65,.9*h),(r*.65,h),(r*.5,h),(r*.5,.88*h),(r*.9,.5*h),(0,.1*h)],x,-z,y,mat or m['clay'],segments=24)
def sign(name,text,x,y,z,size=.2,mat=None,flat=False):
    curve=bpy.data.curves.new(name,'FONT');curve.body=text;curve.size=size;curve.align_x='CENTER';curve.extrude=.0007
    obj=bpy.data.objects.new(name,curve);COL.objects.link(obj);obj.location=(x,-z,y);obj.rotation_euler=(0,0,0) if flat else (math.pi/2,0,0);obj.scale.x=-1;obj['ep3_lettering_corrected']=True;curve.materials.append(mat or m['ivory']);return obj
def usable(name,x,y,z,build):
    before=set(COL.objects);build();objects=[o for o in COL.objects if o not in before and not o.name.startswith('col_') and o.parent is None]
    root=anchor('interact_'+name,x,y,z);bpy.context.view_layer.update()
    for o in objects:
        world=o.matrix_world.copy();o.parent=root;o.matrix_world=world
    return root
def deck(name,x,y,z,w,d,collision=True):
    for i in range(math.ceil(d/.24)):
        zz=z-d/2+(i+.5)*d/math.ceil(d/.24)
        cube(name+'_plank',x,y-.035,zz,w,.07,d/math.ceil(d/.24)-.012,m['wood'])
    if collision:collider(name,COL,x-w/2,x+w/2,-z-d/2,-z+d/2,y-.15,y,'teak')
    for side in [-1,1]:cube(name+'_joist',x+side*(w/2-.12),y-.22,z,.18,.32,d,m['dark'])
def ramp(name,a,b,width=1.8,rail=False):
    a=np.array(a,dtype=float);b=np.array(b,dtype=float);diff=b-a;length=np.linalg.norm(diff[[0,2]]);cross=np.array([-diff[2],0,diff[0]])/length*width/2
    corners=[a-cross,a+cross,b+cross,b-cross];verts=[(p[0],-p[2],p[1]-.13) for p in corners]+[(p[0],-p[2],p[1]) for p in corners]
    obj=mesh_object('col_'+name,COL,verts,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],surface='teak')
    for k in range(math.ceil(length/.26)):
        t=(k+.5)/math.ceil(length/.26);center=a+(b-a)*t;f=diff/math.ceil(length/.26)*.46
        pts=[center-cross-f,center+cross-f,center+cross+f,center-cross+f]
        v=[(p[0],-p[2],p[1]+.006) for p in pts];mesh_object(name+'_board',COL,v,[(0,3,2,1)],m['wood'])
    if rail:
        for side in [-1,1]:
            pts=[tuple(a+cross*side+[0,1,0]),tuple((a+b)/2+cross*side+[0,.84,0]),tuple(b+cross*side+[0,1,0])]
            pipe(name+'_rope',pts,.025,m['rope'])
            for p in [a,b]:pipe(name+'_post',[tuple(p+cross*side),tuple(p+cross*side+[0,1.08,0])],.045,m['dark'])
    return obj
def roof(name,x,z,w,d,eave,ridge):
    # Corrugated metal sheets: rolled ribs have actual relief, rusty hems and individual fixings.
    for side in [-1,1]:
        for j in range(math.ceil(d/1.6)):
            zz=z-d/2+j*1.6;dd=min(1.63,z+d/2-zz);verts=[]
            if dd<.1:continue
            for k in range(41):
                t=k/40;px=x+side*t*w/2;yy=ridge+(eave-ridge)*t+.035*math.sin(k*math.pi*2.5)
                for pz in [zz,zz+dd]:verts.append((px,-pz,yy))
            mesh_object(name+'_corrugated',COL,verts,[(k*2,k*2+1,k*2+3,k*2+2) for k in range(40)],m['iron'])
        for zz in np.arange(z-d/2+.3,z+d/2,2):pipe(name+'_rafter',[(x,ridge-.08,zz),(x+side*w/2,eave-.08,zz)],.045,m['dark'])
    pipe(name+'_ridge',[(x,ridge+.03,z-d/2),(x,ridge+.03,z+d/2)],.075,m['iron'])
def wall(name,x,z,w,d,floor=0):
    # Side walls: tide-stained lower dado, separate window jambs, chipped shutters.
    cube(name+'_dado',x,floor+.42,z,w,.84,d,m['teal'],True)
    cube(name+'_header',x,floor+2.65,z,w,.36,d,m['teal'],True)
    alongz=d>w;length=d if alongz else w;count=max(1,round(length/2.6))
    for j in range(count+1):
        delta=-length/2+j*length/count
        xx=x if alongz else x+delta;zz=z+delta if alongz else z
        cube(name+'_jamb',xx,floor+1.65,zz,.18 if alongz else .25,1.6,.25 if alongz else .18,m['dark'],True)
    for j in range(count):
        delta=-length/2+(j+.5)*length/count;xx=x if alongz else x+delta;zz=z+delta if alongz else z
        for yy in [floor+.92,floor+2.4]:cube(name+'_window_sill',xx,yy,zz,.28 if alongz else length/count-.16,.09,length/count-.16 if alongz else .28,m['wood'])
        for k in range(3):
            if (j+k)%4==0:continue
            cube(name+'_broken_shutter',xx+.02 if alongz else xx+(k-1)*.25,floor+1.65,zz+(k-1)*.3 if alongz else zz,.09 if alongz else .22,1.36,.24 if alongz else .09,m['wood'],tilt=(0,.08*(k-1),.03*(j%2)))
    cube(name+'_algae_line',x,floor+.28,z,w+.014,.055,d+.014,m['algae'])
def table(name,x,y,z,w=1.1,d=.65):
    cube(name+'_top',x,y,z,w,.08,d,m['wood'],True)
    for dx in [-w*.4,w*.4]:
        for dz in [-d*.35,d*.35]:cube(name+'_leg',x+dx,y-.4,z+dz,.065,.8,.065,m['dark'])
def lamp(name,x,y,z):
    cube(name+'_wall_bracket',x,y,z,.16,.32,.1,m['iron'])
    pot(name+'_oil_reservoir',x,y-.12,z+.08,.1,.12,m['brass'])
    pipe(name+'_lamp_cage',[(x-.11,y-.05,z+.09),(x-.11,y+.32,z+.09),(x+.11,y+.32,z+.09),(x+.11,y-.05,z+.09)],.012,m['iron'])
    pot(name+'_chimney',x,y,z+.08,.07,.26,m['ivory'])
    cube(name+'_glow',x,y+.1,z+.09,.045,.1,.045,m['ember'])
    anchor('light_flame_'+name,x,y+.13,z+.15,radius=5,intensity=3.5)
def bed(name,x,z):
    cube(name+'_mattress',x,.68,z,1.05,.14,2,m['cloth'],True)
    for dx in [-.56,.56]:
        pipe(name+'_bed_rail',[(x+dx,.3,z-1),(x+dx,.72,z-1),(x+dx,.72,z+1),(x+dx,.3,z+1)],.023,m['iron'])
    for zz in [-1,1]:
        for dx in [-.42,-.21,0,.21,.42]:pipe(name+'_headboard',[(x+dx,.7,z+zz),(x+dx,1.15,z+zz)],.012,m['iron'])
        pipe(name+'_curved_headboard',[(x-.56,.7,z+zz),(x-.5,1.22,z+zz),(x,1.35,z+zz),(x+.5,1.22,z+zz),(x+.56,.7,z+zz)],.025,m['iron'])
    cube(name+'_pillow',x,.82,z-.65,.7,.12,.4,m['ivory'])
def boat(name,x,z,y=.32,length=5,width=1.5):
    verts=[];n=16
    for j in range(n+1):
        t=j/n;zz=z-length/2+t*length;ww=width/2*math.sin(math.pi*t)**.45+.035
        for xx,yy in [(-ww,.25),(-ww*.8,-.05),(0,-.18),(ww*.8,-.05),(ww,.25)]:verts.append((x+xx,-zz,y+yy))
    mesh_object(name+'_hull',COL,verts,[(j*5+k,j*5+k+1,(j+1)*5+k+1,(j+1)*5+k) for j in range(n) for k in range(4)],m['dark'])
    for zz in np.linspace(z-length*.28,z+length*.28,4):cube(name+'_seat',x,y+.15,zz,width*.8,.07,.27,m['wood'])
    for side in [-1,1]:pipe(name+'_gunwale',[(x+side*(width/2*math.sin(math.pi*j/n)**.45+.035),y+.25,z-length/2+j/n*length) for j in range(n+1)],.035,m['wood'])
    pipe(name+'_oar',[(x-.35,y+.3,z-1),(x+.5,y+.32,z+1.5)],.025,m['wood'])
def human(name,x,y,z,old=False,scale=1):
    root=anchor(name,x,y,z);body=anatomy(name+'_body',old=old);body.parent=root;body.scale=(scale,)*3
    if name!='kanha':
        height=max(v.co.z for v in body.data.vertices)
        polys=[list(p.vertices) for p in body.data.polygons if sum(body.data.vertices[i].co.z for i in p.vertices)/len(p.vertices)>height*.968 or (sum(body.data.vertices[i].co.z for i in p.vertices)/len(p.vertices)>height*.91 and sum(body.data.vertices[i].co.y for i in p.vertices)/len(p.vertices)>.015)]
        mesh=bpy.data.meshes.new(name+'_hair');mesh.from_pydata([v.co+v.normal*.003 for v in body.data.vertices],[],polys);mesh.materials.append(m['ink'])
        hair=bpy.data.objects.new(name+'_hair',mesh);COL.objects.link(hair);hair.parent=body
        for face in mesh.polygons:face.use_smooth=True
    return root,body

# Main flooded hospital: broad walkable wards, pitched iron roof and fifty years of repair.
deck('clinic_ground',0,0,-.5,24,21)
deck('entry_landing',0,.64,12.3,7,5)
ramp('entry_slope',(0,.64,10.5),(0,0,8),3.4)
for xx in [-11.6,-5.8,0,5.8,11.6]:
    for zz in [-10,-4,2,9]:
        pipe('clinic_pile',[(xx,-3.5,zz),(xx,6.4 if abs(xx)>10 else 3.0,zz)],.15,m['dark'])
        for yy in [-.3,.12]:pipe('pile_rope_binding',[(xx-.16,yy,zz-.15),(xx+.16,yy,zz-.15),(xx+.16,yy,zz+.15),(xx-.16,yy,zz+.15),(xx-.16,yy,zz-.15)],.018,m['rope'])
        if zz<8:pipe('diagonal_pile_brace',[(xx,-2,zz),(xx,.0,zz+3.7)],.07,m['wood'])
wall('west_wall',-12,-.5,.18,21);wall('east_wall',12,-.5,.18,21)
wall('north_wall_west',-3.1,-11,17.8,.18)
wall('north_wall_east',10.8,-11,2.4,.18)
wall('front_left',-7,10,10,.18);wall('front_right',7,10,10,.18)
for zz in [3,-5]:
    wall('ward_partition_west',-6.2,zz,6.5,.12)
    wall('ward_partition_east',7.5,zz,8.6,.12)
for xx in [-6,6]:
    for zz in [-7,-1,6]:
        cube('cross_braced_column',xx,1.5,zz,.16,3,.16,m['dark'],True)
roof('hospital_main',3,-.5,19,23,3.0,5.1)
# Upper west doctor's quarters and sheltered purification veranda.
deck('attic_floor_north',-7.1,3.35,-6.9,9.4,7.8)
deck('attic_floor_south',-5.6,3.35,0,6.4,6)
deck('upper_veranda',-12.5,3.35,3,3,15)
wall('attic_north',-7.1,-10.7,9.4,.15,3.35)
wall('attic_west',-11.9,-7.4,.15,6.6,3.35)
roof('attic',-7.1,-4.5,11,15.6,6.15,7.7)
ramp('attic_stair',(-10,0,8),(-10,3.35,-3),1.7,True)
for i in range(27):
    t=(i+.5)/27;cube('stair_nosing',-10,3.35*t+.012,8-11*t,1.65,.05,.05,m['wood'])
table('doctor_desk',-4.8,4.06,-8.9,2,.7)
cube('attic_bed',-8.8,3.72,-8.9,1.2,.7,2.1,m['wood'],True)
cube('attic_bedroll',-8.8,4.1,-8.9,1.12,.12,1.9,m['cloth'])
for k in range(12):cube('medical_books',-4.1+k*.055,4.14,-9,.045,.22+rng.random()*.07,.19,m['red'] if k%3==0 else m['dark'])
usable('stove',-6.3,3.7,-7,lambda:(pot('charcoal_stove',-6.3,3.35,-7,.22,.45,m['iron']),cube('stove_coals',-6.3,3.77,-7,.2,.03,.2,m['ember'])))
lamp('attic',-6.3,4.8,-8)
lamp('entry',0,2.2,11.3);lamp('ward',8.6,2,-7.5);lamp('deck',-12,4.7,7)

# Wards retain places where patients lived: iron frames, suspended muslin, enamel and glass.
for j,(xx,zz) in enumerate([(-7,0),(-4,-2),(5,-1),(8,-6),(-5,-7),(4,6)]):
    bed('ward_bed_'+str(j),xx,zz)
    for dx in [-.7,.7]:pipe('curtain_frame',[(xx+dx,0,zz-1.2),(xx+dx,2.65,zz-1.2),(xx+dx,2.65,zz+1.2)],.018,m['iron'])
    if j%2==0:
        verts=[(xx-.68,-(zz-1.1+k*.2),2.6-h*(1.8+.06*math.sin(k))) for k in range(12) for h in [0,1]]
        mesh_object('torn_muslin_curtain',COL,verts,[(k*2,k*2+1,k*2+3,k*2+2) for k in range(11)],m['cloth'])
    pot('enamel_basin',xx+.75,.04,zz,.22,.14,m['ivory'])
table('reception_desk',-4,1,6,3,1)
cube('filing_cabinet',3,1,-8,1.5,2,.5,m['teal'],True)
for y in [.35,.85,1.35,1.85]:
    cube('drawer_face',3,y,-7.73,1.4,.43,.05,m['iron']);pipe('drawer_handle',[(2.8,y,-7.68),(3.2,y,-7.68)],.012,m['brass'])
for k in range(25):
    xx,zz=rng.uniform(-10,10),rng.uniform(-9,8)
    if abs(xx)<1.7:continue
    obj=cube('floating_patient_file',xx,.3,zz,.21,.008,.3,m['ivory']);obj.rotation_euler.z=rng.uniform(-3,3)
for xx,zz in [(10,-9),(-11,-8),(4,-9)]:
    table('medical_trolley',xx,.88,zz,.8,.55)
    for j in range(6):pot('stoppered_medicine_bottle',xx+(j%3-1)*.16,.94,zz+(j//3-.5)*.16,.035,.12+rng.random()*.06,m['bottle'])
    pot('instrument_tray',xx,.94,zz+.12,.19,.035,m['iron'])
# Raised dry furniture routes avoid forcing the player to jump.
for j,(a,b) in enumerate([((-2,.45,8),(-2,.45,1)),((-2,.45,1),(3,.45,-3)),((3,.45,-3),(8.6,.45,-7.5))]):ramp('dry_boardwalk_'+str(j),a,b,1.2)
ramp('dry_boardwalk_entry',(-2,0,9),(-2,.45,8),1.2)
for p in layout['fuses']:
    table('fuse_stand_'+p['id'],p['x'],p['y']-.07,p['z'],.65,.5)
    def tin(p=p):
        x,y,z=p['x'],p['y'],p['z'];cube('medical_tin',x,y,z,.35,.1,.25,m['iron']);cube('tin_lid',x,y+.11,z-.11,.35,.18,.025,m['iron']);pipe('dry_brass_fuse',[(x-.1,y+.09,z),(x+.1,y+.09,z)],.018,m['brass']);sign('tin_cross','+',x,y+.03,z+.127,.09,m['red'])
    usable('fuse_'+p['id'],p['x'],p['y'],p['z'],tin)
for p in layout['leaks']:
    x,y,z=p['x'],p['y'],p['z']
    usable('seal_'+p['id'],x,y,z,lambda x=x,y=y,z=z:pipe('splintered_window_jamb',[(x,y-.4,z-.45),(x,y+.4,z+.45)],.04,m['wood']))
    for i in range(3):cube('patch_'+p['id']+'_'+str(i),x-.04,y-.3+i*.24,z,.1,.18,1.4,m['wood'])

# A heavy period diesel set and an actual run of pipe leading down to the cellar.
def generator():
    cube('generator_block',7,.5,-8,1.1,.8,1.65,m['iron']);pot('generator_flywheel',7.65,.35,-8,.4,.15,m['iron'])
    for j in range(9):cube('generator_cooling_fin',7,.91,-8.6+j*.14,.9,.1,.035,m['iron'])
    pot('generator_fuel_tank',7.1,1.02,-8,.23,.28,m['iron']);pipe('generator_crank',[(6.4,.65,-7.6),(6.15,.65,-7.6),(6.15,.85,-7.6)],.025,m['brass'])
    for j in range(3):pot('porcelain_fuse_socket',6.65+j*.32,1.03,-7.5,.06,.13,m['ivory'])
    pipe('pump_discharge',[(7,.25,-8),(9,.25,-8),(9,-1,-15),(7,-1.2,-20)],.085,m['iron'])
usable('generator',7,.85,-8,generator)
sign('pump_label','DRAINAGE / THREE DRY FUSES',7,1.18,-7.16,.1)
deck('vault_floor',0,-1.6,-23,14,9)
wall('vault_back',0,-27.5,14,.22,-1.6);wall('vault_west',-7,-23,.22,9,-1.6)
ramp('vault_ramp',(7.7,0,-9.5),(7.7,-1.6,-20.5),2.2,True)
deck('vault_threshold',7,-1.6,-21,3.6,2.5)
cube('vault_ceiling',0,1.2,-23,14,.17,9,m['dark'])
for xx in [-6,-3,0,3,6]:pipe('vault_beam',[(xx,1.05,-27.5),(xx,1.05,-18.5)],.08,m['dark'])
def safe():
    cube('iron_safe_case',0,-.8,-26,1.8,1.6,1.05,m['iron'],True)
    cube('safe_door',0,-.8,-25.42,1.58,1.38,.08,m['iron'])
    for xx in [-.78,.78]:pipe('safe_hinge',[(xx,-1.4,-25.34),(xx,-.25,-25.34)],.045,m['brass'])
    pipe('safe_handle',[(.55,-1,-25.3),(.55,-.5,-25.3)],.035,m['brass'])
    sign('safe_numerals','0  1  2  3',0,-.5,-25.34,.16)
usable('safe',0,-.7,-25.35,safe)
usable('jar',0,-.58,-25.1,lambda:pot('terracotta_seal_jar',0,-.58,-25.1,.16,.33,m['clay']))
table('vault_ritual_table',-2,-.63,-24,1.4,.8)
usable('scrape',-2,-.55,-24,lambda:cube('debt_slab',-2,-.55,-24,.7,.035,.45,m['clay']))
usable('write',-1.7,-.5,-24,lambda:pipe('ink_stylus',[(-1.9,-.5,-24),(-1.5,-.5,-24.1)],.008,m['dark']))
sign('debt_name','VUTHY',-2,-.525,-24,.12,m['ink'],flat=True)
lamp('vault',-4,.15,-24)

notes={'admission':(-3,1.1,7),'mother':(-7.5,4.1,-5),'calendar':(-4.5,4.1,-9),'letter':(-1.4,-.55,-26),'return':(3,1.1,-8)}
for id,(x,y,z) in notes.items():
    if id in ['admission','mother']:table('note_table',x,y-.1,z,.7,.55)
    usable('note_'+id,x,y,z,lambda x=x,y=y,z=z:cube('folded_document',x,y,z,.32,.016,.43,m['ivory']))
    for j in range(7):cube('written_ink_line',x,y+.009,z-.12+j*.035,.2-.015*(j%3),.001,.002,m['ink'])
# Always-accessible duplicate key in reception; no optional clue can block completion.
usable('calendar_key',-3.9,1.2,7.2,lambda:cube('torn_calendar_key',-3.9,1.2,7.2,.34,.02,.4,m['ivory']))
for j,(x,z) in enumerate([(-12.45,4.5),(-11.6,4.5),(-12,5.3)]):
    usable('candle_'+str(j),x,3.47,z,lambda x=x,z=z:pot('yellow_candle',x,3.35,z,.045,.19,m['yellow']))
    cube('ritual_flame_'+str(j),x,3.58,z,.025,.06,.025,m['ember'])
usable('purify',-12,3.65,5,lambda:pot('purification_bowl',-12,3.35,5,.16,.09,m['brass']))
usable('mother_choice',-12,4.15,3.8,lambda:pipe('extra_candle', [(-12,3.35,3.8),(-12,3.6,3.8)],.035,m['yellow']))

# The escape is continuous, physically collidable, and wide enough for the controller.
for j,(a,b) in enumerate(zip(layout['escape'],layout['escape'][1:])):
    ramp('escape_roof_'+str(j),a,b,2.0,True)
for j,p in enumerate(layout['escape']):roof_joint(COL,m['wood'],'escape_turn_'+str(j),p)
deck('last_stilt',-22,5.5,-18,3.4,3.4)
for dx in [-1.3,1.3]:pipe('last_stilt_pile',[(-22+dx,-3,-18),(-22+dx,6.7,-18)],.17,m['dark'])
usable('rescue',-22,5.9,-18,lambda:pipe('rescue_bell',[(-22,5.6,-18),(-22,6.2,-18)],.04,m['brass']))
boat('sora_moored_boat',4.7,14.5);pipe('cut_mooring_rope',[(3,.7,13),(4,.5,14),(4.7,.5,14.5)],.025,m['rope'])
sign('clinic_facade','TONLE SAP  /  DISPENSAIRE',0,2.65,10.14,.27)
sign('ward_sign','MATERNITY / 1920',-6,2.3,3.1,.17)
sign('attic_sign','DOCTOR / RECORDS',-7,5.7,-3,.17)

# Market: connected floating walkways with an inhabited, late-afternoon palette.
deck('market_main',-64,.7,2,7,22)
for j,(x,z) in enumerate([(-72,-5),(-56,-6),(-72,4),(-56,3),(-64,-13)]):
    deck('market_house_'+str(j),x,.7,z,7,6)
    if x!=-64:ramp('market_link_'+str(j),(-64,.7,z),(x,.7,z),2.2,True)
    wall('market_house_back',x,z-2.8,7,.1,.7)
    for dx in [-3.2,3.2]:
        for dz in [-2.6,2.6]:pipe('market_house_post',[(x+dx,-1,z+dz),(x+dx,3.6,z+dz)],.07,m['wood'])
    roof('market_house_roof',x,z,8,7,3.4,4.5)
    for k in range(5):
        cube('market_float',x-2.5+k*1.25,.05,z,.8,.45,5.5,m['bamboo'])
    if j<4:
        table('seller_stall',x,1.4,z+1.3,3,.9)
        for k in range(12):
            xx=x-1.25+(k%6)*.5;zz=z+1.15+(k//6)*.35
            pot('market_produce_basket',xx,1.45,zz,.18,.17,m['bamboo'])
            for l in range(3):pot('fruit_or_fish',xx+(l-1)*.075,1.57,zz,.055,.08,m['yellow'] if j%2 else m['bottle'])
        cube('market_awning',x,2.65,z+1.3,3.7,.05,2,m[['red','yellow','blue'][j%3]])
    boat('market_sampan_'+str(j),x+4.3,z+2,length=4.8,width=1.3)
ramp('lok_raft_link',(-64,.7,11),(-71,.7,12),2.2,True);deck('lok_raft',-72,.7,13,6,5)
for k in range(8):pipe('raft_bamboo', [(-74.6+k*.7,.2,10.2),(-74.6+k*.7,.2,15.8)],.16,m['wood'])
boat('lok_sampan',-77,13,length=6,width=1.8)
for j,(name,x,z,old) in enumerate([('seller',-71,4,False),('vuthy',-63,-3,True),('lok',-72,12,True)]):
    def person(name=name,x=x,z=z,old=old):
        root,body=human('npc_'+name,x,.7,z,old=old)
        garment(name+'_sampot',body,[(.18,.04),(.22,.15),(.21,.6),(.17,.85)],m['cloth'],pleats=.004)
        if name=='lok':
            pot('lok_hat',x,2.25,z,.25,.12,m['bamboo']);pipe('fishing_pole',[(x-.5,.8,z),(x-.6,3.2,z-.5)],.012,m['wood'])
    usable(name,x,1.6,z,person)
for j,(x,z) in enumerate([(-56,-6),(-72,-5),(-56,3),(-64,-13)]):human('market_resident_'+str(j),x,.7,z,old=j%2==0,scale=.83 if j==3 else 1)
usable('boat',-74,.9,14.2,lambda:pipe('borrowed_oar',[(-74,.86,13.6),(-74,.86,14.9)],.03,m['wood']))
lamp('lok_lamp',-73.7,1.4,12.3)
# Net loops, drying fish, woven traps, washing and mooring stakes give the docks human scale.
for j in range(18):
    x,z=-80+rng.random()*32,-17+rng.random()*34
    if -68<x<-60:continue
    pipe('mooring_stake',[(x,-2,z),(x,1.6,z)],.04,m['dark'])
    if j%3==0:
        pot('fish_trap',x,.75,z,.27,.6,m['bamboo'])
        for k in range(10):
            a=k*math.tau/10;pipe('trap_reed',[(x+.23*math.cos(a),.75,z+.23*math.sin(a)),(x+.12*math.cos(a),1.35,z+.12*math.sin(a))],.007,m['wood'])

# Kanha is built from the same anatomical source as Sora, with actual layered wet hair.
root,body=human('kanha',0,-1.5,0)
body.data.materials[1]=m['ivory'];body.data.materials[2]=m['cloth']
garment('kanha_wet_sampot',body,[(.2,.08),(.23,.25),(.19,.7),(.16,.9)],m['cloth'],pleats=.008)
kanha_root,kanha_body=root,body
root,body=human('pich',0,0,0,scale=.48);body.data.materials[1]=m['ivory']
finish_lake_characters(COL,kanha_root,kanha_body,body,m)
# Sparse flooded forest silhouettes, broken nets and debris beyond the clinic.
for k in range(28):
    x,z=rng.uniform(-36,30),rng.uniform(-43,-31)
    pipe('drowned_tree',[(x,-2,z),(x+.2,3,z),(x-.2,5+rng.random()*3,z+.2)],.12,m['dark'])
    for side in [-1,1]:pipe('drowned_branch',[(x,2.5,z),(x+side*1.2,4,z+.3),(x+side*2.3,4.3,z)],.055,m['dark'])
for k in range(25):
    x,z=rng.uniform(-22,22),rng.uniform(-15,18)
    if abs(x)<13:continue
    o=cube('lake_driftwood',x,.08,z,rng.uniform(.4,1.5),.08,.13,m['wood']);o.rotation_euler.z=rng.uniform(0,math.tau)

# Story-bearing decay: real broken joinery, suspended lines, instruments and ragged netting.
from house_detail import corner_web
for j,(x,z) in enumerate([(-11,-9),(10,-8),(-8,2),(5,2),(11,8),(-10,-4)]):
    corner_web('clinic_web_'+str(j),COL,(x,-z,2.6),(0,1,0),(0,0,-1),.55)
    pipe('sagging_clinic_wire',[(x,2.75,z),(x+1.1,2.25,z+.3),(x+2.1,2.7,z+.6)],.009,m['ink'])
for k in range(45):
    side=-1 if k%2 else 1;x=side*rng.uniform(10.1,11.6);z=rng.uniform(-9.8,8.8)
    cube('drifted_wall_debris',x,.03,z,rng.uniform(.08,.3),rng.uniform(.02,.06),rng.uniform(.15,.5),m['wood'] if k%3 else m['iron'],tilt=(.02,0,rng.uniform(-2,2)))
for j in range(5):
    x=9.7+j*.085
    pipe('surgical_forceps',[(x,.96,-8.9),(x+.015,.96,-8.65),(x+.04,.96,-8.57)],.004,m['iron'])
    pipe('forceps_finger_ring',[(x+.018*math.cos(a),.96,-8.92+.024*math.sin(a)) for a in np.linspace(0,math.tau,12)],.003,m['iron'])
for side in [-1,1]:
    for i in range(18):
        a=-11+i*.65
        pipe('dock_fishing_net',[(side*13,.15,a),(side*13.4,-.8,a+.4),(side*13.1,-1.4,a+.5)],.004,m['rope'])
    for h in [-.3,-.7,-1.1]:pipe('dock_fishing_net_weft',[(side*(13.1+.12*math.sin(k)),h,-11+k*.65) for k in range(18)],.004,m['rope'])
# Loose beams get independent animation during the collapse; their clearance is outside the route.
for j,(x,z) in enumerate([(10,7),(8,-9),(-8,-9)]):
    root=anchor('collapse_beam_'+str(j),x,2.8,z)
    obj=cube('split_hanging_beam',x,2.8,z,2.6,.12,.16,m['wood']);bpy.context.view_layer.update();worldmat=obj.matrix_world.copy();obj.parent=root;obj.matrix_world=worldmat
    pipe('frayed_beam_rope',[(x,3,z),(x-.8,2.4,z)],.016,m['rope'])

# Close-view scene craft follows main's photographed props and layered decay.
apply_realism(COL)
# Compensate Babylon's left-handed glTF import exactly as Episode 2 does.
world=anchor('village_axes',0,0,0)
for obj in list(COL.objects):
    if obj!=world and obj.parent is None:obj.parent=world
world.scale.x=-1
for obj in COL.objects:
    if obj.type=='MESH':
        for p in obj.data.polygons:
            if 'hair' in obj.name or 'hull' in obj.name:p.use_smooth=True
path=ROOT/'art-source/blender/ep3/ep3_area_village.blend';path.parent.mkdir(parents=True,exist_ok=True)
# The glTF exporter only ships meshes; retain real, readable raised lettering.
for obj in list(COL.objects):
    if obj.type=='FONT':
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.convert(target='MESH')
from compact_source import compact_source
compact_source()
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
print('EP3 authored:',len(COL.all_objects),'objects')
