"""Author Episode 2's living harvest, famine village, and seated Sophal.
Uses the same CC0 MakeHuman anatomy and Poly Haven/cloth kit as Episode 1.
blender -b --factory-startup -P tools/ep2/build-cinematics.py
Exports are optimized with npm run assets -- ep2/ep2_cinematics.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Quaternion
ROOT=Path(__file__).resolve().parents[2]
ROBE_EDGE=[]
import os
LEG=[float(v) for v in os.environ.get('MONK_LEG','60,75,-60,150').split(',')]
HAND=[float(v) for v in os.environ.get('MONK_HAND','.6,.2,2.4').split(',')]
BUDDHA_HAND=[float(v) for v in os.environ.get('BUDDHA_HAND','1.35,-.15,2.9').split(',')]
GHOST=[float(v) for v in os.environ.get('GHOST_POSE','2,72,8,12,6,22').split(',')]
sys.path.insert(0,str(ROOT/'tools/areas'))
from kit import box,empty,library_material,image_material,plain,lathe,tube,world_uvs
from khmer import place
bpy.ops.wm.read_factory_settings(use_empty=True)
COL=bpy.data.collections.new('ep2_cinematics');bpy.context.scene.collection.children.link(COL)
def adopt(obj,parent):
    world=obj.matrix_world.copy();obj.parent=parent;obj.matrix_world=world

def garment(name,parent,profile,mat,center=(0,0,0),pleats=.012):
    # Closed, continuous cloth silhouette, with proper UVs and small hanging folds.
    o=lathe(name,COL,profile,0,0,0,mat,segments=64)
    for v in o.data.vertices:
        a=math.atan2(v.co.y,v.co.x);r=math.hypot(v.co.x,v.co.y)
        if r>.12:
            d=pleats*math.sin(a*18)*(1-min(1,v.co.z/1.5)*.5)
            v.co.x+=math.cos(a)*d;v.co.y+=math.sin(a)*d
    for f in o.data.polygons:f.use_smooth=True
    o.parent=parent;o.location=center
    return o

def anatomy(name,old=False,monk=False,ghost=False,hands=None):
    source=ROOT/('art-source/library/makehuman-sok' if old else 'art-source/library/makehuman-sora')
    verts,uvs,faces,faceuv=[],[],[],[];group=''
    for line in (source/'base.obj').read_text().splitlines():
        a=line.split()
        if not a:continue
        if a[0]=='v':verts.append(Vector(map(float,a[1:4])))
        elif a[0]=='vt':uvs.append(tuple(map(float,a[1:3])))
        elif a[0]=='g':group=a[1]
        elif a[0]=='f' and group=='body':
            data=[p.split('/') for p in a[1:]];faces.append([int(p[0])-1 for p in data]);faceuv.append([int(p[1])-1 for p in data])
    targets=['asian-male-old.target','universal-male-old-minmuscle-averageweight.target'] if old else ['asian-female-young.target','universal-female-young-averagemuscle-averageweight.target']
    for target in targets:
        for line in (source/target).read_text().splitlines():
            if line and not line.startswith('#'):
                a=line.split();verts[int(a[0])]+=Vector(map(float,a[1:4]))
    used=sorted({i for f in faces for i in f});remap={i:n for n,i in enumerate(used)}
    mesh=bpy.data.meshes.new(name+'_anatomy');mesh.from_pydata([verts[i] for i in used],[],[[remap[i] for i in f] for f in faces]);mesh.update()
    uv=mesh.uv_layers.new(name='MakeHumanUV')
    for poly,indices in zip(mesh.polygons,faceuv):
        for loop,index in zip(poly.loop_indices,indices):uv.data[loop].uv=uvs[index]
    body=bpy.data.objects.new(name,mesh);COL.objects.link(body)
    for poly in mesh.polygons:poly.use_smooth=True
    skeleton=json.loads((source/'default.mhskel').read_text())
    def joint(n):return sum((verts[i] for i in skeleton['joints'][n]),Vector())/len(skeleton['joints'][n])
    arm=bpy.data.armatures.new(name+'_rig');rig=bpy.data.objects.new(arm.name,arm);COL.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for n,b in skeleton['bones'].items():
        bone=arm.edit_bones.new(n);bone.head=joint(b['head']);bone.tail=joint(b['tail'])
    for n,b in skeleton['bones'].items():
        if b['parent']:arm.edit_bones[n].parent=arm.edit_bones[b['parent']]
    bpy.ops.object.mode_set(mode='OBJECT')
    regions={}
    for n,weights in json.loads((source/'default_weights.mhw').read_text())['weights'].items():
        g=body.vertex_groups.new(name=n)
        for i,w in weights:
            if i in remap:
                g.add([remap[i]],w,'REPLACE')
                if w>regions.get(remap[i],('',0))[1]:regions[remap[i]]=(n,w)
    mod=body.modifiers.new('Weighted_human_motion','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True
    def rotate(n,axis,angle):
        if n not in rig.pose.bones:return
        b=rig.pose.bones[n];q=b.bone.matrix_local.to_quaternion();b.rotation_mode='QUATERNION';b.rotation_quaternion=b.rotation_quaternion@(q.inverted()@Quaternion(Vector(axis),math.radians(angle))@q)
    ik=[]
    if monk:
        for side,sign in [('L',1),('R',-1)]:
            target=bpy.data.objects.new(name+'_lap_'+side,None);COL.objects.link(target)
            constraint=rig.pose.bones['lowerarm01.'+side].constraints.new('IK')
            constraint.target=target;constraint.chain_count=2
            ik.append((target,sign))
    floor=min(verts[i].y for i in used)
    def local(v):return Vector((v.x*.1,-v.z*.1,(v.y-floor)*.1))
    def pose(kind):
        for b in rig.pose.bones:b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion()
        for side,sign in [('L',-1),('R',1)]:
            rotate('upperarm01.'+side,(0,0,1),sign*34)
            rotate('lowerarm01.'+side,(1,0,0),-18)
            for finger in range(1,6):
                for part in [2,3]:rotate(f'finger{finger}-{part}.{side}',(0,1,0),sign*12)
            if monk:
                # Cross-legged: thighs splayed out flat, turned out, shins folded in beneath.
                rotate('upperleg01.'+side,(0,1,0),sign*LEG[0])
                rotate('upperleg01.'+side,(1,0,0),-LEG[1])
                rotate('upperleg01.'+side,(0,1,0),sign*LEG[2])
                rotate('lowerleg01.'+side,(1,0,0),LEG[3])
                rotate('lowerarm01.'+side,(1,0,0),-50)
                rotate('upperarm01.'+side,(0,0,1),-sign*10)
            elif kind in ['left','right','clap']:
                direction=-1 if kind=='left' else 1
                rotate('upperarm01.'+side,(0,0,1),-sign*(22 if kind!='clap' else 36))
                rotate('lowerarm01.'+side,(1,0,0),-35 if kind!='clap' else -64)
                rotate('wrist.'+side,(0,1,0),sign*12)
                rotate('upperleg01.'+side,(1,0,0),direction*sign*7)
                rotate('lowerleg01.'+side,(1,0,0),8)
                rotate('head',(0,0,1),direction*3)
            elif ghost:
                # The apparition: hunched, arms reaching out at the viewer, knees giving.
                rotate('upperarm01.'+side,(0,0,1),-sign*GHOST[0])
                # MakeHuman rests in a T-pose: swing the arms forward about the vertical.
                rotate('upperarm01.'+side,(0,1,0),sign*GHOST[1])
                rotate('lowerarm01.'+side,(1,0,0),-GHOST[2])
                for finger in range(1,6):
                    for part in [1,2,3]:rotate(f'finger{finger}-{part}.{side}',(1,0,0),-14 if finger>1 else 0)
                rotate('upperleg01.'+side,(1,0,0),-14)
                rotate('lowerleg01.'+side,(1,0,0),22)
            elif kind=='famine':
                rotate('spine01',(1,0,0),18);rotate('head',(1,0,0),18)
                rotate('upperleg01.'+side,(1,0,0),-55);rotate('lowerleg01.'+side,(1,0,0),80)
        if monk:
            hip=(rig.pose.bones['pelvis.L'].head+rig.pose.bones['pelvis.R'].head)*.5
            for n,(target,sign) in enumerate(ik):
                h=hands[n] if hands else (sign*HAND[0],HAND[1],HAND[2])
                target.location=hip+Vector(h)
        if kind=='listen':rotate('head',(0,1,0),-7);rotate('neck01',(1,0,0),4)
        if ghost:
            rotate('spine01',(1,0,0),GHOST[3]);rotate('spine03',(1,0,0),GHOST[3]*.8)
            rotate('neck01',(1,0,0),GHOST[4]);rotate('head',(0,0,1),GHOST[5]);rotate('head',(1,0,0),-20)
        bpy.context.view_layer.update()
    poses={}
    eyes=[]
    for kind in (['rest','listen'] if monk else ['rest'] if ghost else ['rest','left','right','clap','famine']):
        pose(kind);ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());out=ev.to_mesh()
        points=[local(v.co) for v in out.vertices];ev.to_mesh_clear()
        # Keep a planted foot in every authored pose; the runtime adds only a subtle weight shift.
        drop=min(v.z for v in points)
        poses[kind]=[Vector((v.x,v.y,v.z-drop)) for v in points]
        if kind=='rest' and 'eye.L' in rig.pose.bones:
            for n in ('eye.L','eye.R','head'):
                b=rig.pose.bones[n];eyes.append((local(b.head)-Vector((0,0,drop)),local(b.tail)-Vector((0,0,drop))))
    body.modifiers.clear();bpy.data.objects.remove(rig,do_unlink=True)
    for target,_ in ik:bpy.data.objects.remove(target,do_unlink=True)
    for vertex,p in zip(mesh.vertices,poses['rest']):vertex.co=p
    mesh.update();body.shape_key_add(name='Basis')
    for kind,points in poses.items():
        if kind=='rest':continue
        key=body.shape_key_add(name=kind);key.value=0
        for vertex,p in zip(key.data,points):vertex.co=p
    if ghost:
        skin=image_material(name+'_skin',ghost_skin(source/'young_lightskinned_female_diffuse3.png'),rough=.55)
    else:
        skin=image_material(name+'_skin',str(source/('old_lightskinned_male_diffuse2.png' if old else 'young_lightskinned_female_diffuse3.png')),rough=.83,tint=(.63,.48,.34))
    cloth=library_material('rough_linen',name+'_cloth',colour=(.36,.045,.003) if monk else (.2,.012,.012) if ghost else (.19,.21,.16))
    wrap=library_material('rough_linen',name+'_wrap',colour=(.46,.23,.065) if monk else (.16,.01,.01) if ghost else (.3,.16,.11))
    body.data.materials.clear()
    for mat in [skin,cloth,wrap]:body.data.materials.append(mat)
    # Bone regions keep cloth off the face in every baked pose, including seated poses.
    for poly in mesh.polygons:
        names=[regions.get(i,('',0))[0] for i in poly.vertices]
        torso=sum(n.startswith(('spine','pelvis','root')) for n in names)
        leg=sum(n.startswith(('upperleg','lowerleg')) for n in names)
        sleeve=sum(n.startswith('upperarm') for n in names)
        poly.material_index=2 if leg>len(names)/2 else 1 if torso+sleeve>len(names)/2 else 0
    if monk:
        # A Theravada robe: body, legs and left arm covered; the right shoulder, upper
        # chest and arm bare along a diagonal edge from left shoulder to right armpit.
        def centre(n):
            pts=[mesh.vertices[i].co for i,(r,w) in regions.items() if r==n]
            return sum(pts,Vector())/len(pts) if pts else None
        # The world root mirrors X, so MakeHuman's left side is the figure's right in game.
        right=1 if centre('upperarm01.L').x>0 else -1
        # The top of the upper arm, not its middle: the arms hang down at his sides.
        shoulder=max(mesh.vertices[i].co.z for i,(r,w) in regions.items() if r.startswith('upperarm01'))
        def bare(c):
            u=c.x*right
            return u>-.19 and c.z>shoulder+.03-(u+.19)*.55
        for poly in mesh.polygons:
            names=[regions.get(i,('',0))[0] for i in poly.vertices]
            main=max(set(names),key=names.count)
            c=poly.center
            if main.startswith(('head','neck','jaw','eye','tongue','teeth','special','temporalis','oculi','levator','orbicularis','risorius')) or 'finger' in main or main.startswith(('wrist','metacarpal','hand')):
                poly.material_index=0
            elif main.startswith(('upperarm','lowerarm')):
                poly.material_index=0 if main.endswith('.L') else 1
            elif main.startswith(('upperleg','lowerleg','foot','toe','ankle')):
                poly.material_index=1
            else:
                poly.material_index=0 if bare(c) else 1
        global ROBE_EDGE
        ROBE_EDGE=[]
        for u in [-.19+k*.035 for k in range(11)]:
            z=shoulder+.03-(u+.19)*.55
            near=[v.co for v in mesh.vertices if abs(v.co.x*right-u)<.03 and abs(v.co.z-z)<.03]
            if near:
                front=min(near,key=lambda v:v.y)
                ROBE_EDGE.append((front.x,front.y-.012,front.z-.014))
        # Ease the stepped face boundary into one continuous rolled hem.
        for _ in range(3):
            ROBE_EDGE=[ROBE_EDGE[0]]+[tuple((ROBE_EDGE[k-1][d]+2*ROBE_EDGE[k][d]+ROBE_EDGE[k+1][d])/4 for d in range(3)) for k in range(1,len(ROBE_EDGE)-1)]+[ROBE_EDGE[-1]]
    # Closed garment shells keep the shirt and wrapped waist visibly separate from skin.
    # Each garment vertex moves once (not once per face), or the cloth blisters.
    lifted={i for poly in mesh.polygons if poly.material_index for i in poly.vertices}
    for index in lifted:
        mesh.vertices[index].co+=mesh.vertices[index].normal*(0 if monk else .008)
    print('Authored',name,len(mesh.polygons),'faces',flush=True)
    body['eyes']=[list(c) for pair in eyes for c in pair]
    return body

def ghost_skin(source):
    """The dead woman's skin from Sora's own atlas: bloodless grey-blue, mottled with
    lividity, split by a network of dry cracks with darkened edges and blue veins."""
    import numpy as np
    sys.path.insert(0,str(ROOT/'tools/areas'))
    from weathering import cracks, fbm
    img=bpy.data.images.load(str(source),check_existing=False)
    w,h=img.size;px=np.empty(w*h*4,np.float32);img.pixels.foreach_get(px);px=px.reshape(h,w,4)
    rng=np.random.default_rng(1932)
    lum=px[:,:,:3].mean(axis=2)
    size=w
    rot=fbm(size,rng,((5,.5),(13,.3),(31,.2)))
    rgb=lum[:,:,None]*np.array([.62,.66,.68])*(.85+.3*rot[:,:,None])
    livid=np.clip((rot-.6)*3,0,1)[:,:,None]
    rgb=rgb*(1-livid*.5)+np.array([.18,.17,.22])*livid*.5
    crack=cracks(size,rng,count=420)
    edge=np.zeros_like(crack)
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(2,0),(0,2)):edge|=np.roll(np.roll(crack,dx,0),dy,1)
    rgb[edge&~crack]*=.55
    rgb[crack]=np.array([.05,.03,.03])
    vein=cracks(size,rng,count=160)
    rgb[vein&~crack]=rgb[vein&~crack]*.6+np.array([.12,.16,.3])*.4
    px[:,:,:3]=np.clip(rgb,0,1)
    out=str(ROOT/'art-source/textures/ep2/T_ep2_ghost_skin_BC.png')
    new=bpy.data.images.new('T_ep2_ghost_skin_BC',w,h,alpha=True);new.pixels.foreach_set(px.ravel())
    new.filepath_raw=out;new.file_format='PNG';new.save();bpy.data.images.remove(img)
    return out

wood=library_material('weathered_brown_planks','M_memory_teak',tint=(.5,.38,.3))
post=library_material('weathered_planks','M_memory_post',tint=(.66,.6,.54))
thatch=library_material('thatch_roof_angled','M_memory_thatch',tint=(.62,.55,.48));thatch.use_backface_culling=False
straw=plain('M_memory_rice_straw',(.37,.29,.13),rough=.92)
ash=plain('M_memory_ash',(.075,.063,.05),rough=1)
paper=plain('M_memory_paper',(.63,.56,.43),rough=.94)
root=empty('harvest_village',COL,(80,0,0))
# Shallow stilt huts and empty granaries frame the same clear forest path.
for k,(x,y) in enumerate([(72,-1),(88,1),(73,9),(87,10)]):
    start=set(COL.objects)
    for px in [x-1.6,x+1.6]:
        for py in [y-1.5,y+1.5]:box('memory_hut_post',COL,px-.07,px+.07,py-.07,py+.07,0,2.8,post)
    box('memory_hut_floor',COL,x-1.8,x+1.8,y-1.7,y+1.7,.4,.47,wood)
    box('memory_hut_wall',COL,x-1.8,x+1.8,y+1.6,y+1.7,.45,2.4,wood)
    for side in [-1,1]:
        box('memory_hut_side',COL,x+side*1.75-.05,x+side*1.75+.05,y-1.6,y+1.6,.45,2.4,wood)
        o=box('memory_hut_thatch',COL,x+side*.9-.95,x+side*.9+.95,y-2,y+2,2.6,2.7,thatch,tilt=(0,side*math.radians(25),0))
    for o in list(COL.objects):
        if o not in start and o.parent is None:adopt(o,root)
    basket=place(COL,'wicker_basket_01',(x,y,.48),scale=.65,name='memory_basket_'+str(k))
    if basket:adopt(basket,root)
# Filled rice sheaves appear only during the harvest, then cut to empty baskets.
food=empty('harvest_rice',COL,(80,0,0))
for k in range(12):
    x,y=76+(k%4)*2.6,-1+(k//4)*.4
    o=lathe('harvest_rice_sheaf',COL,[(.08,0),(.11,.2),(.2,.45),(.12,.65)],x,y,.05,straw,segments=12);adopt(o,food)
fire=empty('harvest_fire',COL,(80,-3,0))
for k in range(7):
    a=k*math.tau/7
    o=tube('harvest_log',COL,[(80+math.cos(a)*.5,-3+math.sin(a)*.5,.04),(80-math.cos(a)*.35,-3-math.sin(a)*.35,.13)],.05,wood,sides=8);adopt(o,fire)
# Actual people, never the guardian's ghost model. Child proportions are separate instances.
adult=anatomy('harvest_woman')
festival_shirt=library_material('rough_linen','harvest_indigo_shirt',colour=(.055,.12,.15))
festival_wrap=library_material('rough_linen','harvest_oxblood_wrap',colour=(.23,.065,.04))
for k,(x,y,scale) in enumerate([(77.4,-2,1),(82.6,-2,.98),(78.2,-5,.68),(81.8,-5,.74)]):
    person=empty('harvest_person_'+str(k),COL,(x,y,0))
    obj=adult if k==0 else adult.copy()
    if k:COL.objects.link(obj);obj.data=adult.data.copy()
    obj.parent=person;obj.location=(0,0,0);obj.scale=(scale,scale,scale)
    person.rotation_euler.z=(.15 if k%2 else -.15)
    dress=empty('harvest_garments_'+str(k),COL,(0,0,0));dress.parent=person;dress.scale=(scale,scale,scale)
    garment('harvest_wrapped_skirt',dress,[(.22,.1),(.24,.17),(.23,.45),(.2,.66),(.15,.82)],festival_wrap,pleats=.008)
    garment('harvest_linen_shirt',dress,[(.16,.72),(.15,.85),(.2,1.02),(.23,1.13),(.17,1.23),(.085,1.27)],festival_shirt,pleats=.004)
# Seated, living head monk in the kuti; distinct from the mortuary/guardian presentation.
monk=anatomy('sophal_living',old=True,monk=True)
monk.location=(-18,-11,.2)
robe=library_material('rough_linen','sophal_saffron_drape',colour=(.33,.04,.003),tile=.35)
# Plain dyed cotton on the body: the linen texture shrinks to scales on the body's UVs.
body_robe=plain('sophal_saffron_robe',(.34,.05,.004),rough=.93);body_robe.use_backface_culling=False
monk.data.materials[1]=body_robe;monk.data.materials[2]=body_robe
robe.use_backface_culling=False
# The robe region of the body is smoothed until no anatomy shows through it, lifted off
# the skin and given hanging folds; the same offset goes into every baked pose.
keys=monk.data.shape_keys.key_blocks
faces_of={}
for poly in monk.data.polygons:
    for i in poly.vertices:faces_of.setdefault(i,set()).add(poly.material_index)
robe_v=[i for i,mats in faces_of.items() if mats=={1}]
near={i:set() for i in robe_v}
for e in monk.data.edges:
    a,b=e.vertices
    if a in near:near[a].add(b)
    if b in near:near[b].add(a)
basis=[k.co.copy() for k in keys['Basis'].data]
pos={i:basis[i].copy() for i in robe_v}
# Rings of distance from the robe's edge, so the lift fades out where it meets skin.
ring={i:0 for i in robe_v if any(j not in near for j in near[i])}
frontier=list(ring)
while frontier:
    nxt=[]
    for i in frontier:
        for j in near[i]:
            if j in near and j not in ring:ring[j]=ring[i]+1;nxt.append(j)
    frontier=nxt
for _ in range(int(os.environ.get("ROBE_SMOOTH","30"))):
    pos={i:pos[i].lerp(sum((pos.get(j,basis[j]) for j in near[i]),Vector())/max(1,len(near[i])),.65) for i in robe_v}
# Lift along the smoothed cloth's own normals, not the body's (they bring the anatomy back).
for i in robe_v:monk.data.vertices[i].co=pos[i]
monk.data.update()
normal={i:monk.data.vertices[i].normal.copy() for i in robe_v}
for i in robe_v:monk.data.vertices[i].co=basis[i]
for i in robe_v:
    n=normal[i]
    c=pos[i];a=math.atan2(c.y,c.x)
    fold=(.006*math.sin(a*11+c.z*7)+.003*math.sin(c.x*55+c.z*30))*float(os.environ.get("ROBE_FOLD","1"))
    taper=min(1,ring.get(i,4)/4)
    d=(pos[i]-basis[i]+n*(.022+fold))*taper
    for kb in keys:kb.data[i].co+=d
    monk.data.vertices[i].co=keys['Basis'].data[i].co
# The folded upper edge of the robe across the chest; he sits on a worn reed mat.
fold=tube('sophal_living_fold',COL,ROBE_EDGE,.016,robe,sides=10,radius_end=.022)
fold.parent=monk
legs=[v.co for v in monk.data.vertices if v.co.z<.16]
lx=sum(v.x for v in legs)/len(legs);ly=sum(v.y for v in legs)/len(legs)
spread=lathe('sophal_living_robe_spread',COL,[(.2,.13),(.3,.09),(.37,.045),(.415,.014),(.43,.004)],lx,ly,0,body_robe,segments=96)
for v in spread.data.vertices:
    a=math.atan2(v.co.y-ly,v.co.x-lx);r=math.hypot(v.co.x-lx,v.co.y-ly)
    k=1+.035*math.sin(a*7)+.015*math.sin(a*17)
    v.co.x=lx+(v.co.x-lx)*k;v.co.y=ly+(v.co.y-ly)*k*.82;v.co.z+=.012*math.sin(a*17)
spread.parent=monk
# A mala of dark seed beads looped round his folded hands.
skin_v={i for poly in monk.data.polygons if poly.material_index==0 for i in poly.vertices}
hands_v=[monk.data.vertices[i].co for i in skin_v if monk.data.vertices[i].co.z<.5]
if hands_v:
    hc=sum(hands_v,Vector())/len(hands_v)
    bead=plain('sophal_mala_seed',(.05,.025,.012),rough=.45)
    for k in range(54):
        t=k/54*math.tau
        p=hc+Vector((math.cos(t)*.055,-.03+math.sin(t)*.012,-.02-.035*(1-math.cos(t))*.5-.03*max(0,math.sin(t))))
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6,ring_count=4,radius=.0065,location=p)
        b=bpy.context.object;b.name='sophal_living_mala'
        for c in list(b.users_collection):c.objects.unlink(b)
        COL.objects.link(b);b.data.materials.append(bead);b.parent=monk
mat=library_material('bamboo_wall','sophal_living_mat',tint=(.55,.48,.38))
seat=box('sophal_living_mat',COL,-.55,.55,-.45,.45,-.01,.012,mat)
seat.parent=monk
# The hall image: a real seated body made into painted plaster, calling the earth to
# witness: left hand in the lap, right hand down over the right knee. (Advisor review.)
buddha=anatomy('hall_buddha_statue',old=True,monk=True,hands=[tuple(BUDDHA_HAND),(-.2,.15,1.7)])
buddha_edge=list(ROBE_EDGE)
buddha.shape_key_clear()
bpy.context.view_layer.objects.active=buddha
for o in bpy.context.selected_objects:o.select_set(False)
buddha.select_set(True)
smooth=buddha.modifiers.new('plaster','SMOOTH');smooth.factor=.7;smooth.iterations=10
bpy.ops.object.modifier_apply(modifier=smooth.name)
plaster_skin=library_material('clay_plaster','hall_buddha_plaster',colour=(.56,.52,.43),tile=.8)
plaster_robe=library_material('clay_plaster','hall_buddha_robe_paint',colour=(.6,.23,.035),tile=.8)
buddha.data.materials[0]=plaster_skin;buddha.data.materials[1]=plaster_robe;buddha.data.materials[2]=plaster_robe
for poly in buddha.data.polygons:poly.use_smooth=True
eL,_,eR,_,bhead,bcrown=[Vector(c) for c in buddha['eyes']]
mid=(eL+eR)/2;up=Vector((0,0,1))
def blob(name,at,size,mat,seg=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=max(4,seg//2),location=at)
    o=bpy.context.object;o.name=name;o.scale=size
    for c in list(o.users_collection):c.objects.unlink(o)
    COL.objects.link(o);o.data.materials.append(mat);o.parent=buddha
    for f in o.data.polygons:f.use_smooth=True
    return o
# Snail-shell curls packed over the scalp (above the brow, behind the ears), sitting on
# the smoothed head itself; the ushnisha on the crown and its flame above.
scalp=[v for v in buddha.data.vertices if (v.co-mid).length<.16 and
       (v.co.z>mid.z+.035 or (v.co.y-mid.y>.075 and v.co.z>mid.z-.045))]
curls=[]
for v in sorted(scalp,key=lambda v:-v.co.z):
    if all((v.co-c).length>.017 for c in curls):curls.append(v.co.copy())
    if len(curls)>=320:break
top=max(scalp,key=lambda v:v.co.z)
for k,c in enumerate(curls):
    n=next(v.normal for v in scalp if v.co==c)
    blob('hall_buddha_curl',c+n*.004,(.0105,.0105,.0085),plaster_skin,6)
crown_c=top.co
blob('hall_buddha_ushnisha',crown_c+up*.012,(.042,.042,.036),plaster_skin,14)
# Downcast eyes: plaster fills the sockets, as on a cast image.
for e in (eL,eR):blob('hall_buddha_eye',e+Vector((0,-.002,-.001)),(.0125,.011,.0105),plaster_skin,10)
edge=tube('hall_buddha_robe_edge',COL,buddha_edge,.016,plaster_robe,sides=8,radius_end=.02);edge.parent=buddha
flame=tube('hall_buddha_flame',COL,[tuple(crown_c+up*.07),tuple(crown_c+up*.21)],.018,plaster_skin,sides=10,radius_end=.002);flame.parent=buddha
# Long earlobes hanging from the side of the head at eye height.
for side in (eL,eR):
    out=1 if side.x>mid.x else -1
    ring=[v.co for v in buddha.data.vertices if abs(v.co.z-mid.z)<.025 and (v.co-mid).length<.14]
    ear=max(ring,key=lambda c:(c.x-mid.x)*out)
    lobe=tube('hall_buddha_earlobe',COL,[tuple(ear+Vector((-out*.008,0,-.01))),tuple(ear+Vector((-out*.006,.003,-.045))),tuple(ear+Vector((-out*.012,.002,-.078)))],.01,plaster_skin,sides=8,radius_end=.013)
    lobe.parent=buddha
buddha.scale=(1.85,1.85,1.85);buddha.location=(22,6.15,1.554)

# The apparition: a dead woman in a rotted red dress, hair hanging over her face.
import random
ghost_root=empty('pagoda_ghost',COL,(0,0,0))
ghost=anatomy('pagoda_ghost_body',ghost=True)
ghost.parent=ghost_root
eyeL,_,eyeR,_,head,crown=[Vector(c) for c in ghost['eyes']]
void=plain('pagoda_ghost_void',(.003,.002,.002),rough=.15)
glint=plain('pagoda_ghost_glint',(.25,.24,.22),rough=.1,emission=(.35,.33,.3),strength=.25)
for e in (eyeL,eyeR):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=10,location=e,radius=.016)
    o=bpy.context.object;o.name='pagoda_ghost_eye'
    for c in list(o.users_collection):c.objects.unlink(o)
    COL.objects.link(o);o.data.materials.append(void);o.parent=ghost_root
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=6,location=e+Vector((0,-.012,0)),radius=.003)
    g=bpy.context.object;g.name='pagoda_ghost_glint'
    for c in list(g.users_collection):c.objects.unlink(g)
    COL.objects.link(g);g.data.materials.append(glint);g.parent=ghost_root
hair_mat=plain('pagoda_ghost_hair',(.012,.011,.01),rough=.35)
rnd=random.Random(7)
axis=(crown-head).normalized();top=crown+axis*.02
for k in range(520):
    a=rnd.uniform(0,math.tau);up=rnd.uniform(.0,.9)
    face=math.sin(a)<-.25
    # A centre parting: the hair falls either side of the face, which is left bare.
    if face and abs(math.cos(a))<.45:a=math.atan2(math.sin(a),math.copysign(.45,math.cos(a)))
    # Rooted over the whole scalp, which lies on the skull along the head bone.
    start=head.lerp(crown,.55+.4*(1-up))+Vector((math.cos(a)*.08*(.6+up*.5),math.sin(a)*.09*(.6+up*.5),.0))
    length=rnd.uniform(.35,.6) if face else rnd.uniform(.55,.85)
    out=Vector((math.cos(a)*.06,math.sin(a)*.08-(.06 if face else 0),0))
    pts=[start]
    for i in range(1,7):
        t=i/6;p=start+out*min(1,t*3)+Vector((rnd.gauss(0,.012),rnd.gauss(0,.012),-length*t))
        pts.append(p)
    o=tube('pagoda_ghost_hair',COL,[tuple(p) for p in pts],rnd.uniform(.0018,.0035),hair_mat,sides=3,radius_end=.001)
    o.parent=ghost_root
# A rotted red skirt hanging straight, its hem torn into rags.
dress=library_material('rough_linen','pagoda_ghost_dress',colour=(.22,.012,.015));dress.use_backface_culling=False
skirt=garment('pagoda_ghost_skirt',ghost_root,[(.15,.95),(.19,.85),(.24,.6),(.28,.35),(.31,.18)],dress,pleats=.02)
import bmesh
bm=bmesh.new();bm.from_mesh(skirt.data)
for v in bm.verts:
    if v.co.z<.2:v.co.z+=rnd.uniform(-.06,.12)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_center_median().z<.4 and rnd.random()<.18],context='FACES')
bm.to_mesh(skirt.data);bm.free()
ghost_root.location=(0,0,-60)
# A world anchor compensates the glTF X reflection, exactly as in the pagoda area.
axes=empty('cinematic_axes',COL,(0,0,0))
for obj in list(COL.objects):
    if obj!=axes and obj.parent is None:obj.parent=axes
axes.scale.x=-1
for img in bpy.data.images:
    if img.source=='FILE':img.pack()
path=ROOT/'art-source/blender/ep2/ep2_cinematics.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(path))
# Export only this collection, excluding library prototypes.
bpy.ops.object.select_all(action='DESELECT')
for obj in COL.all_objects:obj.select_set(True)
out=ROOT/'art-export/ep2/ep2_cinematics.glb';out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_morph=True,export_extras=True,export_cameras=False,export_lights=False)
print('CINEMATICS_ASSET',len(COL.all_objects),flush=True)
