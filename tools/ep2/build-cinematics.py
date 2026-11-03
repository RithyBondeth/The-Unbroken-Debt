"""Author Episode 2's living harvest, famine village, the apparition, and the scanned
images: Sophal, the hall Buddha and the clearing of the reclining Buddha.
Uses the same CC0 MakeHuman anatomy (harvest villagers) and Poly Haven/cloth kit as
Episode 1, and the scans in tools/ep2/pagoda_scans.py.
blender -b --factory-startup -P tools/ep2/build-cinematics.py
Exports are optimized with npm run assets -- ep2/ep2_cinematics.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Quaternion
ROOT=Path(__file__).resolve().parents[2]
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

def anatomy(name,old=False):
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
    floor=min(verts[i].y for i in used)
    def local(v):return Vector((v.x*.1,-v.z*.1,(v.y-floor)*.1))
    def pose(kind):
        for b in rig.pose.bones:b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion()
        for side,sign in [('L',-1),('R',1)]:
            rotate('upperarm01.'+side,(0,0,1),sign*34)
            rotate('lowerarm01.'+side,(1,0,0),-18)
            for finger in range(1,6):
                for part in [2,3]:rotate(f'finger{finger}-{part}.{side}',(0,1,0),sign*12)
            if kind in ['left','right','clap']:
                direction=-1 if kind=='left' else 1
                rotate('upperarm01.'+side,(0,0,1),-sign*(22 if kind!='clap' else 36))
                rotate('lowerarm01.'+side,(1,0,0),-35 if kind!='clap' else -64)
                rotate('wrist.'+side,(0,1,0),sign*12)
                rotate('upperleg01.'+side,(1,0,0),direction*sign*7)
                rotate('lowerleg01.'+side,(1,0,0),8)
                rotate('head',(0,0,1),direction*3)
            elif kind=='famine':
                rotate('spine01',(1,0,0),18);rotate('head',(1,0,0),18)
                rotate('upperleg01.'+side,(1,0,0),-55);rotate('lowerleg01.'+side,(1,0,0),80)
        if kind=='listen':rotate('head',(0,1,0),-7);rotate('neck01',(1,0,0),4)
        bpy.context.view_layer.update()
    poses={}
    for kind in ['rest','left','right','clap','famine']:
        pose(kind);ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());out=ev.to_mesh()
        points=[local(v.co) for v in out.vertices];ev.to_mesh_clear()
        # Keep a planted foot in every authored pose; the runtime adds only a subtle weight shift.
        drop=min(v.z for v in points)
        poses[kind]=[Vector((v.x,v.y,v.z-drop)) for v in points]
    body.modifiers.clear();bpy.data.objects.remove(rig,do_unlink=True)
    for vertex,p in zip(mesh.vertices,poses['rest']):vertex.co=p
    mesh.update();body.shape_key_add(name='Basis')
    for kind,points in poses.items():
        if kind=='rest':continue
        key=body.shape_key_add(name=kind);key.value=0
        for vertex,p in zip(key.data,points):vertex.co=p
    skin=image_material(name+'_skin',str(source/('old_lightskinned_male_diffuse2.png' if old else 'young_lightskinned_female_diffuse3.png')),rough=.83,tint=(.63,.48,.34))
    cloth=library_material('rough_linen',name+'_cloth',colour=(.19,.21,.16))
    wrap=library_material('rough_linen',name+'_wrap',colour=(.3,.16,.11))
    body.data.materials.clear()
    for mat in [skin,cloth,wrap]:body.data.materials.append(mat)
    # Bone regions keep cloth off the face in every baked pose, including seated poses.
    for poly in mesh.polygons:
        names=[regions.get(i,('',0))[0] for i in poly.vertices]
        torso=sum(n.startswith(('spine','pelvis','root')) for n in names)
        leg=sum(n.startswith(('upperleg','lowerleg')) for n in names)
        sleeve=sum(n.startswith('upperarm') for n in names)
        poly.material_index=2 if leg>len(names)/2 else 1 if torso+sleeve>len(names)/2 else 0
    # Closed garment shells keep the shirt and wrapped waist visibly separate from skin.
    # Each garment vertex moves once (not once per face), or the cloth blisters.
    lifted={i for poly in mesh.polygons if poly.material_index for i in poly.vertices}
    for index in lifted:
        mesh.vertices[index].co+=mesh.vertices[index].normal*.008
    print('Authored',name,len(mesh.polygons),'faces',flush=True)
    return body

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
# Real images from photogrammetry scans (tools/ep2/pagoda_scans.py). Sophal keeps his
# node name for the cinematics; the area's first-pass monk is hidden at runtime.
sys.path.insert(0,str(ROOT/'tools/ep2'))
import numpy as np
from pagoda_scans import scan,instance
from pagoda_rituals import ritual_materials,red_string_web,hanging_doll,talisman
from kit import collider
monk=scan(COL,'monk_seated','sophal_living',height=.95,at=(-18,-11,.16))
# The hall image on its red lotus throne.
scan(COL,'buddha_seated','hall_buddha_image',height=1.75,at=(22,6.15,1.554))

# ---- The clearing east of the fallen bay: the sala of the reclining Buddha.
# The path in runs west to east at Y -8.7; the images face whoever walks it.
rng=np.random.default_rng(1932)
rm=ritual_materials()
rm['bronze']=plain('M_ep2_bell_bronze',(.3,.2,.08),rough=.4,metal=.8)
# The same weathered masonry as the temple: mould-streaked lime plaster, sooty brick.
from pagoda_ruin import ruin_materials
masonry=ruin_materials()
brick=masonry['brick']
lime=masonry['mould_white']
tiles=library_material('clay_roof_tiles_02','M_ep2_sala_tiles',tint=(.5,.4,.34))
tiles.use_backface_culling=False
timber=library_material('weathered_brown_planks','M_ep2_sala_timber',tint=(.42,.34,.27))
timber.use_backface_culling=False
wax=plain('M_ep2_sala_wax',(.3,.03,.025),rough=.38)
soot=plain('M_ep2_sala_wick',(.02,.018,.015),rough=1)
# Naga guardians on brick posts either side of the breach, hoods towards the compound.
naga=None
for k,y in enumerate((-10.9,-6.5)):
    box('sala_naga_post',COL,29.05,29.75,y-.35,y+.35,0,.62,lime)
    collider('sala_naga_post_'+str(k),COL,29.05,29.75,y-.35,y+.35,0,1.9,'stone')
    if naga is None:naga=scan(COL,'naga_finial','sala_naga',height=1.3,at=(29.4,y,.62),yaw=math.radians(-90))
    else:instance(COL,naga,'sala_naga',(29.4,y,.62),math.radians(-90))
# A third, broken off its balustrade, lies half sunk in the pond.
drowned=instance(COL,naga,'pond_naga_sunken',(-13.6,31.4,-.5),math.radians(90))
drowned.rotation_euler=(math.radians(-20),math.radians(8),math.radians(90))  # hoods towards the bridge
# The watchers: painted alms-monks lining the path, three a side, facing the lane.
watcher=None
for k,(x,y) in enumerate([(30.7,-10.9),(32.4,-10.9),(34.1,-10.9),(30.7,-6.5),(32.4,-6.5),(34.1,-6.5)]):
    yaw=math.pi if y<-8.7 else 0.0
    if watcher is None:
        watcher=scan(COL,'monk_alms_standing','pagoda_watcher_0',height=1.66,at=(x,y,0),yaw=yaw)
    else:instance(COL,watcher,'pagoda_watcher_'+str(k),(x,y,0),yaw)
    collider('pagoda_watcher_'+str(k),COL,x-.24,x+.24,y-.24,y+.24,0,1.7,'teak')
# The sala: a low brick platform, square lime-washed piers, timber beams and a roof
# that has half come down. The south end lies in the leaves.
box('sala_platform',COL,35.2,41.2,-15,-3.4,0,.2,brick)
collider('sala_platform',COL,35.2,41.2,-15,-3.4,0,.2,'stone')
box('sala_step',COL,34.6,35.2,-10.4,-7,0,.1,brick)
collider('sala_step',COL,34.6,35.2,-10.4,-7,0,.1,'stone')
piers=[]
for x in (35.6,40.8):
    for y in (-14.6,-11.1,-6.3,-3.8):
        if (x,y)==(40.8,-14.6):continue  # fallen
        box('sala_pier',COL,x-.17,x+.17,y-.17,y+.17,.2,3.0,lime)
        box('sala_pier_foot',COL,x-.24,x+.24,y-.24,y+.24,.2,.42,brick)
        collider('sala_pier_'+str(len(piers)),COL,x-.24,x+.24,y-.24,y+.24,.2,3.0,'stone')
        piers.append((x,y))
tube('sala_pier_fallen',COL,[(41.6,-15.6,.14),(40.2,-17.7,.2),(38.9,-19.4,.15)],.17,lime,sides=4)
for x in (35.6,40.8):box('sala_plate',COL,x-.12,x+.12,-14.8,-3.6,3.0,3.18,timber)
for y in (-11.1,-6.3,-3.8):box('sala_tie',COL,35.4,41.0,y-.1,y+.1,3.0,3.15,timber)
# The standing half of the roof: two pitches of clay tile over the north end, holed.
for side in (-1,1):
    for k in range(18):
        y0=-8.4+k*.3
        if rng.random()<.18:continue
        x_eave=38.2+side*3.0
        # A unit board bent into place: t runs from the eave (0) to the ridge (1).
        b=box('sala_roof_tiles',COL,-.16,.16,0,1,0,.03,tiles)
        for v in b.data.vertices:
            t=v.co.y
            v.co=Vector((x_eave+(38.2-x_eave)*t,y0+v.co.x,3.1+1.5*t+v.co.z))
# The fallen half: square rafters slumped from the south eaves into the leaves, and
# the tiles that came down with them lying broken in slabs.
for k in range(9):
    y0=-14.2+k*.48+rng.normal(0,.06)
    a=rng.uniform(-.25,.25)
    tube('sala_rafter_fallen',COL,[(40.8+rng.normal(0,.1),y0,3.0-k*.1),(39.2,y0+a,1.5+rng.uniform(0,.4)),(37.4,y0+a*2,.06)],.05,timber,sides=4)
for k in range(16):
    x,y=rng.uniform(36.2,40.6),rng.uniform(-14.9,-11.6)
    slab=box('sala_tiles_fallen',COL,-rng.uniform(.2,.45),rng.uniform(.2,.45),-rng.uniform(.15,.35),rng.uniform(.15,.35),0,.03,tiles)
    slab.location=(x,y,.21 if 35.2<x<41.2 else .01)
    slab.rotation_euler=(rng.normal(0,.12),rng.normal(0,.12),rng.uniform(0,math.tau))
# The image on its brick bed, lying on his right side, facing the way in.
box('sala_bed',COL,37.7,39.7,-13.4,-4.4,.2,.62,brick)
box('sala_bed_cap',COL,37.6,39.8,-13.5,-4.3,.62,.68,lime)
collider('sala_bed',COL,37.6,39.8,-13.5,-4.3,.2,1.5,'stone')
scan(COL,'buddha_reclining','sala_reclining_buddha',length=3.5,at=(38.75,-8.9,.68),yaw=math.radians(-90))
# Burnt-down red candles along the bed's edge, each in a puddle of its own wax with
# runs down its side and a black wick, and a row of dead marigolds.
for k in range(26):
    y=-13.1+k*.34+rng.normal(0,.03)
    x=37.52+rng.normal(0,.03)
    h=rng.uniform(.05,.15)
    r=rng.uniform(.013,.019)
    lathe('sala_wax_pool',COL,[(0,0),(r*1.9,0),(r*1.7,.003),(r*1.1,.006),(0,.006)],x,y,.2,wax,segments=14)
    candle=lathe('sala_candle',COL,[(r,0),(r*1.05,h*.3),(r,h*.6),(r*1.08,h*.85),(r*.95,h),(r*.5,h+.004),(r*.3,h-.003),(0,h-.002)],x,y,.2,wax,segments=14)
    for v in candle.data.vertices:  # runs of wax down one side
        a=math.atan2(v.co.y-y,v.co.x-x)
        v.co.x+=math.cos(a)*.003*max(0,math.sin(a*3+k))
        v.co.y+=math.sin(a)*.003*max(0,math.sin(a*3+k))
    tube('sala_wick',COL,[(x,y,.2+h-.003),(x+.001,y,.2+h+.008)],.0012,soot,sides=4)
    if k%2:lathe('sala_marigold',COL,[(0,0),(.03,.01),(.035,.03),(0,.045)],37.9,y,.68,rm['marigold_dead'],segments=6)
# Red cord overhead from the naga hoods to the sala eaves and between the piers,
# tags and bells along it, dolls under the beams.
anchors=[(29.4,-10.9,1.85),(29.4,-6.5,1.85),(35.6,-11.1,2.9),(35.6,-6.3,2.9),(35.6,-14.6,2.8),(35.6,-3.8,2.8),(40.8,-11.1,2.9),(40.8,-3.8,2.9)]
red_string_web(COL,rm,'sala_cords',anchors,rng,density=1.6)
for k in range(9):
    x,y=rng.uniform(36,40.4),rng.uniform(-11,-4.2)
    hanging_doll(COL,rm,'sala_doll_'+str(k),(x,y,3.0),rng,drop=rng.uniform(.5,1.2))
for k,(x,y) in enumerate(piers):
    for j in range(3):talisman(COL,rm,f'sala_tag_{k}_{j}',(x+rng.normal(0,.12),y-.19,rng.uniform(1.2,2.2)),rng,rm['talisman_red'] if j==0 else None)
# She stands where the trees close in, bound in cord, turned towards the sala.
goddess=scan(COL,'prajnaparamita','pagoda_goddess',height=1.95,at=(43.0,-18.5,0),yaw=math.radians(-90))
helix=[(math.cos(t)*.21,math.sin(t)*.14,.5+t*.045) for t in np.linspace(0,math.tau*2.6,90)]
cord=tube('pagoda_goddess_cord',COL,helix,.006,rm['red_thread'],sides=4)
cord.parent=goddess
for j in range(4):
    t=talisman(COL,rm,f'pagoda_goddess_tag_{j}',(math.cos(j*1.7)*.22,math.sin(j*1.7)*.15,.65+j*.12),rng,rm['talisman_red'])
    for o in t:o.parent=goddess

# The apparition: the woman in red (the Kuntilanak Merah scan), arms hanging, head
# dropped. Parked out of sight; PagodaApparition moves her for each scare.
ghost_root=empty('pagoda_ghost',COL,(0,0,0))
ghost=scan(COL,'kuntilanak_red','pagoda_ghost_body',height=1.66)
ghost.parent=ghost_root
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
