"""Build the full-volume Krasue, with GPU-skinned hair/viscera and PBR maps.
Run: Blender --background --python art-source/characters/krasue/build_krasue.py
Metres, +Y facing, +Z up. GLB exports to Babylon +Z facing / +Y up.
"""
import bpy, bmesh, math, random, sys
import numpy as np
from mathutils import Vector
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'public/assets/ep1/krasue'
OUT.mkdir(parents=True, exist_ok=True)
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
    image.filepath_raw = str(OUT / (name + '.png'))
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
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw=str(OUT/'krasue_hair_fibers.png');img.file_format='PNG';img.save()
    return img
hair_color=hair_albedo()

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
        tex.image=bpy.data.images.load(str(OUT/'krasue-apparition.png'),check_existing=True)
        # Only RGB is used: this is the albedo of a solid, closed head.
        m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    if normal:
        tex=m.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=normal
        nm=m.node_tree.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value=.45 if photo else .8 if 'hair' in name else .7
        m.node_tree.links.new(tex.outputs['Color'],nm.inputs['Color'])
        m.node_tree.links.new(nm.outputs['Normal'],p.inputs['Normal'])
    return m
face=material('M_krasue_face',(.28,.25,.22),.73,skin_normal,True)
skin=material('M_krasue_skin',(.09,.076,.062),.86,skin_normal)
hair=material('M_krasue_hair',(.009,.007,.006),.64,hair_normal)
hair_glint=material('M_krasue_hair_glint',(.014,.011,.009),.68,hair_normal)
hair_roots=material('M_krasue_hair_roots',(.004,.003,.002),.94,hair_normal)
hair_roots.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.06
flesh=material('M_krasue_viscera',(.095,.012,.017),.54,organ_normal)
liver_mat=material('M_krasue_liver',(.052,.012,.017),.61,organ_normal)
vessel=material('M_krasue_vessels',(.038,.008,.016),.62,organ_normal)
cavity=material('M_krasue_cavity',(.008,.003,.004),.94)
eye=material('M_krasue_sclera',(.32,.36,.32),.34)
iris=material('M_krasue_iris',(.029,.036,.032),.4)
teeth=material('M_krasue_teeth',(.31,.27,.19),.72,skin_normal)
lip=material('M_krasue_lips',(.075,.033,.032),.62,skin_normal)
gum=material('M_krasue_gums',(.065,.018,.023),.48,organ_normal)

# Spatial pigment follows the lobes and folds, rather than one uniform red.
# Linear vertex colors survive glTF export without a texture-baking shortcut.
for tissue in [flesh,liver_mat]:
    p=tissue.node_tree.nodes.get('Principled BSDF')
    p.inputs['Coat Weight'].default_value=.12
    p.inputs['Coat Roughness'].default_value=.34
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

def gauss(x,z,cx,cz,sx,sz): return math.exp(-((x-cx)/sx)**2-((z-cz)/sz)**2)
# Continuous asymmetric cranial profile, with actual sculpted facial anatomy.
profile=[(-.265,.008,.025),(-.24,.060,.080),(-.19,.096,.107),(-.12,.123,.114),(-.04,.141,.128),(.04,.148,.129),(.12,.148,.124),(.19,.132,.108),(.25,.090,.065),(.285,.004,.004)]
def dimensions(z):
    for a,b in zip(profile,profile[1:]):
        if a[0]<=z<=b[0]:
            t=(z-a[0])/(b[0]-a[0]); t=t*t*(3-2*t)
            return a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t
    return .004,.004
verts=[]; uv=[]; faces=[]; slots=[]
R,C=104,144
for r in range(R+1):
    z=-.265+r/R*.55; width,depth=dimensions(z)
    for c in range(C+1):
        a=-math.pi+2*math.pi*c/C
        x=math.sin(a)*width; front=max(0,math.cos(a))
        y=math.cos(a)*(depth if front else depth*1.25)
        sculpt=0
        if front:
            sculpt+=.047*gauss(x,z,0,-.062,.021,.034)+.023*gauss(x,z,0,.001,.014,.078)
            sculpt+=.013*gauss(x,z,-.024,-.073,.014,.014)+.013*gauss(x,z,.024,-.073,.014,.014)
            for s in [-1,1]:
                sculpt-=.030*gauss(x,z,s*.065,.027,.035,.020)
                sculpt+=.019*gauss(x,z,s*.065,.064,.046,.011)
                sculpt+=.013*gauss(x,z,s*.091,-.048,.027,.039)
                sculpt-=.012*gauss(x,z,s*.092,-.104,.034,.039)
            # A real recessed oral bowl; its material and vertices deform with
            # the jaw, instead of stretching a painted mouth across the face.
            oral=(x/.053)**2+((z+.151)/.014)**2
            sculpt-=.067*max(0,1-oral)**.45
            for s in [-1,1]:
                fold=s*(.035+max(0,-z-.08)*.38)
                sculpt-=.0027*gauss(x,z,fold,-.12,.003,.037)
                sculpt-=.0017*gauss(x,z,s*.065,.074,.037,.0017)
                sculpt-=.0014*gauss(x,z,s*.075,.083,.034,.0016)
            sculpt+=.007*gauss(x,z,0,-.133,.047,.007)+.008*gauss(x,z,0,-.168,.041,.010)
            sculpt+=.009*gauss(x,z,0,-.222,.047,.023)
            # Fine irregularity breaks mathematically smooth skin under grazing light.
            sculpt+=.00045*math.sin(x*331+z*19)*math.sin(z*281)
            y+=sculpt*front**6
        verts.append((x,y,z))
        uv.append((.5+x*.77,1-(310-z*600)/1536) if front>.35 else (c/C,r/R))
for r in range(R):
    for c in range(C):
        a=r*(C+1)+c; faces.append((a,a+1,a+C+2,a+C+1))
        angle=-math.pi+2*math.pi*(c+.5)/C
        x=(verts[a][0]+verts[a+1][0])/2
        z=(verts[a][2]+verts[a+C+1][2])/2
        oral=(x/.053)**2+((z+.151)/.014)**2
        slots.append(2 if math.cos(angle)>.8 and oral<.85 else 0 if math.cos(angle)>.35 else 1)
faces.append(tuple(range(C-1,-1,-1))); slots.append(1)
faces.append(tuple(R*(C+1)+c for c in range(C))); slots.append(1)
mesh('krasue_sculpted_head',verts,faces,[face,skin,cavity],uv,slots)

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
for s in [-1,1]:
    blob(f'krasue_eye_{s}',(s*.065,.113,.027),(.032,.029,.019),eye)
    blob(f'krasue_iris_{s}',(s*.065,.128,.027),(.012,.004,.012),iris)
    blob(f'krasue_nostril_{s}',(s*.019,.165,-.078),(.012,.006,.007),cavity)
for row in [0,1]:
    for i in range(-3,4):
        # Slightly uneven, curved dental arches, recessed behind the lip.
        blob(f'krasue_tooth_{row}_{i}',(i*.0105,.114-.009*(abs(i)/3)**2,-.143-row*.016),(.0085,.010,.012+random.random()*.003),teeth)
blob('krasue_tongue',(0,.084,-.157),(.047,.026,.009),gum)

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

# Raised lips and eyelid edges catch real light even from the side.
paths=[]
for row in [0,1]:
    path=[]
    for i in range(41):
        a=math.pi*i/40
        x=.054*math.cos(a)
        z=-.151+(1 if row==0 else -1)*.014*math.sin(a)
        y=.119-.008*(abs(x)/.054)**2+.003*math.sin(a)
        path.append((x,y,z))
    paths.append((path,lambda t:.0024+.0012*math.sin(t*math.pi)))
tubes('krasue_lip_rims',paths,lip)
paths=[]
for row in [0,1]:
    paths.append(([(i*.0095,.109-.007*(i/3)**2,-.137-row*.030) for i in range(-3,4)],.0038))
tubes('krasue_dental_gums',paths,gum)
paths=[]
for s in [-1,1]:
    for row in [0,1]:
        paths.append(([(s*.065+.018*math.cos(a/24*math.pi),.123+.003*math.sin(a/24*math.pi),.027+(1 if row==0 else -1)*.011*math.sin(a/24*math.pi)) for a in range(25)],.0018))
tubes('krasue_eyelid_rims',paths,skin)

# Scalp cap, covering crown and rear skull while preserving the face.
vs=[]; fs=[]; uvs=[]
for r in range(25):
    for c in range(97):
        a=c/96*2*math.pi
        # A dense fitted underlayer extends to the temples, jaw sides and nape.
        # Only the central face remains exposed; the head cannot read as bald
        # between a few isolated strands, including in the profile view.
        end=-.205+.385*max(0,math.cos(a))**2.5+math.sin(a*7)*.003
        z=.286+(end-.286)*r/24; w,d=dimensions(min(.284,z))
        vs.append((math.sin(a)*(w+.010),math.cos(a)*(d+.010 if math.cos(a)>0 else d*1.25+.012),z))
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
                z=.287-.131*(phi/1.05)**1.7
                w,d=dimensions(min(.284,z))
                x=math.sin(angle)*(w+.008)
                y=math.cos(angle)*(d+.010 if math.cos(angle)>0 else d*1.25+.010)
            else:
                f=(t-.25)/.75
                x=math.sin(angle)*(.154+.045*math.sin(f*math.pi*.7))*spread
                y=math.cos(angle)*(.148+.008*math.sin(phase))-.065*f*f
                if math.cos(angle)>.7:
                    # A soft asymmetric part leaves an eye visible between
                    # individual wisps while the temples remain densely filled.
                    x+=(.06 if math.sin(angle)>0 else -.06)*min(1,f/.25)
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

# Consolidate static facial detail to avoid a draw for every tooth/eyeball.
for mat in [eye,iris,cavity,teeth]:
    objs=[o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.data.materials)==1 and o.data.materials[0]==mat]
    if len(objs)>1:
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:o.select_set(True)
        bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join()
        objs[0].name='krasue_'+mat.name.removeprefix('M_krasue_')
        objs[0].data.name=objs[0].name

for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH': continue
    bm=bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data); bm.free(); obj.data.update()

# Shared jaw displacement makes the closed head, lip margins, dental arches and
# tongue open as one anatomical form. Cheeks/chin stretch, temples stay fixed.
def jaw_displacement(v):
    x,y,z=v
    front=max(0,min(1,(y-.025)/.065))
    side=math.exp(-(abs(x)/.088)**6)
    lower=max(0,min(1,(-z-.143)/.025))
    chin=max(0,min(1,(z+.272)/.030))
    influence=front*side*chin
    lift=.010*math.exp(-((z+.137)/.019)**2)*(1-lower)
    drop=.073*lower
    return (x*.025*influence*lower,-.015*influence*lower,(lift-drop)*influence)
for obj in list(bpy.context.scene.objects):
    if obj.type!='MESH':continue
    facial=obj.name=='krasue_sculpted_head' or obj.name in ['krasue_lip_rims','krasue_teeth','krasue_gums','krasue_tongue','krasue_dental_gums']
    if not facial:continue
    obj.shape_key_add(name='Basis')
    opened=obj.shape_key_add(name='Scream')
    if obj.name=='krasue_teeth':
        # Teeth translate rigidly with the jaw; unlike skin they cannot stretch.
        links=[set() for v in obj.data.vertices]
        for edge in obj.data.edges:
            a,b=edge.vertices;links[a].add(b);links[b].add(a)
        remaining=set(range(len(links)))
        while remaining:
            stack=[remaining.pop()];island=[]
            while stack:
                i=stack.pop();island.append(i)
                for j in links[i]&remaining:remaining.remove(j);stack.append(j)
            center=sum((obj.data.vertices[i].co for i in island),Vector())/len(island)
            delta=Vector(jaw_displacement(center))
            for i in island:opened.data[i].co=obj.data.vertices[i].co+delta
    else:
        for v,p in zip(obj.data.vertices,opened.data):p.co=v.co+Vector(jaw_displacement(v.co))

bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
for o in bpy.context.scene.objects:
    if o.type=='MESH':o.select_set(True)
bpy.context.view_layer.objects.active=rig
for image in bpy.data.images:
    if image.filepath and not image.packed_file: image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(Path(__file__).with_name('krasue.blend')))
bpy.ops.export_scene.gltf(filepath=str(OUT/'krasue-creature.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_yup=True,export_normals=True,export_texcoords=True,export_materials='EXPORT',export_image_format='AUTO')
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
