"""Author the taxi cabin and roadside from the episode's existing CC0 materials/plants.
blender -b --factory-startup -P tools/travel/build-taxi.py
World helpers use Babylon axes (x right, y up, z forward); export uses project glTF conversion.
"""
import bpy, math, sys, json
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/areas'))
from kit import library_material, plain, world_uvs
OUT = ROOT/'art-export/ep1'
OUT.mkdir(parents=True, exist_ok=True)
ART = ROOT/'art-source/blender/ep1'
TEX = ROOT/'art-source/textures/ep1/taxi'
TEX.mkdir(parents=True, exist_ok=True)

def w(p): return Vector((-p[0], -p[2], p[1]))
def mesh(name, vertices, faces, mat=None, uv=True):
    m=bpy.data.meshes.new(name); m.from_pydata([w(v) for v in vertices], [], [tuple(reversed(f)) for f in faces]); m.update()
    o=bpy.data.objects.new(name,m); bpy.context.collection.objects.link(o)
    if mat: m.materials.append(mat)
    if uv and mat: world_uvs(o)
    return o

def rounded(name, at, size, mat, radius=.015):
    x,y,z=at; a,b,c=[v/2 for v in size]
    vs=[(x+i*a,y+j*b,z+k*c) for i in [-1,1] for j in [-1,1] for k in [-1,1]]
    fs=[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]
    o=mesh(name,vs,fs,mat)
    bevel=o.modifiers.new('Soft manufactured edges','BEVEL'); bevel.width=radius; bevel.segments=4
    n=o.modifiers.new('Weighted panel normals','WEIGHTED_NORMAL'); n.keep_sharp=True
    return o

def tube(name, points, r, mat, sides=10):
    curve=bpy.data.curves.new(name,'CURVE'); curve.dimensions='3D'; curve.resolution_u=2
    curve.bevel_depth=r; curve.bevel_resolution=2
    spline=curve.splines.new('POLY'); spline.points.add(len(points)-1)
    for p,co in zip(spline.points,points): p.co=(*w(co),1)
    o=bpy.data.objects.new(name,curve); bpy.context.collection.objects.link(o); curve.materials.append(mat)
    return o

def ellipsoid(name, at, size, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=w(at))
    o=bpy.context.object; o.name=name; o.scale=(size[0]/2,size[2]/2,size[1]/2); o.data.materials.append(mat)
    for f in o.data.polygons: f.use_smooth=True
    world_uvs(o); return o

def quad(name, corners, mat):
    o=mesh(name,corners,[(0,1,2,3)],mat,False)
    layer=o.data.uv_layers.new(name='UVMap')
    for p in o.data.polygons:
        for li in p.loop_indices:
            # reverse-winding faces keep world orientation; vertex UVs remain explicit.
            layer.data[li].uv=[(0,0),(1,0),(1,1),(0,1)][o.data.loops[li].vertex_index]
    return o

def label(name, text, at, size, mat):
    data=bpy.data.curves.new(name,'FONT'); data.body=text; data.size=size
    data.align_x='CENTER'; data.align_y='CENTER'; data.extrude=.00015
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj)
    obj.matrix_world=Matrix(((-1,0,0,0),(0,0,1,0),(0,1,0,0),(0,0,0,1)))
    obj.location=w(at); data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bpy.ops.object.convert(target='MESH')
    return obj

def export(name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o.type in {'MESH','EMPTY','CURVE'}: o.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ART/(name+'.blend')))
    bpy.ops.export_scene.gltf(filepath=str(OUT/(name+'.glb')), export_format='GLB', use_selection=True, export_extras=True, export_yup=True, export_apply=True, export_cameras=False, export_lights=False)
    print('TAXI_EXPORTED',name,len(bpy.context.scene.objects))

def grain_material():
    rng=np.random.default_rng(947)
    n=1024
    yy,xx=np.mgrid[:n,:n]
    def smooth(scale):
        noise=rng.normal(size=(n,n)); f=np.fft.rfft2(noise)
        fy=np.fft.fftfreq(n)[:,None]; fx=np.fft.rfftfreq(n)[None,:]
        a=np.fft.irfft2(f*np.exp(-(fx*fx+fy*fy)*scale*scale),s=(n,n))
        return (a-a.mean())/(a.std()+1e-8)
    pores=smooth(5); pebbles=smooth(22); age=smooth(95)
    height=pores*.18+pebbles*.5
    color=np.clip(.35+.055*pores+.045*pebbles+.035*age, .15,.65)
    bc=np.stack([color*.82,color*.72,color*.53],axis=-1)
    dx,dy=np.gradient(height)
    normal=np.stack([-dy*.7,-dx*.7,np.ones_like(height)],axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    rough=np.clip(.68+pores*.04+age*.05,.45,.9)
    orm=np.stack([np.ones_like(rough),rough,np.zeros_like(rough)],axis=-1)
    def image(suffix,array):
        img=bpy.data.images.new('T_taxi_vinyl_'+suffix,width=n,height=n,alpha=True)
        img.pixels.foreach_set(np.concatenate([array,np.ones((n,n,1))],axis=-1).astype(np.float32).ravel())
        img.filepath_raw=str(TEX/('T_taxi_vinyl_'+suffix+'.png')); img.file_format='PNG'
        if suffix!='BC': img.colorspace_settings.name='Non-Color'
        img.save(); return img
    images=[image('BC',bc),image('N',normal*.5+.5),image('ORM',orm)]
    mat=plain('M_taxi_worn_vinyl',(.08,.06,.035),.75); mat['tile']=.22
    ns=mat.node_tree.nodes; links=mat.node_tree.links; bs=ns.get('Principled BSDF')
    maps=[]
    for img in images: t=ns.new('ShaderNodeTexImage'); t.image=img; maps.append(t)
    links.new(maps[0].outputs['Color'],bs.inputs['Base Color'])
    no=ns.new('ShaderNodeNormalMap'); links.new(maps[1].outputs['Color'],no.inputs['Color']); no.inputs['Strength'].default_value=.45; links.new(no.outputs['Normal'],bs.inputs['Normal'])
    split=ns.new('ShaderNodeSeparateColor'); links.new(maps[2].outputs['Color'],split.inputs[0]); links.new(split.outputs['Green'],bs.inputs['Roughness'])
    return mat

def cabin():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    vinyl=grain_material()
    felt=library_material('rough_linen','M_taxi_headliner',colour=(.075,.07,.055),tile=.12)
    cloth=library_material('waffle_pique_cotton','M_taxi_driver_cotton',colour=(.13,.115,.08),tile=.16)
    carpet=library_material('rough_linen','M_taxi_carpet',colour=(.022,.025,.021),tile=.08)
    wood=library_material('teak_veneer','M_taxi_dashboard_walnut',tint=(.31,.21,.13),tile=.65)
    rubber=plain('M_taxi_rubber',(.012,.014,.012),.75)
    chrome=plain('M_taxi_aged_nickel',(.26,.285,.26),.3,.8)
    black=plain('M_taxi_bakelite',(.021,.024,.021),.28)
    thread=plain('M_taxi_stitching',(.11,.085,.048),.9)
    metal=plain('M_taxi_painted_steel',(.045,.067,.058),.32,.45)
    glass=plain('M_taxi_window_glass',(.07,.095,.11),.13,.05,alpha=.07)
    glass.use_backface_culling=False
    # A closed opaque tub: the trim and seat cushions are not the car body.
    # Overlap seams so looking down/sideways never exposes the moving road.
    for mat in [carpet,metal,vinyl,rubber]: mat.use_backface_culling=False
    rounded('taxi_floorpan_sealed',(0,-.005,-.17),(1.86,.09,3.18),metal,.018)
    rounded('taxi_firewall_sealed',(0,.44,1.20),(1.85,.96,.16),carpet,.035)
    rounded('taxi_rear_bulkhead_sealed',(0,.56,-1.75),(1.85,1.18,.11),vinyl,.025)
    for side in [-1,1]:
        rounded(f'taxi_lower_body_sealed_{side}',(side*.885,.44,-.22),(.13,.94,2.98),metal,.025)
        rounded(f'taxi_footwell_lining_{side}',(side*.813,.25,-.14),(.025,.48,2.83),carpet,.012)
        rounded(f'taxi_door_sill_{side}',(side*.79,.105,-.23),(.115,.075,2.86),rubber,.015)
        for z in [-1.36,-1.02,-.5,.08,.62,.99]:
            ellipsoid('taxi_sill_fastener',(side*.79,.148,z),(.012,.004,.012),chrome)
    # Raised toe boards, grooved mats, heater and pedals fill the real footwell.
    for x in [-.43,.43]:
        rounded('taxi_rubber_footmat',(x,.063,.51),(.62,.025,.95),rubber,.035)
        for i in range(17):
            rounded('taxi_footmat_rib',(x-.27+i*.033,.079,.51),(.009,.009,.84),black,.003)
        tube('taxi_footmat_edge',[(x-.29,.077,.08),(x-.29,.077,.94),(x+.29,.077,.94),(x+.29,.077,.08),(x-.29,.077,.08)],.006,rubber)
    rounded('taxi_under_dash_heater',(0,.53,1.08),(.31,.23,.14),metal,.025)
    for i in range(9): rounded('taxi_heater_grille',(-.12+i*.03,.53,.997),(.008,.17,.007),black,.002)
    for x in [-.61,-.43,-.25]:
        tube('taxi_pedal_stalk',[(x,.08,.98),(x,.22,.83)],.008,chrome)
        rounded('taxi_pedal_pad',(x,.225,.80),(.085,.10,.033),rubber,.012)

    # Sculpted dashboard: curved top, vertical instrument fascia, padded lower roll.
    cross=[(.84,1.025),(1.01,1.035),(1.11,1.04),(1.12,1.22),(1.0,1.35),(.87,1.35),(.79,1.18)] # y,z
    vertices=[]
    for x in [-.85,-.68,-.4,0,.4,.68,.85]:
        for y,z in cross: vertices.append((x,y+.025*(1-(x/.85)**2),z))
    faces=[]; m=len(cross)
    for k in range(6):
        for j in range(m): faces.append((k*m+j,k*m+(j+1)%m,(k+1)*m+(j+1)%m,(k+1)*m+j))
    faces += [tuple(reversed(range(m))),tuple(6*m+j for j in range(m))]
    o=mesh('taxi_dashboard_sculpted',vertices,faces,vinyl)
    bevel=o.modifiers.new('Dashboard rolled lip','BEVEL'); bevel.width=.018; bevel.segments=4
    o.modifiers.new('Weighted dashboard normals','WEIGHTED_NORMAL')
    rounded('taxi_walnut_instrument_panel',(0,.958,1.014),(1.59,.18,.032),wood,.025)
    tube('taxi_dash_nickel_bead',[(-.79,.865,1.005),(0,.87,1.005),(.79,.865,1.005)],.004,chrome)
    rounded('taxi_glovebox',(.46,.933,.987),(.51,.112,.016),wood,.014)
    for x in [.24,.68]:
        rounded('taxi_glovebox_hinge',(x,.883,.973),(.065,.012,.011),chrome,.003)
    rounded('taxi_switch_mounting_plate',(-.04,.825,1.018),(.45,.09,.025),metal,.009)
    for x in [-.17,-.04,.09]:
        tube('taxi_dash_pull_switch',[(x,.825,1.018),(x,.825,.983)],.005,chrome)
        ellipsoid('taxi_dash_bakelite_switch',(x,.825,.974),(.026,.026,.016),black)
    for x in [-.72,.73]:
        ellipsoid('taxi_dash_mount_screw',(x,.958,.992),(.011,.011,.005),chrome)
    rounded('taxi_glovebox_latch',(.46,.943,.972),(.054,.018,.011),chrome,.006)
    rounded('taxi_radio',(-.02,.935,.977),(.205,.09,.025),black,.008)
    for x in [-.15,.13]:
        ellipsoid('taxi_radio_knob',(x,.935,.952),(.038,.038,.019),black)
        ellipsoid('taxi_radio_knob_rim',(x,.935,.956),(.043,.043,.012),chrome)
    for i in range(18): rounded('taxi_radio_grille',(-.108+i*.01,.935,.961),(.003,.061,.006),chrome,.001)
    for x in [-.64,-.32,.32,.65]:
        for j in range(6): rounded('taxi_demister_vent',(x+j*.009,1.08,1.18),(.003,.004,.075),rubber,.001)
    ink=plain('M_taxi_ivory_engraving',(.49,.45,.32),.8)
    rounded('taxi_cab_license_frame',(.45,1.021,.981),(.28,.027,.006),chrome,.003)
    rounded('taxi_cab_license_enamel',(.45,1.021,.976),(.268,.021,.004),black,.002)
    label('taxi_cab_license_letters','PHNOM PENH  /  208',(.45,1.021,.972),.010,ink)
    for x,text in [(-.17,'LAMPS'),(-.04,'WIPER'),(.09,'CHOKE')]:
        label('taxi_switch_engraving',text,(x,.799,1.002),.008,ink)
    # Continuous roof and body panels; a true windshield/side-window opening.
    vs=[]; fs=[]
    for k in range(12):
        z=-1.65+k/11*2.55
        for j in range(16):
            x=-.88+j/15*1.76; y=1.77+.10*(1-(x/.88)**2)-.04*((z+.4)/1.4)**2
            vs.append((x,y,z))
    for k in range(11):
        for j in range(15): a=k*16+j; fs.append((a,a+1,a+17,a+16))
    roof=mesh('taxi_headliner_curved',vs,fs,felt); roof.data.materials[0].use_backface_culling=False
    solid=roof.modifiers.new('Roof lining thickness','SOLIDIFY'); solid.thickness=.035
    for side in [-1,1]:
        x=side*.86
        rounded(f'taxi_door_trim_{side}',(x,.63,-.05),(.09,.53,2.17),vinyl,.045)
        rounded(f'taxi_door_pocket_{side}',(x-side*.058,.43,-.05),(.08,.18,.51),vinyl,.025)
        tube(f'taxi_door_pocket_binding_{side}',[(x-side*.105,.51,-.30),(x-side*.105,.525,-.05),(x-side*.105,.51,.20)],.005,thread)
        for z in [-.92,.54]:
            ellipsoid('taxi_door_card_screw',(x-side*.049,.79,z),(.006,.013,.013),chrome)
        tube(f'taxi_door_card_stitch_{side}',[(x-side*.049,.39,-1.0),(x-side*.049,.84,-1.0),(x-side*.049,.84,.58)],.0018,thread)
        rounded(f'taxi_armrest_{side}',(x-side*.043,.735,-.14),(.13,.085,.48),vinyl,.034)
        rounded(f'taxi_door_handle_{side}',(x-side*.059,.849,.37),(.021,.023,.125),chrome,.01)
        tube(f'taxi_window_crank_{side}',[(x-side*.068,.71,.29),(x-side*.068,.655,.34)],.009,chrome)
        ellipsoid('taxi_crank_grip',(x-side*.087,.652,.35),(.033,.034,.035),black)
        tube(f'taxi_door_sweep_{side}',[(x-side*.047,.88,-1.07),(x-side*.047,.91,-.3),(x-side*.047,.91,.65),(x-side*.047,1.05,1.23)],.014,rubber)
        tube(f'taxi_A_pillar_{side}',[(side*.82,1.02,1.28),(side*.80,1.3,1.13),(side*.69,1.76,.86)],.038,felt)
        tube(f'taxi_A_pillar_chrome_{side}',[(side*.83,1.03,1.28),(side*.81,1.3,1.13),(side*.70,1.76,.86)],.006,chrome)
        tube(f'taxi_B_pillar_{side}',[(x,.89,-.63),(side*.78,1.79,-.63)],.034,felt)
        tube(f'taxi_rear_pillar_{side}',[(x,.88,-1.3),(side*.76,1.77,-1.43)],.037,felt)
        quad(f'taxi_side_glass_{side}',[(x,.91,-.62),(x,.96,.79),(side*.70,1.74,.82),(side*.78,1.76,-.62)],glass)
        quad(f'taxi_quarter_glass_{side}',[(x,.89,-1.27),(x,.91,-.67),(side*.78,1.76,-.67),(side*.76,1.73,-1.39)],glass)
        rounded('taxi_sunvisor',(side*.42,1.71,.72),(.48,.13,.025),felt,.026)
    # Thin bonnet: visibility below the windshield, with rounded ridges and panel seams.
    rounded('taxi_bonnet', (0,.83,1.92),(1.57,.10,1.44),metal,.07)
    tube('taxi_bonnet_centre_ridge',[(0,.892,1.28),(0,.90,2.05),(0,.867,2.6)],.005,chrome)
    for x in [-.72,.72]: tube('taxi_bonnet_seam',[(x,.88,1.3),(x,.88,2.53)],.003,rubber)
    # Padded seat cushions, piped edges, buttoned pleats and rails.
    for side in [-1,1]:
        x=side*.41
        rounded('taxi_seat_cushion',(x,.39,-.32),(.68,.20,.72),vinyl,.085)
        rounded('taxi_seatback',(x,.82,-.72),(.69,.76,.20),vinyl,.082)
        for k in range(6):
            xx=x-.27+k*.108
            tube('taxi_seat_pleat',[(xx,.49,-.62),(xx,.497,-.30),(xx,.47,-.02)],.0025,thread)
            tube('taxi_seatback_pleat',[(xx,.51,-.598),(xx,.80,-.607),(xx,1.13,-.64)],.0025,thread)
        tube('taxi_seat_piping',[(x-.30,.43,-.64),(x-.32,.47,-.45),(x-.32,.46,-.06),(x-.27,.45,.004),(x+.27,.45,.004),(x+.32,.46,-.06),(x+.32,.47,-.45),(x+.30,.43,-.64)],.004,thread)
        for xx in [x-.22,x+.22]: rounded('taxi_seat_rail',(xx,.22,-.32),(.04,.055,.65),chrome,.008)
    rounded('taxi_rear_bench',(0,.42,-1.43),(1.54,.22,.55),vinyl,.07)
    rounded('taxi_rear_bench_back',(0,.87,-1.68),(1.54,.79,.18),vinyl,.065)
    rounded('taxi_floor_carpet',(0,.048,-.15),(1.70,.026,3.01),carpet,.02)
    rounded('taxi_transmission_tunnel',(0,.19,.1),(.21,.29,1.42),carpet,.09)
    tube('taxi_gear_lever',[(.02,.3,.36),(.02,.65,.39),(.03,.70,.36)],.012,chrome)
    ellipsoid('taxi_gear_knob',(.03,.70,.36),(.055,.055,.055),black)
    # Metal-backed rear-view mirror and overhead grab handles.
    tube('taxi_mirror_stem',[(0,1.79,.85),(0,1.64,.76)],.009,chrome)
    rounded('taxi_mirror_frame',(0,1.63,.745),(.30,.10,.022),black,.022)
    quad('taxi_mirror_surface',[(-.135,1.59,.731),(.135,1.59,.731),(.135,1.67,.731),(-.135,1.67,.731)],chrome)
    for side in [-1,1]: tube('taxi_grab_handle',[(side*.76,1.69,-.08),(side*.76,1.65,-.1),(side*.76,1.65,-.34),(side*.76,1.69,-.36)],.013,black)
    # Steering wheel in a 1930s upright driving position.
    wheelcentre=Vector((-.39,1.02,.47)); normal=Vector((0,.3,-.95)).normalized(); right=Vector((1,0,0)); up=normal.cross(right).normalized()
    tube('taxi_steering_rim',[wheelcentre+right*math.cos(k/64*math.tau)*.211+up*math.sin(k/64*math.tau)*.211 for k in range(65)],.016,black)
    for a in [math.pi/2,math.pi*7/6,math.pi*11/6]: tube('taxi_steering_spoke',[wheelcentre,wheelcentre+(right*math.cos(a)+up*math.sin(a))*.196],.009,chrome)
    ellipsoid('taxi_steering_horn',wheelcentre,(.105,.105,.052),black)
    tube('taxi_steering_column',[(-.39,.72,1.03),wheelcentre],.027,black)
    # Instrument faces are painted at runtime and occupy recessed, circular bezels.
    for x,r in [(-.49,.075),(-.29,.047)]:
        tube('taxi_instrument_bezel',[(x+r*math.cos(k/64*math.tau),.975+r*math.sin(k/64*math.tau),.986) for k in range(65)],.0045,chrome)
    # Fine door cards and stitching, no giant flat dashboard blocks.
    driver(cloth,black)
    passenger()
    export('ep1_taxi_cabin')

def character_skin(name,src,photo):
    mat=plain(name,(.30,.20,.13),.7)
    image=bpy.data.images.load(str(src/photo),check_existing=True)
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=image
    links=mat.node_tree.links; bs=mat.node_tree.nodes['Principled BSDF']; links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    # Photo-derived fine relief breaks the plastic highlight without inventing scars.
    pixels=np.array(image.pixels[:],dtype=np.float32).reshape(image.size[1],image.size[0],4)
    stride=max(1,image.size[0]//1024); rgb=pixels[::stride,::stride,:3]
    grey=rgb@np.array([.2126,.7152,.0722]); dy,dx=np.gradient(grey)
    normals=np.stack([-dx*.65,-dy*.65,np.ones_like(grey)],axis=-1)
    normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
    h,width=grey.shape
    normal=bpy.data.images.new(name+'_pores',width=width,height=h,alpha=False)
    rgba=np.concatenate([normals*.5+.5,np.ones((h,width,1))],axis=-1).astype(np.float32)
    normal.colorspace_settings.name='Non-Color'; normal.pixels.foreach_set(rgba.ravel())
    normal.filepath_raw=str(TEX/(name+'_N.png')); normal.file_format='PNG'; normal.save()
    t=mat.node_tree.nodes.new('ShaderNodeTexImage'); t.image=normal
    n=mat.node_tree.nodes.new('ShaderNodeNormalMap'); n.inputs['Strength'].default_value=.3
    links.new(t.outputs['Color'],n.inputs['Color']); links.new(n.outputs['Normal'],bs.inputs['Normal'])
    return mat

def passenger():
    """Seated lower body from Sora's own source; no head inside the camera."""
    src=ROOT/'art-source/library/makehuman-sora'
    verts=[];uvs=[];faces=[];faceuv=[];group=''
    for line in (src/'base.obj').read_text().splitlines():
        a=line.split()
        if not a:continue
        if a[0]=='v':verts.append(Vector(map(float,a[1:4])))
        elif a[0]=='vt':uvs.append(tuple(map(float,a[1:3])))
        elif a[0]=='g':group=a[1]
        elif a[0]=='f' and group=='body':
            q=[v.split('/') for v in a[1:]];faces.append([int(v[0])-1 for v in q]);faceuv.append([int(v[1])-1 for v in q])
    for name in ['asian-female-young.target','universal-female-young-averagemuscle-averageweight.target']:
        for line in (src/name).read_text().splitlines():
            if line and not line.startswith('#'):
                a=line.split();verts[int(a[0])]+=Vector(map(float,a[1:4]))
    skel=json.loads((src/'default.mhskel').read_text())
    def joint(name): return sum((verts[i] for i in skel['joints'][name]),Vector())/len(skel['joints'][name])
    hip=(joint(skel['bones']['upperleg01.L']['head'])+joint(skel['bones']['upperleg01.R']['head']))/2
    kept=[(f,uv) for f,uv in zip(faces,faceuv) if max(verts[i].y for i in f)<hip.y+.9 and max(abs(verts[i].x) for i in f)<2.6]
    faces=[f for f,uv in kept]; faceuv=[uv for f,uv in kept]
    ids=sorted(set(i for f in faces for i in f)); remap={v:i for i,v in enumerate(ids)}
    data=bpy.data.meshes.new('taxi_sora_anatomical_legs');data.from_pydata([verts[i] for i in ids],[],[[remap[i] for i in f] for f in faces]);data.update()
    body=bpy.data.objects.new('taxi_sora_legs',data);bpy.context.collection.objects.link(body)
    uv=data.uv_layers.new(name='MakeHumanUV')
    for poly,indices in zip(data.polygons,faceuv):
        for li,i in zip(poly.loop_indices,indices):uv.data[li].uv=uvs[i]
    arm=bpy.data.armatures.new('Sora_seated_authoring_rig');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for name,b in skel['bones'].items():bone=arm.edit_bones.new(name);bone.head=joint(b['head']);bone.tail=joint(b['tail'])
    for name,b in skel['bones'].items():
        if b['parent']:arm.edit_bones[name].parent=arm.edit_bones[b['parent']]
    bpy.ops.object.mode_set(mode='OBJECT')
    for name,weights in json.loads((src/'default_weights.mhw').read_text())['weights'].items():
        vg=body.vertex_groups.new(name=name)
        for i,weight in weights:
            if i in remap:vg.add([remap[i]],weight,'REPLACE')
    mod=body.modifiers.new('Seated female anatomy','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True
    def rotate(name,degrees):
        b=rig.pose.bones[name];q=b.bone.matrix_local.to_quaternion();b.rotation_mode='QUATERNION';b.rotation_quaternion=q.inverted()@Quaternion(Vector((1,0,0)),math.radians(degrees))@q
    for side in ['L','R']:
        rotate('upperleg01.'+side,-78);rotate('lowerleg01.'+side,55);rotate('foot.'+side,23)
    bpy.context.view_layer.update()
    baked=bpy.data.meshes.new_from_object(body.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    for v in baked.vertices:v.co=w((.39+v.co.x*.106,.55+(v.co.y-hip.y)*.106,-.36+(v.co.z-hip.z)*.106))
    baked.flip_normals();baked.update();body.modifiers.clear();body.data=baked
    skin=character_skin('M_taxi_sora_skin',src,'young_lightskinned_female_diffuse3.png')
    cotton=library_material('rough_linen','M_taxi_sora_travel_cotton',colour=(.055,.065,.085),tile=.10)
    leather=plain('M_taxi_sora_shoe_leather',(.025,.018,.014),.52)
    sole=plain('M_taxi_sora_shoe_sole',(.014,.012,.011),.86)
    welt=plain('M_taxi_sora_shoe_welt',(.07,.045,.025),.8)
    for mat in [skin,cotton,leather]:baked.materials.append(mat)
    for poly,f in zip(baked.polygons,faces):
        y=sum(verts[i].y for i in f)/len(f)
        poly.material_index=1 if y>-7.25 else 2 if y<-7.45 else 0;poly.use_smooth=True
    # Give the cotton trousers a little ease around the anatomical legs.
    # The small blouse/lap fold seals the cut waist without covering the legs.
    for k,v in enumerate(baked.vertices):
        if verts[ids[k]].y>-7.25:
            v.co+=v.normal*(.008+.002*math.sin(verts[ids[k]].y*13))
    baked.update()
    posed=[Vector((-v.co.x,v.co.z,-v.co.y)) for v in baked.vertices]
    vs=[];fs=[];rows=16;columns=20
    for j in range(rows+1):
        t=j/rows;z=-.50+t*.20
        row_top=max((v.y for v in posed if abs(v.z-z)<.04),default=.57)
        for i in range(columns+1):
            u=i/columns;x=.39+(u-.5)*.43
            y=row_top+.024-.028*(abs(u-.5)*2)**4+.004*math.sin(u*math.tau*4+t*1.7)
            if j==rows:y-=.012
            vs.append((x,y,z-.035*abs(u-.5)*2*t*t))
    for j in range(rows):
        for i in range(columns):a=j*(columns+1)+i;fs.append((a,a+columns+1,a+columns+2,a+1))
    skirt=mesh('taxi_sora_lap_fold',vs,fs,cotton);cotton.use_backface_culling=False
    hem=[vs[rows*(columns+1)+i] for i in range(columns+1)]
    tube('taxi_sora_blouse_hem',hem,.003,cotton)
    # Closed leather flats, fitted to the posed anatomical feet and resting on the mat.
    for side,sign in [('L',1),('R',-1)]:
        points=[Vector((-v.co.x,v.co.z,-v.co.y)) for k,v in enumerate(baked.vertices) if verts[ids[k]].y<-7.2 and verts[ids[k]].x*sign>0]
        cx=(min(v.x for v in points)+max(v.x for v in points))/2
        z0=min(v.z for v in points)-.01;z1=max(v.z for v in points)+.012
        width=(max(v.x for v in points)-min(v.x for v in points))*.54
        base=max(.080,min(v.y for v in points)-.005)
        shoevs=[];shoefs=[];sections=12;sides=16
        for k in range(sections+1):
            t=k/sections;zz=z0+(z1-z0)*t
            width_at=width*(.65+.35*math.sin(math.pi*t))*(.24 if k in [0,sections] else 1)
            height=.045+.045*math.exp(-((t-.35)/.24)**2)
            for i in range(sides+1):
                a=math.pi*i/sides;shoevs.append((cx+math.cos(a)*width_at,base+.015+math.sin(a)*height,zz))
        for k in range(sections):
            for i in range(sides):a=k*(sides+1)+i;shoefs.append((a,a+1,a+sides+2,a+sides+1))
        shoe=mesh('taxi_sora_shoe_'+side,shoevs,shoefs,leather);leather.use_backface_culling=False
        for p in shoe.data.polygons:p.use_smooth=True
        rounded('taxi_sora_shoe_sole_'+side,(cx,base+.006,(z0+z1)/2),(width*1.96,.02,z1-z0),sole,.028)
        tube('taxi_sora_shoe_welt_'+side,[shoevs[k*(sides+1)] for k in range(sections+1)]+[shoevs[k*(sides+1)+sides] for k in range(sections,-1,-1)],.002,welt)
    bpy.data.objects.remove(rig,do_unlink=True)
    print('SORA_LEGS_BOUNDS',min(v.co.z for v in baked.vertices),max(v.co.z for v in baked.vertices))

def driver(cloth,black):
    src=ROOT/'art-source/library/makehuman-sok'
    verts=[]; uvs=[]; faces=[]; faceuv=[]; group=''
    for line in (src/'base.obj').read_text().splitlines():
        a=line.split()
        if not a: continue
        if a[0]=='v': verts.append(Vector(map(float,a[1:4])))
        elif a[0]=='vt': uvs.append(tuple(map(float,a[1:3])))
        elif a[0]=='g': group=a[1]
        elif a[0]=='f' and group=='body':
            q=[t.split('/') for t in a[1:]]; faces.append([int(t[0])-1 for t in q]); faceuv.append([int(t[1])-1 for t in q])
    # Different from Sok: neutral open eyes, lighter age morph and no mortuary expression.
    for name,weight in [('asian-male-old.target',.28),('universal-male-old-averagemuscle-averageweight.target',.65)]:
        for line in (src/name).read_text().splitlines():
            if line and not line.startswith('#'):
                a=line.split(); verts[int(a[0])]+=Vector(map(float,a[1:4]))*weight
    rigdata=json.loads((src/'default.mhskel').read_text())
    def joint(n): return sum((verts[i] for i in rigdata['joints'][n]),Vector())/len(rigdata['joints'][n])
    arm=bpy.data.armatures.new('Taxi_driver_authoring_rig'); rig=bpy.data.objects.new('Taxi_driver_authoring_rig',arm); bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig; rig.select_set(True); bpy.ops.object.mode_set(mode='EDIT')
    for name,b in rigdata['bones'].items(): bone=arm.edit_bones.new(name); bone.head=joint(b['head']); bone.tail=joint(b['tail'])
    for name,b in rigdata['bones'].items():
        if b['parent']: arm.edit_bones[name].parent=arm.edit_bones[b['parent']]
    bpy.ops.object.mode_set(mode='OBJECT')
    used=sorted(set(i for f in faces for i in f)); remap={v:i for i,v in enumerate(used)}
    m=bpy.data.meshes.new('taxi_driver_anatomy'); m.from_pydata([verts[i] for i in used],[],[[remap[i] for i in f] for f in faces]); m.update()
    body=bpy.data.objects.new('taxi_driver_anatomy',m); bpy.context.collection.objects.link(body)
    layer=m.uv_layers.new(name='MakeHumanUV')
    for poly,indices in zip(m.polygons,faceuv):
        for li,i in zip(poly.loop_indices,indices): layer.data[li].uv=uvs[i]
    for name,weights in json.loads((src/'default_weights.mhw').read_text())['weights'].items():
        vg=body.vertex_groups.new(name=name)
        for i,weight in weights:
            if i in remap: vg.add([remap[i]],weight,'REPLACE')
    mod=body.modifiers.new('Seated anatomical driving pose','ARMATURE'); mod.object=rig; mod.use_deform_preserve_volume=True
    def rotate(name,axis,degrees):
        bone=rig.pose.bones.get(name)
        if bone is None: return
        r=bone.bone.matrix_local.to_quaternion(); bone.rotation_mode='QUATERNION'; bone.rotation_quaternion=bone.rotation_quaternion @ (r.inverted() @ Quaternion(Vector(axis),math.radians(degrees)) @ r)
    for side,sign in [('L',-1),('R',1)]:
        rotate('upperleg01.'+side,(1,0,0),-76); rotate('lowerleg01.'+side,(1,0,0),82)
        rotate('upperarm01.'+side,(0,0,1),sign*49); rotate('upperarm01.'+side,(1,0,0),-44)
        rotate('lowerarm01.'+side,(1,0,0),-49)
    # Four deform bones make up each arm; solve to wrists just behind the wheel rim.
    ik_targets=[]
    hip_ref=(joint(rigdata['bones']['upperleg01.L']['head'])+joint(rigdata['bones']['upperleg01.R']['head']))/2
    for side,hand_x in [('L',-.14),('R',-.64)]:
        target=bpy.data.objects.new('driver_grip_'+side,None); bpy.context.collection.objects.link(target)
        target.location=((hand_x+.39)/.1, hip_ref.y+(.94-.54)/.115, (.45-.035)/.1)
        bone=rig.pose.bones['lowerarm02.'+side]
        ik=bone.constraints.new('IK'); ik.target=target; ik.chain_count=4; ik.use_stretch=False
        ik_targets.append(target)
    bpy.context.view_layer.update()
    # Adduct each finger and oppose the thumb in the posed hand's own basis.
    # A shared world-axis curl leaves the source hand splayed beside the wheel.
    for side in ['L','R']:
        wrist_bone=rig.pose.bones['wrist.'+side]
        wrist=wrist_bone.head.copy()
        current=(rig.pose.bones['finger3-3.'+side].tail-wrist).normalized()
        across=rig.pose.bones['finger2-1.'+side].head-rig.pose.bones['finger5-1.'+side].head
        across=(across-current*across.dot(current)).normalized()
        target_up=Vector((0,1,.1)).normalized()
        target_across=Vector((-1 if side=='L' else 1,0,0))
        basis=Matrix((across,current,across.cross(current))).transposed()
        target_basis=Matrix((target_across,target_up,target_across.cross(target_up))).transposed()
        rotation=(target_basis @ basis.transposed()).to_quaternion() @ wrist_bone.matrix.to_quaternion()
        wrist_bone.matrix=Matrix.LocRotScale(wrist,rotation,wrist_bone.matrix.to_scale())
        bpy.context.view_layer.update()
        ay=(rig.pose.bones['finger3-3.'+side].tail-wrist).normalized()
        ax=rig.pose.bones['finger2-1.'+side].head-rig.pose.bones['finger5-1.'+side].head
        ax=(ax-ay*ax.dot(ay)).normalized()
        az=-ax.cross(ay).normalized() if side=='L' else ax.cross(ay).normalized()
        def point(digit,part,direction):
            b=rig.pose.bones[f'finger{digit}-{part}.{side}']
            target=(ax*direction[0]+ay*direction[1]+az*direction[2]).normalized()
            rotation=(b.tail-b.head).normalized().rotation_difference(target) @ b.matrix.to_quaternion()
            b.matrix=Matrix.LocRotScale(b.head,rotation,b.matrix.to_scale())
            bpy.context.view_layer.update()
        for digit,inward in [(2,-.12),(3,0),(4,.10),(5,.22)]:
            point(digit,1,(inward,.48,.86))
            point(digit,2,(0,-.55,.84))
            point(digit,3,(0,-.95,-.30))
        point(1,1,(.07,.78,.62)); point(1,2,(-.78,.55,.30)); point(1,3,(-.91,-.15,-.38))
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get()); baked=bpy.data.meshes.new_from_object(evaluated)
    # MakeHuman +Y up, +Z forward; hips anchored on the seat cushion.
    hip=(joint(rigdata['bones']['upperleg01.L']['head'])+joint(rigdata['bones']['upperleg01.R']['head']))/2
    for v in baked.vertices: v.co=w((-.39+v.co.x*.10,.54+(v.co.y-hip.y)*.115,.035+v.co.z*.10))
    baked.flip_normals(); baked.update()
    body.modifiers.clear(); body.data=baked
    skin=character_skin('M_taxi_driver_skin',src,'old_lightskinned_male_diffuse2.png')
    trousers=library_material('rough_linen','M_taxi_driver_trousers',colour=(.018,.025,.023),tile=.16)
    for mat in [skin,cloth,trousers,black]: baked.materials.append(mat)
    cuffs=[]
    for side in ['L','R']:
        rest=joint(rigdata['bones']['wrist.'+side]['head'])
        forearm=(rest-joint(rigdata['bones']['lowerarm02.'+side]['head'])).normalized()
        cuffs.append((rest,forearm))
    for poly,original in zip(baked.polygons,faces):
        c=sum((verts[i] for i in original),Vector())/len(original)
        hand=any((c-rest).dot(axis)>-.24 and abs(c.x)>3.5 for rest,axis in cuffs)
        poly.material_index=0 if c.y>5.8 or hand else 2 if c.y<.2 else 1
        poly.use_smooth=True
    # A rolled cloth collar covers the neckline boundary and reads as clothing
    # in the passenger's close profile view.
    collar_y=.54+(5.8-hip.y)*.115
    tube('taxi_driver_shirt_collar', [(-.39+.068*math.cos(a),collar_y,.047+.058*math.sin(a)) for a in [i*math.tau/40 for i in range(41)]],.010,cloth)
    # The source skin includes cropped scalp detail; keep its anatomical hairline.
    eye=plain('M_taxi_driver_eye',(.24,.22,.18),.42)
    iris=plain('M_taxi_driver_iris',(.025,.019,.012),.38)
    for side in ['L','R']:
        name='eye.'+side
        if name not in rigdata['bones']: continue
        at=joint(rigdata['bones'][name]['head'])
        at=Vector((-.39+at.x*.1,.54+(at.y-hip.y)*.115,.035+at.z*.1))
        ellipsoid('taxi_driver_eye_'+side,at,(.023,.022,.024),eye)
        ellipsoid('taxi_driver_iris_'+side,at+Vector((0,0,.011)),(.009,.010,.003),iris)
    # Tailored shirt details follow the posed body instead of hovering in front of it.
    def world(v): return Vector((-.39+v.x*.10,.54+(v.y-hip.y)*.115,.035+v.z*.10))
    def front(x,y):
        samples=[v for v in verts if abs(v.x-x)<.22 and abs(v.y-y)<.18]
        z=max((v.z for v in samples),default=.8)
        return world(Vector((x,y,z+.035)))
    stitch=plain('M_taxi_driver_thread',(.17,.15,.105),.95)
    buttonmat=plain('M_taxi_driver_buttons',(.055,.045,.028),.4)
    tube('taxi_driver_shirt_placket',[front(0,y) for y in [3.0,3.4,3.8,4.2,4.6,5.0,5.4]],.0035,cloth)
    for y in [3.3,3.8,4.3,4.8,5.3]:ellipsoid('taxi_driver_shirt_button',front(0,y)+Vector((0,0,.002)),(.008,.008,.004),buttonmat)
    for side in [-1,1]:
        mesh('taxi_driver_collar_leaf',[front(side*.12,5.75),front(side*.72,5.45),front(side*.28,5.1)],[(0,1,2)],cloth)
    pocket=[front(.6,4.1),front(1.35,4.1),front(1.35,4.8),front(.6,4.8)]
    quad('taxi_driver_chest_pocket',pocket,cloth)
    tube('taxi_driver_pocket_stitch',[v+Vector((0,0,.003)) for v in pocket+[pocket[0]]],.001,stitch)
    for side in ['L','R']:
        wrist=world(rig.pose.bones['wrist.'+side].head)
        elbow=world(rig.pose.bones['lowerarm02.'+side].head)
        axis=(wrist-elbow).normalized()
        across=axis.cross(Vector((0,1,0))).normalized();up=across.cross(axis).normalized()
        centre=wrist-axis*.018
        for offset in [-.012,.012]:
            tube('taxi_driver_rolled_cuff_'+side,[centre+axis*offset+across*math.cos(i/32*math.tau)*.029+up*math.sin(i/32*math.tau)*.024 for i in range(33)],.004,cloth)
        tube('taxi_driver_cuff_stitch_'+side,[centre+across*math.cos(i/32*math.tau)*.030+up*math.sin(i/32*math.tau)*.025 for i in range(33)],.001,stitch)
    # Worn cloth cap, sewn panels and a shallow bill give the silhouette a lived-in character.
    cap=library_material('waffle_pique_cotton','M_taxi_driver_cap',colour=(.045,.038,.025),tile=.12)
    ellipsoid('taxi_driver_cap_crown',(-.39,1.439,.080),(.220,.080,.214),cap)
    rounded('taxi_driver_cap_bill',(-.39,1.400,.157),(.204,.014,.132),cap,.025)
    tube('taxi_driver_cap_band',[(-.39+math.cos(i/48*math.tau)*.102,1.405,.080+math.sin(i/48*math.tau)*.096) for i in range(49)],.004,cap)
    for side in [-1,1]:
        tube('taxi_driver_cap_seam',[(-.39,1.479,.080),(-.39+side*.052,1.469,.085),(-.39+side*.092,1.441,.092),(-.39+side*.100,1.411,.103)],.0014,stitch)
    # Wristwatch on the passenger-facing arm, with an actual strap, bezel and hands.
    wrist=world(rig.pose.bones['wrist.L'].head);at=wrist+Vector((0,.029,-.012))
    leather=plain('M_taxi_driver_watch_strap',(.025,.016,.01),.7)
    tube('taxi_driver_watch_strap',[wrist+Vector((math.cos(i/32*math.tau)*.027,math.sin(i/32*math.tau)*.025,-.012)) for i in range(33)],.006,leather)
    nickel=plain('M_taxi_driver_watch_nickel',(.22,.23,.20),.29,.8)
    dial=plain('M_taxi_driver_watch_ivory',(.40,.36,.24),.62)
    ellipsoid('taxi_driver_watch_bezel',at,(.032,.008,.032),nickel)
    ellipsoid('taxi_driver_watch_face',at+Vector((0,.004,0)),(.027,.003,.027),dial)
    tube('taxi_driver_watch_hour',[at+Vector((0,.006,0)),at+Vector((-.006,.006,.004))],.0008,black)
    tube('taxi_driver_watch_minute',[at+Vector((0,.006,0)),at+Vector((.004,.006,.010))],.0006,black)
    for target in ik_targets: bpy.data.objects.remove(target,do_unlink=True)
    bpy.data.objects.remove(rig,do_unlink=True)
    print('TAXI_DRIVER_HIP',hip[:], 'bounds',min(v.co.z for v in baked.vertices),max(v.co.z for v in baked.vertices))

def road_x(z): return 3.8*math.sin(z*.018)+2.2*math.sin(z*.037)
def road_heading(z): return math.atan(3.8*.018*math.cos(z*.018)+2.2*.037*math.cos(z*.037))
def road_point(x,y,z):
    a=road_heading(z)
    return (road_x(z)+x*math.cos(a),y,z-x*math.sin(a))

def roadside():
    bpy.ops.wm.open_mainfile(filepath=str(ART/'ep1_area_village.blend'))
    original=bpy.context.scene
    templates={name:bpy.data.objects.get(name) for name in ['tree_0','tree_3','palm_0','coco_0','banana_1','bamboo_0','fern_02_a.001','shrub_02_a.001','forest_grass_-1_-1']}
    mats={m.name:m for m in bpy.data.materials}
    scene=bpy.data.scenes.new('Taxi_monsson_road'); bpy.context.window.scene=scene
    # Existing vegetation keeps its authored folded leaves, bark maps and root detail.
    rng=np.random.default_rng(2008)
    def plant(name,x,z,scale=1):
        src=templates[name]
        if not src: return
        bounds=[src.matrix_world @ Vector(c) for c in src.bound_box]
        foot=Vector(((min(p.x for p in bounds)+max(p.x for p in bounds))/2,(min(p.y for p in bounds)+max(p.y for p in bounds))/2,0))
        col=bpy.data.objects.get('col_'+name.removeprefix('far_'))
        if col: foot=col.matrix_world.translation.copy(); foot.z=0
        obj=src.copy(); obj.data=src.data; scene.collection.objects.link(obj); obj.parent=None
        obj.name='taxi_road_'+name
        obj.matrix_world=Matrix.Translation(w((x,-.12,z))) @ Matrix.Rotation(float(rng.random()*math.tau),4,'Z') @ Matrix.Scale(scale,4) @ Matrix.Translation(-foot) @ src.matrix_world
        obj.hide_render=False; obj.hide_set(False)
    far_templates=[]
    for name in ['tree_0','tree_3']:
        obj=templates[name].copy();obj.data=templates[name].data.copy();scene.collection.objects.link(obj)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        mod=obj.modifiers.new('Distant canopy LOD','DECIMATE');mod.ratio=.24
        bpy.ops.object.modifier_apply(modifier=mod.name)
        templates['far_'+name]=obj;far_templates.append(obj)
    # Independent, irregular groves with several species/ages. No opposing rows.
    # One 540 m route covers the complete journey and the visible horizon.
    for side in [-1,1]:
        z=-24+float(rng.random()*8)
        while z<510:
            kind=str(rng.choice(['tree_0','tree_3','palm_0','coco_0','bamboo_0'],p=[.32,.32,.08,.08,.20]))
            x=side*float(rng.uniform(4.3,10.5))
            at=road_point(x,-.12,z)
            plant(kind,at[0],at[2],float(rng.uniform(.6,1.18)))
            z+=float(rng.uniform(2.8,5.6))
        z=-24+float(rng.random()*7)
        while z<510:
            kind=str(rng.choice(['tree_0','tree_3','banana_1','bamboo_0'],p=[.35,.35,.12,.18]))
            x=side*float(rng.uniform(3.2,6.8))
            at=road_point(x,-.12,z)
            scale=float(rng.uniform(.32,.53) if kind.startswith('tree') else rng.uniform(.60,1.02))
            plant(kind,at[0],at[2],scale)
            z+=float(rng.uniform(2.8,5.1))
        # A second wall of lower-detail trees closes the view behind the near trunks.
        z=-24+float(rng.random()*5)
        while z<510:
            at=road_point(side*float(rng.uniform(9.5,19)),-.12,z)
            plant('far_tree_0' if rng.random()<.5 else 'far_tree_3',at[0],at[2],float(rng.uniform(.65,1.15)))
            z+=float(rng.uniform(3.2,5.6))
        for i in range(320):
            z=float(rng.uniform(-24,510)); x=side*float(rng.uniform(2.7,13))
            kind=str(rng.choice(['fern_02_a.001','shrub_02_a.001','forest_grass_-1_-1']))
            if kind.startswith('forest_grass'): x=side*float(rng.uniform(3,12))
            at=road_point(x,-.12,z)
            plant(kind,at[0],at[2],float(rng.uniform(.65,1.25)))
        # Low ferns soften the narrowed verge; trunks remain outside the driving corridor.
        z=-24+float(rng.random()*4)
        while z<510:
            at=road_point(side*float(rng.uniform(2.45,3.2)),-.12,z)
            plant('fern_02_a.001',at[0],at[2],float(rng.uniform(.4,.72)))
            z+=float(rng.uniform(3.5,7))
    # Sculpted continuous verge and a slightly crowned, deeply rutted muddy track.
    floor=mats['M_wet_forest_floor']; mud=mats['M_wet_mud']
    for name,mat,span,steps in [('taxi_road_ground',floor,26,26),('taxi_muddy_track',mud,2.2,16)]:
        vs=[]; fs=[]; rows=540
        for i in range(rows+1):
            z=-28+i
            for j in range(steps+1):
                x=-span+2*span*j/steps
                if span<4:
                    rut=math.exp(-((abs(x)-.72)/.2)**2)*.065
                    y=-.13+.055*(1-(x/span)**2)-rut+.008*math.sin(z*1.8+x*3)
                else: y=-.22+.028*math.sin(x*.7+z*.3)+.018*math.sin(z*.8+x*2)
                vs.append(road_point(x,y,z))
        for i in range(rows):
            for j in range(steps): a=i*(steps+1)+j; fs.append((a,a+steps+1,a+steps+2,a+1))
        mesh(name,vs,fs,mat)
    puddle=mats['M_puddle']
    for i in range(170):
        x=float(rng.choice([-1,1]))*.74+float(rng.normal(0,.22)); z=-24+float(rng.random()*532)
        vs=[road_point(x,-.111,z)]; count=20; radius=float(.25+rng.random()*.65); long=float(1+rng.random()*2)
        for j in range(count):
            a=j/count*math.tau; r=radius*(.85+.15*math.sin(j*2.7)); vs.append(road_point(x+math.cos(a)*r,-.111,z+math.sin(a)*r*long))
        mesh('taxi_rut_water',vs,[(0,(j+1)%count+1,j+1) for j in range(count)],puddle)
    # Occasional old markers, clustered near bends rather than a picket fence.
    post=mats.get('M_wet_old_planks',floor)
    for z,side in [(31,-1),(76,1),(131,-1),(181,-1),(252,1),(319,-1),(404,1),(449,1)]:
        rounded('taxi_road_marker',road_point(side*2.65,.10,z),(.10,.5,.12),post,.008)
    for obj in far_templates:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.scenes.remove(original)
    bpy.data.orphans_purge(do_recursive=True)
    export('ep1_taxi_roadside')

mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'all'
if mode in ['all','roadside']: roadside()
if mode in ['all','cabin']: cabin()
