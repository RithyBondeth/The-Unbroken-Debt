"""Build the full-volume Krasue, with GPU-skinned hair/viscera and PBR maps.
Run: Blender --background --python art-source/characters/krasue/build_krasue.py
Metres, +Y facing, +Z up. GLB exports to Babylon +Z facing / +Y up.
"""
import bpy, bmesh, math, random, sys
import numpy as np
from mathutils import Vector
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'public/assets/shared/krasue'
OUT.mkdir(parents=True, exist_ok=True)
# Maps are embedded in the GLB; their working copies stay out of public/.
WORK = ROOT / 'art-export/krasue'
WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import krasue_head
random.seed(73191)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Small reusable normal maps; no photographic surface carries transparency.
def normal_map(name, strength, seed):
    rng = np.random.default_rng(seed)
    n = 256
    y, x = np.mgrid[0:n, 0:n]
    h = rng.normal(0, .11, (n, n))
    for scale, amp in [(9,.2),(23,.08),(53,.025)]:
        h += np.sin(x/scale + np.sin(y/(scale*.7))) * np.cos(y/(scale*.8)) * amp
    if 'hair' in name:
        # Directional cuticle grooves run along each lock's UV length.
        h=.20*np.sin(x*2*math.pi/5+np.sin(y/55)*.4)+.055*np.sin(x*2*math.pi/2.3+y/83)
    dy, dx = np.gradient(h)
    normals = np.stack((-dx*strength, -dy*strength, np.ones_like(h)), axis=-1)
    normals /= np.linalg.norm(normals,axis=-1,keepdims=True)
    rgba = np.ones((n,n,4),dtype=np.float32)
    rgba[:,:,:3] = normals * .5 + .5
    image = bpy.data.images.new(name, n, n, alpha=False)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str((OUT if name == 'krasue_hair_normal' else WORK) / (name + '.png'))
    image.file_format = 'PNG'; image.save()
    return image
skin_normal = normal_map('krasue_skin_normal',1.2,19)
organ_normal = normal_map('krasue_tissue_normal',2.2,29)
hair_normal = normal_map('krasue_hair_normal',.6,39)

def hair_albedo():
    # Long irregular fibers add root-layer detail, including
    # when fine geometry becomes subpixel in the window view.
    w,h=512,1024
    rng=np.random.default_rng(871)
    y,x=np.mgrid[0:h,0:w]
    columns=rng.uniform(.035,.14,w)
    drift=np.sin(y/170)*1.8+np.sin(y/53)*.3
    sample=(x+drift).astype(int)%w
    value=columns[sample]*(.85+.15*np.sin(y/127+x/37))
    rgba=np.ones((h,w,4),dtype=np.float32)
    rgba[:,:,:3]=value[:,:,None]*np.array([1,.88,.78])
    img=bpy.data.images.new('krasue_hair_fibers',w,h,alpha=False)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.filepath_raw=str(WORK/'krasue_hair_fibers.png');img.file_format='PNG';img.save()
    return img
hair_color=hair_albedo()

def dead_skin():
    """MakeHuman's CC0 skin photograph (pores, lips, brows) turned to a corpse's:
    grey-olive and bloodless, mottled with lividity, a net of dark veins under
    the thin skin of the temples, jaw and throat."""
    src=bpy.data.images.load(str(krasue_head.SKIN_TEXTURE))
    w,h=src.size
    px=np.array(src.pixels[:],dtype=np.float32).reshape(h,w,4)
    rng=np.random.default_rng(4471)
    rgb=px[:,:,:3]
    lum=rgb@np.array([.3,.59,.11],dtype=np.float32)
    grey=np.repeat(lum[:,:,None],3,axis=2)
    out=(grey*.8+rgb*.2)*np.array([.6,.64,.57],dtype=np.float32)
    y,x=np.mgrid[0:h,0:w].astype(np.float32)/max(w,h)
    blot=sum(np.sin(x*f*6.3+p)*np.cos(y*f*5.1-p) for f,p in ((3,.2),(7,1.9),(13,4.1)))
    livid=np.clip(.5+.25*blot+rng.normal(0,.04,(h,w)),0,1)
    out*=(1-.22*livid[:,:,None]*np.array([.35,.55,.25],dtype=np.float32))
    veins=np.zeros((h,w),dtype=np.float32)
    for k in range(9):
        f=rng.uniform(40,90);ph=rng.uniform(0,6.3)
        line=np.abs(np.sin((x*np.cos(k)+y*np.sin(k))*f+np.sin(y*17+k)*1.6+ph))
        veins=np.maximum(veins,np.clip(1-line/.035,0,1)*rng.uniform(.3,.7))
    out=out*(1-veins[:,:,None]*.28)+veins[:,:,None]*np.array([.02,.03,.05],dtype=np.float32)
    img=bpy.data.images.new('krasue_dead_skin',w,h,alpha=False)
    rgba=np.concatenate((np.clip(out,0,1),np.ones((h,w,1),dtype=np.float32)),axis=2)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.filepath_raw=str(WORK/'krasue_dead_skin.png');img.file_format='PNG';img.save()
    bpy.data.images.remove(src)
    return img
skin_photo=dead_skin()

def material(name, color, rough=.7, normal=None, photo=False):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough
    p.inputs['Specular IOR Level'].default_value=.22
    if 'hair' in name:
        tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=hair_color
        m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    if photo:
        tex=m.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image=photo
        m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    if normal:
        tex=m.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=normal
        nm=m.node_tree.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value=.45 if photo else .8 if 'hair' in name else .7
        m.node_tree.links.new(tex.outputs['Color'],nm.inputs['Color'])
        m.node_tree.links.new(nm.outputs['Normal'],p.inputs['Normal'])
    return m
face=material('M_krasue_face',(.28,.25,.22),.58,skin_normal,skin_photo)
hair=material('M_krasue_hair',(.009,.007,.006),.64,hair_normal)
hair_glint=material('M_krasue_hair_glint',(.014,.011,.009),.68,hair_normal)
hair_roots=material('M_krasue_hair_roots',(.004,.003,.002),.94,hair_normal)
hair_roots.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.06
flesh=material('M_krasue_viscera',(.085,.009,.013),.48,organ_normal)
liver_mat=material('M_krasue_liver',(.052,.012,.017),.61,organ_normal)
vessel=material('M_krasue_vessels',(.045,.004,.008),.3,organ_normal)
cavity=material('M_krasue_cavity',(.008,.003,.004),.94)
eye=material('M_krasue_sclera',(.32,.36,.32),.12,photo=bpy.data.images.load(str(krasue_head.EYE_TEXTURE)))
teeth=material('M_krasue_teeth',(.24,.19,.11),.55,skin_normal)
gum=material('M_krasue_gums',(.065,.018,.023),.48,organ_normal)

# Spatial pigment follows the lobes and folds, rather than one uniform red.
# Linear vertex colors survive glTF export without a texture-baking shortcut.
for tissue in [flesh,liver_mat]:
    p=tissue.node_tree.nodes.get('Principled BSDF')
    # Wet: a slick coat over the tissue that catches the moon in streaks.
    p.inputs['Coat Weight'].default_value=.55
    p.inputs['Coat Roughness'].default_value=.12
    pigment=tissue.node_tree.nodes.new('ShaderNodeVertexColor')
    pigment.layer_name='TissuePigment'
    tissue.node_tree.links.new(pigment.outputs['Color'],p.inputs['Base Color'])

# One armature. Every strand has a real cross-section and 4-bone skin weights.
rigdata=bpy.data.armatures.new('KrasueSkeleton')
rig=bpy.data.objects.new('krasue_rig',rigdata); bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
base=rigdata.edit_bones.new('krasue_head'); base.head=(0,0,-.02); base.tail=(0,0,.18)
bpy.ops.object.mode_set(mode='OBJECT'); rig.select_set(False)

def chain(prefix, points):
    bpy.context.view_layer.objects.active=rig; rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); names=[]
    for i in range(len(points)-1):
        b=rigdata.edit_bones.new(f'{prefix}_{i}')
        b.head=points[i]; b.tail=points[i+1]
        b.parent=rigdata.edit_bones[names[-1]] if names else rigdata.edit_bones['krasue_head']
        names.append(b.name)
    bpy.ops.object.mode_set(mode='OBJECT'); rig.select_set(False)
    return names

def mesh(name, verts, faces, mats, uv=None, slots=None, weights=None):
    data=bpy.data.meshes.new(name); data.from_pydata(verts,[],faces); data.update()
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj)
    for m in mats: data.materials.append(m)
    for i,p in enumerate(data.polygons):
        p.use_smooth=True
        if slots: p.material_index=slots[i]
    if uv:
        layer=data.uv_layers.new(name='UVMap')
        for poly in data.polygons:
            for li in poly.loop_indices: layer.data[li].uv=uv[data.loops[li].vertex_index]
    if len(mats)==1 and mats[0] in [flesh,liver_mat]:
        base=mats[0].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value[:3]
        colors=data.color_attributes.new(name='TissuePigment',type='FLOAT_COLOR',domain='POINT')
        for i,(x,y,z) in enumerate(verts):
            broad=math.sin(x*53+z*17)*math.cos(z*31-y*27)
            folds=math.sin(z*151+x*79+math.sin(y*83))
            capillary=math.exp(-math.sin(x*117+math.sin(z*37))**2/.018)
            shade=.9+broad*.16+folds*.045-capillary*.14
            colors.data[i].color=(base[0]*shade,base[1]*(shade+.07*broad),base[2]*(shade-.05*broad),1)
    obj.parent=rig
    mod=obj.modifiers.new('Krasue skinning','ARMATURE'); mod.object=rig
    if weights:
        groups={n:obj.vertex_groups.new(name=n) for n in {n for w in weights for n,v in w}}
        for i,w in enumerate(weights):
            for n,value in w:
                if value>0: groups[n].add([i],value,'REPLACE')
    else:
        obj.vertex_groups.new(name='krasue_head').add(list(range(len(verts))),1,'REPLACE')
    return obj

def rigged(obj, shape=None):
    """Parents a finished object to the head bone; `shape` adds its Scream key."""
    obj.parent=rig
    mod=obj.modifiers.new('Krasue skinning','ARMATURE'); mod.object=rig
    obj.vertex_groups.new(name='krasue_head').add(list(range(len(obj.data.vertices))),1,'REPLACE')
    for p in obj.data.polygons: p.use_smooth=True
    if shape is not None:
        obj.shape_key_add(name='Basis')
        key=obj.shape_key_add(name='Scream')
        for v,d,k in zip(obj.data.vertices,shape,key.data): k.co=v.co+d
    return obj

# A real head from CC0 MakeHuman anatomy (krasue_head.py): skull, ears, lids,
# lips and teeth, starved gaunt and torn away at the neck. The eyes and mouth
# close into deep sockets, the neck into a raw stump, so the solid stays closed.
head_bm,head_gape,head_parts,stump_z=krasue_head.build_head()
dims=krasue_head.measure(head_bm)
def dimensions(z):
    w,front,back=dims(z)
    return w,front
def back_depth(z):
    return dims(z)[2]
head_data=bpy.data.meshes.new('krasue_sculpted_head')
gape=[v[head_gape].copy() for v in head_bm.verts]
# Blood and death in the skin: dark sunken orbits, red-rimmed lids, grey lips,
# and blood run from the mouth over the chin and down the torn throat.
# The lower lip: the height of the mouth's own teeth.
LIP_Z=sum(v.z for v in head_parts['lower_teeth'][0])/len(head_parts['lower_teeth'][0])+.01
stain=[]
for v in head_bm.verts:
    x,y,z=v.co
    c=np.array([1.,1.,1.])
    for s in (-1,1):
        d=math.hypot((x-s*.0725)/.05,(z-.027)/.034)
        c*=1-.55*math.exp(-d*d)*np.array([1,1.1,.95])
        rim=math.exp(-((math.hypot((x-s*.0725)/.036,(z-.027)/.019)-1)/.35)**2)
        c*=1-.3*rim*np.array([.1,.75,.7])
    mouth=math.exp(-((x/.06)**2+((z-LIP_Z)/.025)**2))*(y>.04)
    c=c*(1-.6*mouth)+.6*mouth*np.array([.3,.06,.06])
    # Runs from the corners and the middle of the lower lip, down the chin.
    for cx,length,width in ((-.05,.2,.011),(.052,.15,.009),(.006,.26,.014),(.024,.11,.008)):
        wob=cx+.006*math.sin(z*70+cx*40)
        top=LIP_Z-.008
        if z<top+.01 and z>top-length and y>-.02:
            t=max(0,(top-z)/length)
            fade=min(1,(top+.01-z)/.02)*(1-t**2)
            run=math.exp(-((x-wob)/(width*(1.2-.5*t)))**2)*fade
            c=c*(1-run)+run*np.array([.3,.02,.018])
    # Soaked round the torn neck.
    if z<-.2:
        soak=min(1,(-.2-z)/.07)
        c=c*(1-.85*soak)+.85*soak*np.array([.3,.02,.02])
    stain.append((*c,1))
from mathutils.bvhtree import BVHTree
head_tree=BVHTree.FromBMesh(head_bm)
def on_head(a,z,off):
    """The point of the real skull (ears included) in direction `a` round it at
    height `z`, lifted `off` off the skin: the scalp and the hair's roots sit on
    the head itself, not on an ellipse that the cheeks and ears poke through."""
    el=math.asin(max(-1,min(1,(z-.02)/.272)))
    d=Vector((math.sin(a)*math.cos(el),math.cos(a)*math.cos(el),math.sin(el)))
    centre=Vector((0,0,.02))
    hit=head_tree.ray_cast(centre+d*.6,-d,.6)[0]
    if hit is None: hit=centre+d*.27
    return tuple(hit+d*off)
head_bm.to_mesh(head_data)
head_bm.free()
for m in (face,cavity,flesh): head_data.materials.append(m)
colors=head_data.color_attributes.new(name='KrasueStain',type='FLOAT_COLOR',domain='POINT')
for i,c in enumerate(stain): colors.data[i].color=c
head_obj=bpy.data.objects.new('krasue_sculpted_head',head_data); bpy.context.collection.objects.link(head_obj)
rigged(head_obj,gape)
MAKEHUMAN={'krasue_sculpted_head'}

# Closed lobed surfaces for eyes, irregular viscera and roots; not image cards.
def blob(name, center, size, mat, kind='plain', bone=None, rotation=0):
    verts=[]; uv=[]; fs=[]; weights=[]; rows=28; cols=44
    for r in range(rows+1):
        lat=-math.pi/2+math.pi*r/rows
        for c in range(cols+1):
            a=2*math.pi*c/cols
            rr=math.cos(lat); z=math.sin(lat)
            x=rr*math.sin(a); y=rr*math.cos(a)
            if kind!='plain':
                ripple=1+.065*math.sin(a*3+lat*7)+.026*math.cos(a*9-lat*11)
                x*=ripple; y*=ripple
                if kind=='heart': x*=.77+.23*(z+1)/2; y+=.13*math.sin(a*2)*rr; z-=.12*x
                if kind=='lung':
                    x*=.6+.4*(1-z)/2
                    y*=.85+.15*math.cos(lat*5)
                    y-=.08*math.exp(-((z-.23*x)/.075)**2)*max(0,math.cos(a))
                if kind=='liver':
                    z+=.22*math.sin(a+1)*rr
                    x*=1+.17*y
                    x+=.13*rr*rr
                    z-=.09*math.exp(-((x+.1)/.16)**2)
                if kind=='stomach': x+=.28*z*z-.12; y+=.12*math.sin(lat*4)
            vx=x*size[0]/2; vy=y*size[1]/2
            verts.append((center[0]+vx*math.cos(rotation)-vy*math.sin(rotation),center[1]+vx*math.sin(rotation)+vy*math.cos(rotation),center[2]+z*size[2]/2))
            uv.append((c/cols,r/rows)); weights.append([(bone or 'krasue_head',1)])
    for r in range(rows):
        for c in range(cols):
            a=r*(cols+1)+c; fs.append((a,a+1,a+cols+2,a+cols+1))
    return mesh(name,verts,fs,[mat],uv,weights=weights)
tooth_rng=random.Random(5113)
for name in ('upper_teeth','lower_teeth'):
    pv,_,_,pd=head_parts.pop(name)
    xs=[v.x for v in pv];front=max(v.y for v in pv);zc=sum(v.z for v in pv)/len(pv)
    half=(max(xs)-min(xs))/2*.92;upper=name.startswith('upper')
    for i in range(10):
        u=(i+.5)/10*2-1
        if tooth_rng.random()<.12: continue  # lost
        canine=abs(abs(u)-.55)<.12
        # At the creature's scale (about 2.6 times life): long, uneven, yellowed.
        length=(.036 if canine else .025)*tooth_rng.uniform(.8,1.15)*(1 if abs(u)<.8 else .8)
        cx=u*half;cy=front-.006-(abs(u)**2)*.03
        cz=zc+(-1 if upper else 1)*(-.004)-(length/2 if upper else -length/2)
        tooth=blob(f'krasue_tooth_{name}_{i}',(cx+tooth_rng.uniform(-.001,.001),cy,cz),
                   (.019*(1-.3*abs(u)),.014,length),teeth,rotation=-u*.9+tooth_rng.uniform(-.12,.12))
        tooth.shape_key_add(name='Basis');key=tooth.shape_key_add(name='Scream')
        mean=pd[0]
        for v,k in zip(tooth.data.vertices,key.data):k.co=v.co+mean
        MAKEHUMAN.add(tooth.name)
for name,(pv,pf,puv,pd) in head_parts.items():
    data=bpy.data.meshes.new('krasue_'+name);data.from_pydata(pv,[],pf);data.update()
    layer=data.uv_layers.new(name='UVMap')
    for poly,uvs in zip(data.polygons,puv):
        for li,u in zip(poly.loop_indices,uvs):layer.data[li].uv=u
    data.materials.append(eye if name.startswith('eye') else gum)
    obj=bpy.data.objects.new('krasue_'+name,data);bpy.context.collection.objects.link(obj)
    rigged(obj,None if name.startswith('eye') else pd)
    MAKEHUMAN.add(obj.name)

# Tube builder gives a circular cross-section, taper, UVs and interpolated skinning.
def tubes(name, paths, mat, bones=None):
    vs=[]; fs=[]; uvs=[]; ws=[]
    for path,radius in paths:
        n=len(path); sides=3 if 'hair' in name else 9; start=len(vs)
        for i,p in enumerate(path):
            t=i/(n-1); tangent=Vector(path[min(n-1,i+1)])-Vector(path[max(0,i-1)])
            tangent.normalize(); ref=Vector((1,0,0)) if abs(tangent.x)<.85 else Vector((0,1,0))
            nrm=tangent.cross(ref).normalized(); bit=tangent.cross(nrm).normalized()
            rad=radius(t) if callable(radius) else radius
            if bones:
                v=t*(len(bones)-1); index=min(len(bones)-2,int(v)); f=v-index
                weight=[(bones[index],1-f),(bones[index+1],f)]
            else: weight=[('krasue_head',1)]
            for j in range(sides):
                a=j/sides*2*math.pi; pt=Vector(p)+(nrm*math.cos(a)+bit*math.sin(a))*rad
                vs.append(tuple(pt)); uvs.append((j/sides,t*4)); ws.append(weight)
            if i:
                for j in range(sides):
                    a=start+(i-1)*sides+j; b=start+(i-1)*sides+(j+1)%sides
                    fs.append((a,b,b+sides,a+sides))
        fs.append(tuple(start+j for j in reversed(range(sides))))
        fs.append(tuple(start+(n-1)*sides+j for j in range(sides)))
    return mesh(name,vs,fs,[mat],uvs,weights=ws)



# Scalp cap, covering crown and rear skull while preserving the face.
vs=[]; fs=[]; uvs=[]
for r in range(25):
    for c in range(97):
        a=c/96*2*math.pi
        # A dense fitted underlayer extends to the temples, jaw sides and nape.
        # Only the central face remains exposed; the head cannot read as bald
        # between a few isolated strands, including in the profile view.
        end=-.27+.45*max(0,math.cos(a))**2.5+math.sin(a*7)*.003
        z=.292+(end-.292)*(r/24)**.9
        vs.append(on_head(a,z,.007))
        uvs.append((c/96,r/24))
for r in range(24):
    for c in range(96):
        a=r*97+c;fs.append((a,a+1,a+98,a+97))
mesh('krasue_scalp',vs,fs,[hair_roots],uvs)

# Motion groups only: the visible mane consists entirely of independent fine
# fibers. No hanging solid cores or broad lock surfaces are exported.
for lock in range(18):
    a=lock/18*2*math.pi
    start=Vector((math.sin(a)*.125,math.cos(a)*.105,.20))
    length=.69+random.random()*.36
    side=math.sin(a); front=math.cos(a)>.25
    center=[]
    for k in range(25):
        t=k/24
        if t<.24:
            f=t/.24
            x=side*(.008+.15*math.sin(f*math.pi/2))
            y=math.cos(a)*(.008+.13*math.sin(f*math.pi/2))
            z=.291-.135*f**1.7
        else:
            f=(t-.24)/.76
            x=side*(.158+.045*math.sin(f*math.pi*.7))
            if front:
                x=side*(.145+.055*math.sin(f*math.pi*.6))
                if lock==0:x=-.075*math.sin(f*math.pi*.75)
                if lock in [1,17]:x+=(1 if side>0 else -1)*(.11 if lock==1 else .055)*min(1,f/.35)
            y=math.cos(a)*(.162 if front else .148)-.075*f*f
            z=.156-f*length
        center.append((x,y,z))
    bones=chain(f'krasue_hair_{lock:02}',[center[0],center[8],center[16],center[24],(center[-1][0],center[-1][1],center[-1][2]-.04)])
    paths=[]; highlights=[]
    # 144 independently rooted fibers per group, spread through a volume instead
    # of arranged around the outline of a large rope. Nine rings and triangular
    # cross-sections keep 2,592 strands within the existing geometry budget.
    for strand in range(144):
        angle=a+random.uniform(-.24,.24)
        root=random.uniform(.05,.88)
        strand_length=random.uniform(.66,1.12)
        if math.cos(angle)<0:strand_length+=.08
        phase=random.random()*math.tau
        # Renderable fibers need a small screen-space presence at the window;
        # finer flyaways retain the soft edge without making the whole mane
        # break into subpixel dots under the game's temporal rendering.
        radius=random.uniform(.00058,.00085)
        flyaway=strand%17==0
        if flyaway:radius*=.4
        spread=random.uniform(.88,1.12)
        path=[]
        for k in range(9):
            t=k/8
            if t<=.25:
                f=t/.25
                phi=root+(1.05-root)*f
                z=.29-.134*(phi/1.05)**1.7
                x,y,_=on_head(angle,z,.009)
            else:
                f=(t-.25)/.75
                x=math.sin(angle)*(.154+.045*math.sin(f*math.pi*.7))*spread
                y=math.cos(angle)*(.148+.008*math.sin(phase))-.065*f*f
                if math.cos(angle)>.7:
                    # A soft asymmetric part leaves an eye visible between
                    # individual wisps while the temples remain densely filled.
                    x+=(.1 if math.sin(angle)>0 else -.1)*min(1,f/.25)
                    if strand%7==0:x-=.025*math.sin(f*math.pi)
                    y+=.015
                z=.156-f*strand_length
                wave=(.0035 if not flyaway else .017)*f
                x+=math.sin(f*5+phase)*wave
                y+=math.cos(f*4.3+phase)*wave
            path.append((x,y,z))
        target=highlights if strand%6==0 else paths
        target.append((path,lambda t,r=radius:r*(1-.82*t**1.3)))
    tubes(f'krasue_hair_lock_{lock:02}',paths,hair,bones)
    tubes(f'krasue_hair_fine_{lock:02}',highlights,hair_glint,bones)

organ_bones=chain('krasue_organs',[(0,0,-.24),(0,0,-.43),(0,0,-.70),(0,0,-.96)])
# Connective tissue/trachea and the suspended organ mass.
tubes('krasue_throat',[([(0,0,-.23),(0,.004,-.31),(0,-.005,-.4),(0,0,-.49)],lambda t:.021*(1-.12*t))],flesh,organ_bones)
trachea=[]
for i in range(11):
    z=-.285-i*.011
    trachea.append(([(math.sin(a/18*2*math.pi)*.021,math.cos(a/18*2*math.pi)*.021,z) for a in range(19)],.0014))
tubes('krasue_tracheal_ridges',trachea,flesh,organ_bones)
blob('krasue_heart',(-.016,.052,-.50),(.13,.10,.21),flesh,'heart',organ_bones[0],-.2)
for s in [-1,1]:
    blob(f'krasue_lung_{s}',(s*.079,-.005,-.49),(.112,.075,.25),flesh,'lung',organ_bones[0],s*.25)
blob('krasue_liver',(-.027,.008,-.63),(.23,.12,.13),liver_mat,'liver',organ_bones[1],.18)
blob('krasue_stomach',(.026,.025,-.765),(.12,.10,.19),flesh,'stomach',organ_bones[1])
# Anatomical branching vessels, following the lobes instead of spanning like ribs.
paths=[]
for s in [-1,1]:
    for i in range(7):
        paths.append(([(s*.018,.041,-.365-i*.009),(s*.046,.05,-.40-i*.018),(s*(.071+.009*math.sin(i)),.045,-.43-i*.02)],.0018))
for i in range(4):
    paths.append(([(.012-i*.009,.072,-.56),(.026-i*.012,.108,-.5),(.017-i*.011,.101,-.44)],.002))
for i in range(5):
    paths.append(([(-.1+i*.038,.066,-.61),(-.07+i*.034,.076,-.63),(-.06+i*.03,.069,-.66)],.0017))
tubes('krasue_organ_vessels',paths,vessel,organ_bones)
# A folded, thin solid mesentery connects the hanging bundle. It has two
# physical surfaces and stitched edges, with veins and folds on both sides.
vs=[];fs=[];uv=[];rows=18;cols=12
for layer in range(2):
    for r in range(rows+1):
        t=r/rows; width=.098*(1-.62*t)
        for c in range(cols+1):
            u=c/cols
            vs.append(((u-.5)*2*width,-.025+math.sin(u*math.pi*3+t*4)*.008+layer*.003,-.69-t*.36))
            uv.append((u,t))
size=(rows+1)*(cols+1)
for r in range(rows):
    for c in range(cols):
        a=r*(cols+1)+c;fs.append((a,a+1,a+cols+2,a+cols+1))
        fs.append((a+size,a+cols+1+size,a+cols+2+size,a+1+size))
border=list(range(cols+1))+[r*(cols+1)+cols for r in range(1,rows+1)]+[rows*(cols+1)+c for c in range(cols-1,-1,-1)]+[r*(cols+1) for r in range(rows-1,0,-1)]
for a,b in zip(border,border[1:]+border[:1]): fs.append((a,b,b+size,a+size))
mesh('krasue_mesenteric_folds',vs,fs,[flesh],uv,weights=[[(organ_bones[1],1)]]*len(vs))
# Coiled intestinal bundle and five individually skinned hanging loops.
for loop in range(5):
    center=[]
    length=.45+loop*.105
    for k in range(49):
        t=k/48
        if loop<2:
            center.append(((-.025 if loop==0 else .025)+math.sin(t*math.pi*2+loop*.8)*.065,.025+math.cos(t*math.pi*2+loop)*.04,-.78-math.sin(t*math.pi)*(.25+loop*.04)))
        else:
            center.append((math.sin(t*math.pi*1.4+loop*1.3)*(.06+.018*loop)*math.sin(t*math.pi*.85),.025+math.cos(t*math.pi*4+loop)*.035,-.77-t*length))
    bones=chain(f'krasue_gut_{loop}',[center[0],center[12],center[24],center[36],center[48],(center[-1][0],center[-1][1],center[-1][2]-.04)])
    tubes(f'krasue_intestine_{loop}',[(center,lambda t:.011*(1-.48*t)+.001*math.sin(t*40))],flesh,bones)
    vessels=[([(x+.005,y+.008,z) for x,y,z in center],.0014)]
    tubes(f'krasue_intestine_vessel_{loop}',vessels,vessel,bones)

# Blood still running off it: strings of it from the torn neck and the lowest
# organs, thickening into drops at their ends, swinging behind as it flies.
drip_rng=random.Random(9127)
for k in range(9):
    if k<5:
        a=k/5*math.tau+drip_rng.uniform(-.3,.3)
        top=(math.sin(a)*.07,math.cos(a)*.055,stump_z-.01)
    else:
        top=(drip_rng.uniform(-.06,.06),drip_rng.uniform(0,.05),-.83-drip_rng.uniform(0,.12))
    length=drip_rng.uniform(.12,.42)
    path=[(top[0]+.004*math.sin(t*9+k),top[1]+.003*math.cos(t*7+k),top[2]-t*length) for t in (i/10 for i in range(11))]
    bones=chain(f'krasue_gut_{5+k}',[path[0],path[4],path[8],path[10],(path[10][0],path[10][1],path[10][2]-.02)])
    # Thin and stretched where it hangs, a heavy bead at the bottom.
    tubes(f'krasue_blood_drip_{k}',[(path,lambda t:.0022+.0008*math.sin(t*13)+.0055*max(0,(t-.86)/.14)**.6)],vessel,bones)

# Consolidate static facial detail to avoid a draw for every tooth/eyeball.
for mat in [eye,teeth]:
    objs=[o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.data.materials)==1 and o.data.materials[0]==mat]
    if len(objs)>1:
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:o.select_set(True)
        bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join()
        objs[0].name='krasue_'+mat.name.removeprefix('M_krasue_')
        objs[0].data.name=objs[0].name

for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH' or obj.data.shape_keys: continue
    bm=bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data); bm.free(); obj.data.update()

bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
for o in bpy.context.scene.objects:
    if o.type=='MESH':o.select_set(True)
bpy.context.view_layer.objects.active=rig
for image in bpy.data.images:
    if image.filepath and not image.packed_file: image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(Path(__file__).with_name('krasue.blend')))
bpy.ops.export_scene.gltf(filepath=str(OUT/'krasue-creature.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_yup=True,export_normals=True,export_texcoords=True,export_materials='EXPORT',export_image_format='AUTO',export_vertex_color='ACTIVE')
print('KRASUE_EXPORT',sum(len(o.data.polygons) for o in bpy.context.scene.objects if o.type=='MESH'),'polygons',len(rig.data.bones),'bones')

if '--preview' in sys.argv:
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=20
    scene.render.resolution_x=640; scene.render.resolution_y=850; scene.render.resolution_percentage=100
    scene.world.color=(.035,.035,.035)
    def area(name,at,power,color,size):
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=at
        obj.rotation_euler=(Vector((0,0,-.4))-obj.location).to_track_quat('-Z','Y').to_euler()
    area('moon',(-1.3,1.8,1.5),80,(.71,.82,1),2)
    area('rim',(1,-.7,.6),90,(.7,.8,1),1.2)
    area('fill',(1.3,1.8,-.5),30,(1,.74,.58),1.8)
    camdata=bpy.data.cameras.new('review');cam=bpy.data.objects.new('review',camdata);scene.collection.objects.link(cam);scene.camera=cam
    camdata.type='ORTHO';camdata.ortho_scale=2.1
    for name,at in [('front',(0,3,.0)),('profile',(3,.7,0))]:
        cam.location=at;cam.rotation_euler=(Vector((0,0,-.6))-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(ROOT/'debug-shots'/('krasue-3d-'+name+'.png'))
        bpy.ops.render.render(write_still=True)
    for obj in scene.objects:
        if obj.type=='MESH' and obj.data.shape_keys:obj.data.shape_keys.key_blocks['Scream'].value=1
    cam.location=(.7,3,.0);cam.rotation_euler=(Vector((0,0,-.5))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(ROOT/'debug-shots'/'krasue-3d-scream.png')
    bpy.ops.render.render(write_still=True)
