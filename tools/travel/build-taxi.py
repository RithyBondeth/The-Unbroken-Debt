"""Author the taxi cabin and roadside from the episode's existing CC0 materials/plants.
blender -b --factory-startup -P tools/travel/build-taxi.py
World helpers use Babylon axes (x right, y up, z forward); export uses project glTF conversion.
"""
import bpy, math, sys, json, re, gzip
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
    # Threads and stitching read as lines: a coarser round keeps their vertex cost down.
    curve.bevel_depth=r; curve.bevel_resolution=2 if r>=.0025 else 1
    spline=curve.splines.new('POLY'); spline.points.add(len(points)-1)
    for p,co in zip(spline.points,points): p.co=(*w(co),1)
    o=bpy.data.objects.new(name,curve); bpy.context.collection.objects.link(o); curve.materials.append(mat)
    return o

def ellipsoid(name, at, size, mat, segments=None):
    # Screws, beads and buttons a few millimetres across need no 24-sided silhouette.
    segments=segments or (12 if max(size)<.03 else 24)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=segments//2, location=w(at))
    o=bpy.context.object; o.name=name; o.scale=(size[0]/2,size[2]/2,size[1]/2); o.data.materials.append(mat)
    for f in o.data.polygons: f.use_smooth=True
    plain_uvs(o); return o

def plain_uvs(o):
    # Primitives arrive with their own UV map; keep only the world projection, so
    # batched meshes sharing a material share one attribute layout.
    for layer in list(o.data.uv_layers): o.data.uv_layers.remove(layer)
    world_uvs(o)

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

# The steering wheel, shared by the cabin and the driver's grip.
WHEEL_CENTRE=(-.39,1.02,.47); WHEEL_FACING=(0,.3,-.95); WHEEL_RADIUS=.211

def cabin():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    vinyl=grain_material()
    felt=library_material('rough_linen','M_taxi_headliner',colour=(.075,.07,.055),tile=.12)
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
    wheelcentre=Vector(WHEEL_CENTRE); normal=Vector(WHEEL_FACING).normalized(); right=Vector((1,0,0)); up=normal.cross(right).normalized()
    tube('taxi_steering_rim',[wheelcentre+right*math.cos(k/64*math.tau)*WHEEL_RADIUS+up*math.sin(k/64*math.tau)*WHEEL_RADIUS for k in range(65)],.016,black)
    for a in [math.pi/2,math.pi*7/6,math.pi*11/6]: tube('taxi_steering_spoke',[wheelcentre,wheelcentre+(right*math.cos(a)+up*math.sin(a))*.196],.009,chrome)
    ellipsoid('taxi_steering_horn',wheelcentre,(.105,.105,.052),black)
    tube('taxi_steering_column',[(-.39,.72,1.03),wheelcentre],.027,black)
    # Instrument faces are painted at runtime and occupy recessed, circular bezels.
    for x,r in [(-.49,.075),(-.29,.047)]:
        tube('taxi_instrument_bezel',[(x+r*math.cos(k/64*math.tau),.975+r*math.sin(k/64*math.tau),.986) for k in range(65)],.0045,chrome)
    mirror_charms(chrome,black)
    taximeter(chrome,black,ink)
    mourners_leavings()
    cabin_detail(vinyl,felt,carpet,wood,rubber,chrome,black,thread,metal,glass)
    driver(black)
    passenger()
    export('ep1_taxi_cabin')

def pleated_cone(name,base,tip,r0,r1,mat,sides=16,rows=10):
    # A furled umbrella: a tapering canopy whose eight ribs pinch the oiled paper into folds.
    axis=(tip-base).normalized(); side=axis.cross(Vector((0,1,0))).normalized(); up=side.cross(axis)
    vs=[];fs=[]
    for i in range(rows+1):
        t=i/rows; c=base.lerp(tip,t); r=r0+(r1-r0)*t
        for j in range(sides):
            a=j/sides*math.tau; rr=r*(1+.18*math.cos(a*8))
            vs.append(tuple(c+side*math.cos(a)*rr+up*math.sin(a)*rr))
    for i in range(rows):
        for j in range(sides): a=i*sides+j; b=i*sides+(j+1)%sides; fs.append((a,b,b+sides,a+sides))
    o=mesh(name,vs,fs,mat)
    for poly in o.data.polygons: poly.use_smooth=True
    return o

def roof_y(x,z):
    # Underside of the curved headliner (its lining is solidified inward).
    return 1.77+.10*(1-(x/.88)**2)-.04*((z+.4)/1.4)**2-.04

def upholstery(x,z0,z1,y,width,mat,thread,rolls=6,depth=.07,name='taxi_seat_roll'):
    """Tuck-and-roll: plump channels side by side, stitched where they meet."""
    pitch=width/rolls
    for k in range(rolls):
        xx=x-width/2+pitch*(k+.5)
        rounded(name,(xx,y,(z0+z1)/2),(pitch*1.06,depth,abs(z1-z0)),mat,min(.03,pitch*.32))
        if k: tube(name+'_seam',[(xx-pitch/2,y+depth*.42,z0+.02),(xx-pitch/2,y+depth*.42,z1-.02)],.0022,thread)

def upright_upholstery(x,y0,y1,z,width,mat,thread,rolls=6,depth=.05,name='taxi_seatback_roll'):
    pitch=width/rolls
    for k in range(rolls):
        xx=x-width/2+pitch*(k+.5)
        rounded(name,(xx,(y0+y1)/2,z),(pitch*1.06,abs(y1-y0),depth),mat,min(.028,pitch*.3))
        if k: tube(name+'_seam',[(xx-pitch/2,y0+.02,z+depth*.42),(xx-pitch/2,y1-.02,z+depth*.42)],.0022,thread)

def cabin_detail(vinyl,felt,carpet,wood,rubber,chrome,black,thread,metal,glass):
    """What makes it a working 1930s taxi rather than a box: tuck-and-roll seats, real
    door cards, roof bows and a dome lamp, the vacuum wiper motor, a rear blind and
    robe rail, a dash clock, the ignition key, the passenger's grab bar, handbrake and
    gaiter, and the mud and leaves the night's fares tracked in."""
    leather=plain('M_taxi_leather',(.05,.03,.018),.42)
    brass=plain('M_taxi_brass',(.36,.25,.1),.34,.9)
    paper=plain('M_taxi_paper',(.42,.39,.31),.85)
    mud=plain('M_taxi_wet_mud',(.045,.03,.018),.25)
    leaf=plain('M_taxi_wet_leaf',(.06,.07,.025),.35); leaf.use_backface_culling=False
    lens=plain('M_taxi_frosted_lens',(.55,.52,.44),.5,alpha=.85)
    # Front seats: a sprung base, tuck-and-roll cushion and back, rolled front edge and top.
    for side in [-1,1]:
        x=side*.41
        rounded('taxi_seat_base',(x,.33,-.32),(.68,.11,.72),vinyl,.04)
        upholstery(x,-.64,.0,.445,.62,vinyl,thread)
        tube('taxi_seat_front_roll',[(x-.31,.43,.02),(x+.31,.43,.02)],.052,vinyl)
        rounded('taxi_seatback_shell',(x,.80,-.75),(.69,.74,.12),vinyl,.05)
        upright_upholstery(x,.5,1.1,-.672,.6,vinyl,thread)
        tube('taxi_seatback_top_roll',[(x-.32,1.14,-.7),(x+.32,1.14,-.7)],.05,vinyl)
        for xx in [x-.33,x+.33]: tube('taxi_seatback_bolster',[(xx,.48,-.69),(xx,1.12,-.7)],.035,vinyl)
        tube('taxi_seat_piping',[(x-.34,.40,-.66),(x-.34,.48,-.66),(x-.34,.48,.04),(x+.34,.48,.04),(x+.34,.48,-.66),(x+.34,.40,-.66)],.0045,thread)
        for xx in [x-.22,x+.22]: rounded('taxi_seat_rail',(xx,.22,-.32),(.04,.055,.65),chrome,.008)
        # A robe rail across the back of each front seat, for rear passengers' rugs.
        tube('taxi_robe_rail_cord',[(x-.28,.98,-.83),(x,.965,-.835),(x+.28,.98,-.83)],.008,leather)
        for xx in [x-.29,x+.29]: ellipsoid('taxi_robe_rail_bracket',(xx,.98,-.825),(.03,.03,.02),chrome)
    # Rear bench: deep buttoned back, rolled cushion and a fold-down centre armrest.
    rounded('taxi_rear_bench_base',(0,.36,-1.43),(1.56,.12,.56),vinyl,.04)
    upholstery(0,-1.68,-1.18,.465,1.48,vinyl,thread,rolls=12)
    tube('taxi_rear_front_roll',[(-.75,.44,-1.15),(.75,.44,-1.15)],.05,vinyl)
    rounded('taxi_rear_back_shell',(0,.89,-1.70),(1.56,.8,.14),vinyl,.05)
    rounded('taxi_rear_back_pad',(0,.89,-1.63),(1.46,.66,.06),vinyl,.03)
    for row,y in enumerate([.68,.82,.96,1.10]):
        for k in range(9 if row%2==0 else 8):
            xx=-.64+k*.16+(0 if row%2==0 else .08)
            ellipsoid('taxi_rear_tuft_button',(xx,y,-1.6),(.022,.022,.012),vinyl)
    rounded('taxi_rear_armrest',(0,.62,-1.5),(.16,.12,.36),vinyl,.04)
    # Door cards: walnut capping on the sill, a pleated panel, chrome strip, carpet kick panel.
    for side in [-1,1]:
        x=side*.86; inner=x-side*.047
        rounded(f'taxi_door_capping_{side}',(x-side*.03,.905,-.17),(.11,.028,2.1),wood,.01)
        tube(f'taxi_window_channel_{side}',[(inner,.925,-1.18),(inner,.925,.78)],.008,black)
        for z0,z1 in [(-.56,.7),(-1.24,-.7)]:
            n=int((z1-z0)/.075)
            for k in range(n):
                zz=z0+(k+.5)*(z1-z0)/n
                rounded(f'taxi_door_pleat_{side}',(inner-side*.006,.67,zz),(.014,.2,(z1-z0)/n*.92),vinyl,.006)
            tube(f'taxi_door_chrome_strip_{side}',[(inner-side*.012,.79,z0),(inner-side*.012,.79,z1)],.0042,chrome)
            tube(f'taxi_door_chrome_strip_{side}',[(inner-side*.012,.555,z0),(inner-side*.012,.555,z1)],.0042,chrome)
            rounded(f'taxi_door_kick_panel_{side}',(inner+side*.004,.24,(z0+z1)/2),(.016,.2,z1-z0-.04),carpet,.008)
        rounded(f'taxi_door_shut_line_{side}',(inner-side*.002,.6,-.645),(.006,.62,.012),black,.002)
        # Leather pull strap, lock knob, crank and handle escutcheons.
        tube(f'taxi_door_pull_strap_{side}',[(inner-side*.01,.83,.05),(inner-side*.03,.79,.12),(inner-side*.03,.79,.32),(inner-side*.01,.83,.4)],.01,leather)
        for z in [.05,.4]: ellipsoid('taxi_strap_stud',(inner-side*.012,.83,z),(.016,.016,.016),chrome)
        tube(f'taxi_door_lock_knob_{side}',[(x-side*.03,.91,-.5),(x-side*.03,.96,-.5)],.007,chrome)
        ellipsoid('taxi_door_lock_cap',(x-side*.03,.965,-.5),(.016,.012,.016),chrome)
        for z,y in [(.33,.69),(-1.0,.69)]:
            ellipsoid('taxi_crank_rosette',(inner-side*.012,y,z),(.012,.05,.05),chrome)
        ellipsoid('taxi_handle_escutcheon',(inner-side*.012,.849,.43),(.01,.045,.045),chrome)
        tube(f'taxi_rear_window_crank_{side}',[(x-side*.068,.71,-1.0),(x-side*.068,.655,-.95)],.009,chrome)
        ellipsoid('taxi_crank_grip',(x-side*.087,.652,-.94),(.033,.034,.035),black)
        rounded(f'taxi_rear_door_handle_{side}',(x-side*.059,.849,-.92),(.021,.023,.125),chrome,.01)
        # Leather assist straps on the rear pillars and a coat hook above each door.
        tube(f'taxi_assist_strap_{side}',[(side*.76,1.62,-1.36),(side*.73,1.42,-1.33),(side*.72,1.36,-1.3),(side*.73,1.42,-1.27),(side*.76,1.62,-1.24)],.011,leather)
        tube(f'taxi_coat_hook_{side}',[(side*.77,1.66,-.6),(side*.72,1.63,-.6),(side*.715,1.58,-.6),(side*.735,1.56,-.6)],.005,chrome)
    # Roof: lining bows, seams and a frosted dome lamp in a nickel bezel.
    for z in [.55,.05,-.45,-.95,-1.4]:
        tube('taxi_headliner_bow',[(x,roof_y(x,z)-.006,z) for x in [-.84+i*.12 for i in range(15)]],.011,felt)
    for x in [-.42,.42]:
        tube('taxi_headliner_seam',[(x,roof_y(x,z)-.004,z) for z in [.7-i*.2 for i in range(12)]],.0025,thread)
    ellipsoid('taxi_dome_lamp_lens',(0,roof_y(0,-.7)-.022,-.7),(.17,.04,.11),lens)
    tube('taxi_dome_lamp_bezel',[(math.cos(a)*.088,roof_y(0,-.7)-.012,-.7+math.sin(a)*.058) for a in [i/32*math.tau for i in range(33)]],.0055,chrome)
    rounded('taxi_dome_lamp_switch',(.13,roof_y(.13,-.7)-.012,-.7),(.03,.016,.02),black,.004)
    # The vacuum wiper motor on the header rail, its little control lever, and the rail itself.
    tube('taxi_windshield_header',[(-.72,1.735,.875),(0,1.75,.87),(.72,1.735,.875)],.026,metal)
    rounded('taxi_wiper_motor',(.21,1.705,.885),(.17,.065,.07),black,.012)
    tube('taxi_wiper_motor_lever',[(.3,1.7,.86),(.33,1.67,.85)],.004,chrome)
    tube('taxi_wiper_vacuum_hose',[(.13,1.7,.9),(.05,1.66,1.0),(-.02,1.3,1.17),(-.05,1.13,1.22)],.006,rubber)
    tube('taxi_windshield_sill_chrome',[(-.78,1.13,1.255),(0,1.145,1.265),(.78,1.13,1.255)],.006,chrome)
    # A roller blind drawn down over the small rear window, its tassel swinging.
    tube('taxi_rear_window_surround',[(-.31,1.12,-1.676),(-.31,1.46,-1.676),(.31,1.46,-1.676),(.31,1.12,-1.676),(-.31,1.12,-1.676)],.009,chrome)
    rounded('taxi_rear_blind',(0,1.29,-1.672),(.6,.31,.008),felt,.004)
    tube('taxi_rear_blind_roller',[(-.31,1.45,-1.668),(.31,1.45,-1.668)],.012,wood)
    tube('taxi_rear_blind_cord',[(0,1.135,-1.666),(0,1.06,-1.664)],.0018,thread)
    ellipsoid('taxi_rear_blind_tassel',(0,1.045,-1.663),(.016,.03,.016),leather)
    # Dashboard: an eight-day clock in the glovebox lid, ignition key, grab bar and ashtray.
    clock_face=plain('M_taxi_clock_face',(.42,.39,.3),.55)
    ellipsoid('taxi_dash_clock_face',(.30,.94,.97),(.095,.095,.008),clock_face)
    tube('taxi_dash_clock_bezel',[(.30+math.cos(a)*.05,.94+math.sin(a)*.05,.968) for a in [i/40*math.tau for i in range(41)]],.0055,chrome)
    for k in range(12):
        a=k/12*math.tau; tube('taxi_dash_clock_tick',[(.30+math.cos(a)*.04,.94+math.sin(a)*.04,.962),(.30+math.cos(a)*.045,.94+math.sin(a)*.045,.962)],.0012,black)
    tube('taxi_dash_clock_hour',[(.30,.94,.961),(.285,.955,.961)],.0018,black)
    tube('taxi_dash_clock_minute',[(.30,.94,.961),(.322,.97,.961)],.0013,black)
    ellipsoid('taxi_ignition_escutcheon',(.2,.83,1.0),(.04,.04,.01),chrome)
    rounded('taxi_ignition_key',(.2,.83,.978),(.012,.03,.03),brass,.004)
    tube('taxi_ignition_keyring',[(.2+math.sin(a)*.016,.795-.016+math.cos(a)*.016,.972) for a in [i/20*math.tau for i in range(21)]],.0018,chrome)
    rounded('taxi_ignition_fob',(.205,.755,.972),(.022,.03,.006),leather,.006)
    tube('taxi_passenger_grab_bar',[(.26,.86,.95),(.27,.84,.93),(.68,.84,.93),(.69,.86,.95)],.011,chrome)
    rounded('taxi_dash_ashtray',(-.02,.87,.968),(.12,.035,.03),chrome,.006)
    for k,dx in enumerate([-.03,.02]):
        tube('taxi_ashtray_butt',[(dx-.02,.892,.962),(dx+.02,.894,.955)],.004,paper)
    # Floor: handbrake, gear-lever gaiter, an oiled-paper umbrella, mud and wet leaves.
    tube('taxi_handbrake_lever',[(-.1,.12,.24),(-.11,.38,.16),(-.12,.52,.08)],.011,chrome)
    rounded('taxi_handbrake_grip',(-.12,.54,.07),(.03,.08,.03),black,.012)
    rounded('taxi_handbrake_ratchet',(-.1,.16,.24),(.02,.08,.12),metal,.006)
    ellipsoid('taxi_gear_gaiter',(.02,.34,.365),(.11,.09,.11),leather)
    umbrella=plain('M_taxi_oiled_umbrella',(.22,.08,.04),.32)
    pleated_cone('taxi_umbrella_canopy',Vector((.66,.09,-.04)),Vector((.7,.42,.48)),.034,.006,umbrella)
    tube('taxi_umbrella_tie',[(.668+math.cos(a)*.024,.2+math.sin(a)*.024*.4,.12+math.sin(a)*.024) for a in [i/12*math.tau for i in range(13)]],.003,leather)
    tube('taxi_umbrella_handle',[(.65,.06,-.1),(.66,.1,-.03)],.009,wood)
    tube('taxi_umbrella_tip',[(.7,.42,.48),(.705,.47,.55)],.004,metal)
    rng=np.random.default_rng(1931)
    for k in range(9):
        x=.39+float(rng.normal(0,.14)); z=.35+float(rng.normal(0,.22))
        ellipsoid('taxi_tracked_mud',(x,.083,z),(float(rng.uniform(.04,.1)),.006,float(rng.uniform(.03,.09))),mud)
    for k in range(7):
        x=.35+float(rng.normal(0,.18)); z=.4+float(rng.normal(0,.25)); a=float(rng.uniform(0,math.tau)); L=float(rng.uniform(.04,.07))
        mesh('taxi_tracked_leaf',[(x,.087,z),(x+math.cos(a+.4)*L*.4,.088,z+math.sin(a+.4)*L*.4),(x+math.cos(a)*L,.087,z+math.sin(a)*L),(x+math.cos(a-.4)*L*.4,.088,z+math.sin(a-.4)*L*.4)],[(0,1,2,3)],leaf)
    # A dog-eared fare card tucked behind the windshield sill.
    quad('taxi_fare_card',[(.5,1.13,1.235),(.62,1.13,1.235),(.625,1.2,1.25),(.505,1.205,1.25)],paper)
    paper.use_backface_culling=False

def painted_material(name,array,rough=.8):
    """A small authored colour map (numpy RGB 0-1) saved beside the vinyl maps."""
    h,width=array.shape[:2]
    img=bpy.data.images.new('T_'+name.removeprefix('M_'),width=width,height=h,alpha=True)
    img.pixels.foreach_set(np.concatenate([array,np.ones((h,width,1))],axis=-1).astype(np.float32).ravel())
    img.filepath_raw=str(TEX/('T_'+name.removeprefix('M_')+'_BC.png')); img.file_format='PNG'; img.save()
    mat=plain(name,(1,1,1),rough)
    t=mat.node_tree.nodes.new('ShaderNodeTexImage'); t.image=img
    mat.node_tree.links.new(t.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    return mat

def yantra_material():
    # A protective cloth diagram for the mirror: ruled squares, rings and diagonals in
    # faded red-brown ink, no script (advisor review).
    n=128; yy,xx=(np.mgrid[:n,:n]-63.5)/63.5
    ink=np.zeros((n,n))
    for r in [.92,.62,.3]: ink=np.maximum(ink,np.exp(-((np.maximum(abs(xx),abs(yy))-r)/.025)**2))
    ink=np.maximum(ink,np.exp(-((np.hypot(xx,yy)-.47)/.025)**2))
    ink=np.maximum(ink,np.exp(-((abs(xx)-abs(yy))/.03)**2)*(np.maximum(abs(xx),abs(yy))<.62))
    ink=np.maximum(ink,np.exp(-(xx/.025)**2)*(abs(yy)<.3)+np.exp(-(yy/.025)**2)*(abs(xx)<.3))
    cloth=np.array([.66,.6,.47]); stain=np.random.default_rng(7).normal(0,.03,(n,n,1))
    colour=cloth*(1-.8*ink[...,None])+np.array([.3,.08,.04])*.8*ink[...,None]+stain
    return painted_material('M_taxi_yantra_cloth',np.clip(colour,0,1),.9)

def mirror_charms(chrome,black):
    """Protection hung from the mirror: a jasmine garland with a red tassel, prayer beads
    and a folded yantra cloth on one cord. Parented to a pivot the runtime swings."""
    pivot=bpy.data.objects.new('taxi_mirror_charm_pivot',None); bpy.context.collection.objects.link(pivot)
    pivot.location=w((.06,1.585,.742))
    cord=plain('M_taxi_charm_cord',(.32,.29,.22),.9)
    jasmine=plain('M_taxi_jasmine',(.55,.53,.44),.65)
    rose=plain('M_taxi_charm_red',(.3,.03,.03),.7)
    wood=plain('M_taxi_prayer_beads',(.09,.05,.025),.45)
    parts=[]
    top=(.06,1.585,.742)
    parts.append(tube('taxi_charm_cord',[top,(.058,1.52,.744),(.055,1.45,.745)],.0018,cord))
    for i in range(22):
        a=i/22*math.tau
        parts.append(ellipsoid('taxi_charm_jasmine',(.055+math.cos(a)*.032,1.43+math.sin(a)*.012,.745+math.sin(a)*.03),(.012,.016,.012),jasmine,8))
    parts.append(ellipsoid('taxi_charm_rose',(.055,1.405,.745),(.022,.022,.022),rose,10))
    parts.append(tube('taxi_charm_tassel',[(.055,1.395,.745),(.057,1.345,.746)],.006,rose))
    for i in range(27):
        a=i/27*math.tau
        parts.append(ellipsoid('taxi_charm_bead',(.075+math.sin(a)*.018,1.52-(1-math.cos(a))*.05,.742),(.008,.008,.008),wood,8))
    yantra=yantra_material()
    parts.append(quad('taxi_charm_yantra',[(.025,1.47,.75),(.065,1.47,.75),(.065,1.51,.75),(.025,1.51,.75)],yantra))
    yantra.use_backface_culling=False
    bpy.context.view_layer.update()
    for part in parts:
        world=part.matrix_world.copy(); part.parent=pivot; part.matrix_world=world

def taximeter(chrome,black,ink):
    # A mechanical taximeter on the dash top, its flag raised: the fare is still running.
    rounded('taxi_meter_case',(.27,1.17,1.13),(.15,.11,.09),black,.012)
    rounded('taxi_meter_window',(.27,1.185,1.083),(.09,.035,.004),chrome,.003)
    rounded('taxi_meter_tariff_plate',(.27,1.145,1.083),(.06,.016,.003),ink,.002)
    tube('taxi_meter_flag_arm',[(.35,1.17,1.13),(.36,1.29,1.13)],.006,chrome)
    rounded('taxi_meter_flag',(.395,1.27,1.13),(.07,.04,.006),plain('M_taxi_meter_flag_red',(.32,.04,.03),.6),.004)
    tube('taxi_meter_crank',[(.35,1.14,1.1),(.38,1.12,1.09)],.005,chrome)

def mourners_leavings():
    """What the morning's mourners left on the rear bench: a white lotus bud, a loose
    coil of blessing thread and a bundle of unlit incense on the floor."""
    petal=plain('M_taxi_lotus',(.62,.6,.53),.6); stem=plain('M_taxi_lotus_stem',(.07,.11,.05),.7)
    ellipsoid('taxi_rear_lotus_bud',(.32,.565,-1.32),(.05,.05,.11),petal)
    tube('taxi_rear_lotus_stem',[(.32,.55,-1.27),(.3,.545,-1.12),(.24,.54,-1.02)],.006,stem)
    thread=plain('M_taxi_blessing_thread',(.62,.6,.55),.9)
    tube('taxi_rear_thread_coil',[(-.22+math.cos(a)*(.05+.004*a),.535+.002*math.sin(a*3),-1.36+math.sin(a)*(.05+.004*a)) for a in [i/6 for i in range(60)]],.0016,thread)
    incense=plain('M_taxi_incense_sticks',(.32,.12,.06),.8)
    for i in range(14):
        dx=(i%5)*.006-.012; dy=(i//5)*.006
        tube('taxi_rear_incense',[(.1+dx,.075+dy,-1.0),(.12+dx,.08+dy,-.72)],.0022,incense)
    tube('taxi_rear_incense_band',[(.096+math.cos(a)*.02,.081+math.sin(a)*.016,-.86) for a in [i/16*math.tau for i in range(17)]],.002,plain('M_taxi_incense_paper',(.45,.05,.04),.7))

def character_skin(name,src,photo,relief=1024):
    mat=plain(name,(.30,.20,.13),.7)
    image=bpy.data.images.load(str(src/photo),check_existing=True)
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=image
    links=mat.node_tree.links; bs=mat.node_tree.nodes['Principled BSDF']; links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    # Photo-derived fine relief breaks the plastic highlight without inventing scars.
    pixels=np.array(image.pixels[:],dtype=np.float32).reshape(image.size[1],image.size[0],4)
    stride=max(1,image.size[0]//relief); rgb=pixels[::stride,::stride,:3]
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
    # Trousers and shoes cover almost all of it: a coarse relief is enough.
    skin=character_skin('M_taxi_sora_skin',src,'young_lightskinned_female_diffuse3.png',256)
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

DRIVER_SRC=ROOT/'art-source/library/makehuman-driver'

def read_mhclo(path):
    """A MakeHuman proxy: each vertex rides three base vertices plus an offset scaled to the body."""
    refs=[]; scales={}; deleted=set(); section=None
    for line in path.read_text().splitlines():
        a=line.split()
        if not a or a[0].startswith('#'): continue
        if a[0] in ('x_scale','y_scale','z_scale'): scales[a[0][0]]=(int(a[1]),int(a[2]),float(a[3])); continue
        if a[0]=='verts': section='verts'; continue
        if a[0]=='delete_verts': section='delete'; continue
        if section=='verts':
            try: numbers=[float(t) for t in a]
            except ValueError: continue
            if len(numbers)==1: refs.append(((int(numbers[0]),0,0),(1.,0.,0.),(0.,0.,0.)))
            elif len(numbers)>=9: refs.append((tuple(int(n) for n in numbers[:3]),tuple(numbers[3:6]),tuple(numbers[6:9])))
        elif section=='delete':
            k=0
            while k<len(a):
                if k+2<len(a) and a[k+1]=='-': deleted.update(range(int(a[k]),int(a[k+2])+1)); k+=3
                else: deleted.add(int(a[k])); k+=1
    return refs,scales,deleted

def fit_proxy(refs,scales,verts):
    s=[abs(verts[scales[axis][0]][j]-verts[scales[axis][1]][j])/scales[axis][2] for j,axis in enumerate('xyz')]
    return [verts[i]*a+verts[j]*b+verts[k]*c+Vector((d[0]*s[0],d[1]*s[1],d[2]*s[2])) for (i,j,k),(a,b,c),d in refs]

def read_obj(path):
    uvs=[]; faces=[]; faceuv=[]
    for line in path.read_text().splitlines():
        a=line.split()
        if not a: continue
        if a[0]=='vt': uvs.append(tuple(map(float,a[1:3])))
        elif a[0]=='f':
            q=[t.split('/') for t in a[1:]]; faces.append([int(t[0])-1 for t in q])
            faceuv.append([int(t[1])-1 if len(t)>1 and t[1] else 0 for t in q])
    return uvs,faces,faceuv

def proxy_object(name,coords,obj_path,refs,bone_weights,rig):
    """The fitted proxy, weighted from the base vertices it rides, posed by the driver's rig."""
    uvs,faces,faceuv=read_obj(obj_path)
    m=bpy.data.meshes.new(name); m.from_pydata(coords,[],faces); m.update()
    o=bpy.data.objects.new(name,m); bpy.context.collection.objects.link(o)
    layer=m.uv_layers.new(name='UVMap')
    for poly,indices in zip(m.polygons,faceuv):
        poly.use_smooth=True
        for li,i in zip(poly.loop_indices,indices): layer.data[li].uv=uvs[i]
    groups={}
    for v,((i,j,k),(a,b,c),_) in enumerate(refs):
        for ref,share in ((i,a),(j,b),(k,c)):
            if share<=0: continue
            for bone,weight in bone_weights.get(ref,{}).items():
                g=groups.get(bone) or groups.setdefault(bone,o.vertex_groups.new(name=bone))
                g.add([v],weight*share,'ADD')
    mod=o.modifiers.new('Seated anatomical driving pose','ARMATURE'); mod.object=rig; mod.use_deform_preserve_volume=True
    return o

def proxy_material(name,image_name,rough=.6,clip=False,tint=None,normal=None):
    mat=plain(name,(1,1,1),rough); nodes=mat.node_tree.nodes; links=mat.node_tree.links; bs=nodes['Principled BSDF']
    tex=nodes.new('ShaderNodeTexImage'); tex.image=bpy.data.images.load(str(DRIVER_SRC/image_name),check_existing=True)
    colour=tex.outputs['Color']
    if tint:
        mix=nodes.new('ShaderNodeMix'); mix.data_type='RGBA'; mix.blend_type='MULTIPLY'; mix.inputs['Factor'].default_value=1
        links.new(colour,mix.inputs['A']); mix.inputs['B'].default_value=(*tint,1); colour=mix.outputs['Result']
    links.new(colour,bs.inputs['Base Color'])
    if clip:
        cut=nodes.new('ShaderNodeMath'); cut.operation='GREATER_THAN'; cut.inputs[1].default_value=.22
        links.new(tex.outputs['Alpha'],cut.inputs[0]); links.new(cut.outputs[0],bs.inputs['Alpha'])
        mat.use_backface_culling=False
    if normal:
        n=nodes.new('ShaderNodeTexImage'); n.image=bpy.data.images.load(str(DRIVER_SRC/normal),check_existing=True)
        n.image.colorspace_settings.name='Non-Color'
        nm=nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value=.8
        links.new(n.outputs['Color'],nm.inputs['Color']); links.new(nm.outputs['Normal'],bs.inputs['Normal'])
    return mat

def faded_cotton(name,tint):
    """The suit's denim map washed to grey so its weave, seams and folds carry a period cotton."""
    image=bpy.data.images.load(str(DRIVER_SRC/'male_casualsuit01_diffuse.png'),check_existing=True)
    if image.size[0]>1024: image.scale(1024,1024)
    px=np.array(image.pixels[:],dtype=np.float32).reshape(image.size[1],image.size[0],4)
    grey=px[...,:3]@np.array([.2126,.7152,.0722]); grey=grey/max(grey.mean(),1e-4)*.5
    rgb=np.clip(grey[...,None]*np.array(tint)*2,0,1)
    out=bpy.data.images.new('T_'+name.removeprefix('M_'),width=image.size[0],height=image.size[1],alpha=True)
    out.pixels.foreach_set(np.concatenate([rgb,np.ones(grey.shape+(1,))],axis=-1).astype(np.float32).ravel())
    out.filepath_raw=str(TEX/('T_'+name.removeprefix('M_')+'_BC.png')); out.file_format='PNG'; out.save()
    mat=plain(name,(1,1,1),.88); nodes=mat.node_tree.nodes; bs=nodes['Principled BSDF']
    t=nodes.new('ShaderNodeTexImage'); t.image=out; mat.node_tree.links.new(t.outputs['Color'],bs.inputs['Base Color'])
    n=nodes.new('ShaderNodeTexImage'); n.image=bpy.data.images.load(str(DRIVER_SRC/'male_casualsuit01_normal.png'),check_existing=True)
    n.image.colorspace_settings.name='Non-Color'
    nm=nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value=1.0
    mat.node_tree.links.new(n.outputs['Color'],nm.inputs['Color']); mat.node_tree.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
    return mat

def driver(black):
    """A real middle-aged Khmer driver from MakeHuman's CC0 body and fitted proxies:
    textured brown eyes, eyelashes, brows, short combed hair, a cotton shirt and
    trousers. One baked 'blink' shape lets the runtime close his eyes."""
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
    # Different from Sok: neutral open eyes, a weathered middle-aged man, no mortuary expression.
    for name,weight in [('asian-male-old.target',.55),('universal-male-old-averagemuscle-averageweight.target',.8)]:
        for line in (src/name).read_text().splitlines():
            if line and not line.startswith('#'):
                a=line.split(); verts[int(a[0])]+=Vector(map(float,a[1:4]))*weight
    suit=read_mhclo(DRIVER_SRC/'male_casualsuit01.mhclo')
    # Skin the shirt and trousers cover is left out, so nothing pokes through the cloth.
    kept=[(f,uv) for f,uv in zip(faces,faceuv) if not any(i in suit[2] for i in f)]
    faces=[f for f,_ in kept]; faceuv=[uv for _,uv in kept]
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
    bone_weights={}
    for name,weights in json.loads((src/'default_weights.mhw').read_text())['weights'].items():
        vg=body.vertex_groups.new(name=name)
        for i,weight in weights:
            bone_weights.setdefault(i,{})[name]=weight
            if i in remap: vg.add([remap[i]],weight,'REPLACE')
    mod=body.modifiers.new('Seated anatomical driving pose','ARMATURE'); mod.object=rig; mod.use_deform_preserve_volume=True
    proxies={}
    for name,stem in [('hair','short02'),('brows','eyebrow002'),('lashes','eyelashes01'),('eyes','high-poly'),('suit','male_casualsuit01')]:
        refs,scales,_=suit if stem=='male_casualsuit01' else read_mhclo(DRIVER_SRC/(stem+'.mhclo'))
        coords=fit_proxy(refs,scales,verts)
        proxies[name]=(proxy_object('taxi_driver_'+name,coords,DRIVER_SRC/(stem+'.obj'),refs,bone_weights,rig),refs,scales)
    def rotate(name,axis,degrees):
        bone=rig.pose.bones.get(name)
        if bone is None: return
        r=bone.bone.matrix_local.to_quaternion(); bone.rotation_mode='QUATERNION'; bone.rotation_quaternion=bone.rotation_quaternion @ (r.inverted() @ Quaternion(Vector(axis),math.radians(degrees)) @ r)
    for side,sign in [('L',-1),('R',1)]:
        rotate('upperleg01.'+side,(1,0,0),-76); rotate('lowerleg01.'+side,(1,0,0),82)
        rotate('upperarm01.'+side,(0,0,1),sign*49); rotate('upperarm01.'+side,(1,0,0),-44)
        rotate('lowerarm01.'+side,(1,0,0),-49)
    # His head turned past Sora toward the trees on her side, his eyes further still;
    # shoulders a little hunched over the wheel.
    def eye_mid():
        bpy.context.view_layer.update()
        return (rig.pose.bones['eye.L'].head+rig.pose.bones['eye.R'].head)/2
    before=eye_mid(); turn=1
    rotate('neck02',(0,1,0),14); rotate('head',(0,1,0),20)
    if eye_mid().x<before.x:
        turn=-1; rotate('neck02',(0,1,0),-28); rotate('head',(0,1,0),-40)
    rotate('head',(1,0,0),3); rotate('spine01',(1,0,0),5)
    for side in ['L','R']: rotate('eye.'+side,(0,1,0),turn*14)
    # Hands on the rim at nine and three, halfway down the wheel: each palm sits just outside the rim, fingers
    # pointing forward through the wheel and curled back around it, thumb inside.
    hip_ref=(joint(rigdata['bones']['upperleg01.L']['head'])+joint(rigdata['bones']['upperleg01.R']['head']))/2
    def to_mh(p): return Vector(((p[0]+.39)/.1, hip_ref.y+(p[1]-.54)/.115, (p[2]-.035)/.1))
    def dir_mh(d): return Vector((d[0]/.1,d[1]/.115,d[2]/.1)).normalized()
    centre=Vector(WHEEL_CENTRE); facing=Vector(WHEEL_FACING).normalized(); right=Vector((1,0,0)); upward=right.cross(facing).normalized()
    if upward.y<0: upward=-upward
    grips={}
    for side,angle in [('L',math.radians(2)),('R',math.radians(178))]:
        radial=right*math.cos(angle)+upward*math.sin(angle)
        tangent=-right*math.sin(angle)+upward*math.cos(angle)
        grips[side]=dict(point=centre+radial*WHEEL_RADIUS,radial=radial,tangent=tangent)
    ik_targets=[]
    for side in ['L','R']:
        target=bpy.data.objects.new('driver_grip_'+side,None); bpy.context.collection.objects.link(target)
        g=grips[side]; target.location=to_mh(g['point']+g['radial']*.045-(-facing)*.07)
        bone=rig.pose.bones['lowerarm02.'+side]
        ik=bone.constraints.new('IK'); ik.target=target; ik.chain_count=4; ik.use_stretch=False
        ik_targets.append(target); g['target']=target
    def pose_hand(side):
        g=grips[side]
        az=dir_mh(-g['radial']); ay=dir_mh(-facing); ay=(ay-az*ay.dot(az)).normalized()
        ax=ay.cross(az) if side=='R' else az.cross(ay)
        wrist_bone=rig.pose.bones['wrist.'+side]
        bpy.context.view_layer.update()
        wrist=wrist_bone.head.copy()
        current=(rig.pose.bones['finger3-3.'+side].tail-wrist).normalized()
        across=rig.pose.bones['finger2-1.'+side].head-rig.pose.bones['finger5-1.'+side].head
        across=(across-current*across.dot(current)).normalized()
        basis=Matrix((across,current,across.cross(current))).transposed()
        target_basis=Matrix((ax,ay,ax.cross(ay))).transposed()
        rotation=(target_basis @ basis.transposed()).to_quaternion() @ wrist_bone.matrix.to_quaternion()
        wrist_bone.matrix=Matrix.LocRotScale(wrist,rotation,wrist_bone.matrix.to_scale())
        bpy.context.view_layer.update()
        def point(digit,part,direction):
            b=rig.pose.bones[f'finger{digit}-{part}.{side}']
            target=(ax*direction[0]+ay*direction[1]+az*direction[2]).normalized()
            rotation=(b.tail-b.head).normalized().rotation_difference(target) @ b.matrix.to_quaternion()
            b.matrix=Matrix.LocRotScale(b.head,rotation,b.matrix.to_scale())
            bpy.context.view_layer.update()
        for digit,inward in [(2,-.1),(3,0),(4,.08),(5,.18)]:
            point(digit,1,(inward,.82,.57))
            point(digit,2,(0,.05,1))
            point(digit,3,(0,-.75,.66))
        # The thumb lies on the rim: up along its inner edge, then curled over its front.
        upward_rim=g['tangent'] if g['tangent'].y>0 else -g['tangent']
        for part,(up_,fwd,inward) in enumerate([(.55,.25,.55),(.35,.7,.3),(.15,.75,-.35)],1):
            aim=dir_mh(upward_rim*up_+(-facing)*fwd+(-g['radial'])*inward)
            b=rig.pose.bones[f'finger1-{part}.{side}']
            rotation=(b.tail-b.head).normalized().rotation_difference(aim) @ b.matrix.to_quaternion()
            b.matrix=Matrix.LocRotScale(b.head,rotation,b.matrix.to_scale())
            bpy.context.view_layer.update()
        g['basis']=(ax,ay,az)
        return point
    # Settle each hand so the hollow of its curled fingers closes on the rim itself.
    for _ in range(5):
        for side in ['L','R']:
            pose_hand(side)
            hollow=Vector()
            for digit in [3,4]:
                for part in [1,2,3]: hollow+=rig.pose.bones[f'finger{digit}-{part}.{side}'].head
                hollow+=rig.pose.bones[f'finger{digit}-3.{side}'].tail
            hollow/=8
            grips[side]['target'].location+=to_mh(grips[side]['point'])-hollow
        bpy.context.view_layer.update()
    for side in ['L','R']: grips[side]['point_fn']=pose_hand(side)
    # MakeHuman +Y up, +Z forward; hips anchored on the seat cushion.
    hip=(joint(rigdata['bones']['upperleg01.L']['head'])+joint(rigdata['bones']['upperleg01.R']['head']))/2
    def place(co): return w((-.39+co.x*.10,.54+(co.y-hip.y)*.115,.035+co.z*.10))
    def posed(obj):
        bpy.context.view_layer.update()
        ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        return [place(v.co) for v in ev.data.vertices]
    driven=[body]+[proxies[n][0] for n in ['hair','brows','lashes','eyes','suit']]
    shapes={o.name:{} for o in driven}
    def capture(name,objects=driven):
        for o in objects: shapes[o.name][name]=posed(o)
    def rest_shape(name,target,objects):
        # A face shape (lids, jaw) evaluated on the posed body, then the rest restored.
        moved=[v.copy() for v in verts]
        for line in target:
            if line and not line.startswith('#'):
                a=line.split(); moved[int(a[0])]+=Vector(map(float,a[1:4]))
        for k,i in enumerate(used): body.data.vertices[k].co=moved[i]
        lashes=proxies['lashes']
        if lashes[0] in objects:
            for k,co in enumerate(fit_proxy(lashes[1],lashes[2],moved)): lashes[0].data.vertices[k].co=co
        body.data.update(); lashes[0].data.update()
        capture(name,objects)
        for k,i in enumerate(used): body.data.vertices[k].co=verts[i]
        for k,co in enumerate(fit_proxy(lashes[1],lashes[2],verts)): lashes[0].data.vertices[k].co=co
        body.data.update(); lashes[0].data.update(); bpy.context.view_layer.update()
    def read_target(*names):
        lines=[]
        for n in names: lines+=gzip.decompress((src/n).read_bytes()).decode().splitlines()
        return lines
    rest_shape('blink',read_target('eye-left-closure.target.gz','eye-right-closure.target.gz'),[body,proxies['lashes'][0]])
    rest_shape('talk',read_target('mouth-open.target.gz'),[body])
    def pose_shape(name,turns,objects=driven,fingers=None):
        saved={b.name:b.matrix_basis.copy() for b in rig.pose.bones}
        for bone,axis,degrees in turns: rotate(bone,axis,degrees)
        if fingers: fingers()
        capture(name,objects)
        for b in rig.pose.bones: b.matrix_basis=saved[b.name]
        bpy.context.view_layer.update()
    # Glances: back to the road, round to Sora, a small nod, and a re-grip of his fingers.
    pose_shape('look_road',[('neck02',(0,1,0),-turn*13),('head',(0,1,0),-turn*19),('eye.L',(0,1,0),-turn*14),('eye.R',(0,1,0),-turn*14)])
    pose_shape('look_sora',[('neck02',(0,1,0),turn*9),('head',(0,1,0),turn*15),('head',(1,0,0),7),('eye.L',(0,1,0),turn*12),('eye.R',(0,1,0),turn*12)])
    pose_shape('nod',[('head',(1,0,0),8),('neck02',(1,0,0),3)])
    def tap():
        point=grips['L']['point_fn']
        for digit,inward in [(2,-.1),(3,0)]:
            point(digit,1,(inward,.97,.2)); point(digit,2,(0,.8,.6)); point(digit,3,(0,.45,.9))
    pose_shape('grip',[],[body],tap)
    def bake(obj):
        ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); baked=bpy.data.meshes.new_from_object(ev)
        for v in baked.vertices: v.co=place(v.co)
        baked.flip_normals(); baked.update()
        obj.modifiers.clear(); obj.vertex_groups.clear(); obj.data=baked
        if shapes.get(obj.name):
            obj.shape_key_add(name='Basis',from_mix=False)
            for name,coords in shapes[obj.name].items():
                key=obj.shape_key_add(name=name,from_mix=False)
                for point,co in zip(key.data,coords): point.co=co
                key.value=0  # at rest; the runtime drives each shape
        return baked
    baked=bake(body)
    skin=character_skin('M_taxi_driver_skin',src,'old_lightskinned_male_diffuse2.png')
    baked.materials.append(skin)
    for poly in baked.polygons: poly.use_smooth=True
    for name in ['hair','brows','eyes','suit','lashes']: bake(proxies[name][0])
    proxies['hair'][0].data.materials.append(proxy_material('M_taxi_driver_hair','short02_diffuse.png',.55,clip=True,tint=(.2,.18,.17),normal='short02_normal.png'))
    proxies['brows'][0].data.materials.append(proxy_material('M_taxi_driver_brows','eyebrow002.png',.7,clip=True,tint=(.35,.3,.27)))
    proxies['lashes'][0].data.materials.append(proxy_material('M_taxi_driver_lashes','eyelashes01.png',.7,clip=True))
    proxies['eyes'][0].data.materials.append(proxy_material('M_taxi_driver_eye','brown_eye.png',.12,tint=(.82,.78,.72)))
    # Washed cotton shirt over faded dark trousers, split at his waist.
    shirt=faded_cotton('M_taxi_driver_cotton',(.66,.62,.52)); trousers=faded_cotton('M_taxi_driver_trousers',(.13,.13,.12))
    suit_mesh=proxies['suit'][0].data; suit_mesh.materials.append(shirt); suit_mesh.materials.append(trousers)
    waist=place(Vector((0,hip.y+1.0,0))).z
    for poly in suit_mesh.polygons:
        poly.material_index=0 if sum(suit_mesh.vertices[i].co.z for i in poly.vertices)/len(poly.vertices)>waist else 1
    def world(v): return Vector((-.39+v.x*.10,.54+(v.y-hip.y)*.115,.035+v.z*.10))
    for target in ik_targets: bpy.data.objects.remove(target,do_unlink=True)
    bpy.data.objects.remove(rig,do_unlink=True)
    print('TAXI_DRIVER_HIP',hip[:], 'bounds',min(v.co.z for v in baked.vertices),max(v.co.z for v in baked.vertices))

def road_x(z): return 3.8*math.sin(z*.018)+2.2*math.sin(z*.037)
def road_heading(z): return math.atan(3.8*.018*math.cos(z*.018)+2.2*.037*math.cos(z*.037))
def road_point(x,y,z):
    a=road_heading(z)
    return (road_x(z)+x*math.cos(a),y,z-x*math.sin(a))

ROAD_HALF_WIDTH=2.8
PLANT_CLEARANCE=ROAD_HALF_WIDTH+.6

def road_lateral(x,z):
    # Nearest centreline parameter, including the normal offset around bends.
    t=np.array(z,copy=True)
    for _ in range(5):
        centre=3.8*np.sin(t*.018)+2.2*np.sin(t*.037)
        slope=3.8*.018*np.cos(t*.018)+2.2*.037*np.cos(t*.037)
        t+=((x-centre)*slope+z-t)/(1+slope*slope)
    angle=np.arctan(3.8*.018*np.cos(t*.018)+2.2*.037*np.cos(t*.037))
    return (x-3.8*np.sin(t*.018)-2.2*np.sin(t*.037))*np.cos(angle)-(z-t)*np.sin(angle)

# Where the journey's set pieces stand, in metres along the route (TaxiApparitions reads the same).
RITUAL_Z=212.0

def roadside():
    bpy.ops.wm.open_mainfile(filepath=str(ART/'ep1_area_village.blend'))
    original=bpy.context.scene
    objects=bpy.data.objects
    def family(pattern,count):
        found=sorted((o for o in objects if o.type=='MESH' and re.fullmatch(pattern,o.name)),key=lambda o:(o.dimensions.z,o.name))
        return [found[round(i*(len(found)-1)/max(1,count-1))].name for i in range(min(count,len(found)))]
    # The village's old-growth giants, a spread of heights and crowns, and its dead and termite-built ground.
    giants=family(r'tree_\d{1,3}',9)
    giants=[name for name in giants if objects.get('col_'+name)]
    dead=family(r'dead_\d+',4); mounds=family(r'termite_\d+',2)
    understory=family(r'jungle_understory_-?\d+_-?\d+',5); litter=family(r'jungle_litter_-?\d+_-?\d+',3)
    sedge=family(r'forest_edge_sedge_-?\d+_-?\d+',3)
    small=['shrub_02_a','shrub_02_b','shrub_02_c','fern_02_a.001','fern_02_b','fern_02_c','shrub_02_a.001','forest_grass_-1_-1']
    rite=['spirit_house','tingmong_0','tingmong_1','old_flag_0','old_flag_1','old_flag_2','old_flag_3','ground_offering_0','ground_offering_1','path_threads_0','path_threads_1','milestone']
    rite+=family(r'step_candle_\d+',3)+family(r'altar_incense_\d+',3)
    names=giants+dead+mounds+understory+litter+sedge+small+rite+['bamboo_0','coco_0','palm_0']
    templates={name:objects.get(name) for name in names}
    missing=[name for name,obj in templates.items() if obj is None]
    if missing: print('TAXI_MISSING_TEMPLATES',missing)
    mats={m.name:m for m in bpy.data.materials}
    scene=bpy.data.scenes.new('Taxi_monsson_road'); bpy.context.window.scene=scene
    rng=np.random.default_rng(2008)
    plant_vertices={}
    def plant(name,offset,z,scale=1,yaw=None,label=None,clear=PLANT_CLEARANCE,lift=-.12,ground=False):
        src=templates.get(name)
        if not src: return None
        bounds=[src.matrix_world @ Vector(c) for c in src.bound_box]
        foot=Vector(((min(p.x for p in bounds)+max(p.x for p in bounds))/2,(min(p.y for p in bounds)+max(p.y for p in bounds))/2,min(p.z for p in bounds) if ground else 0))
        col=bpy.data.objects.get('col_'+name.removeprefix('far_'))
        if col: foot=col.matrix_world.translation.copy(); foot.z=0
        obj=src.copy(); obj.data=src.data; scene.collection.objects.link(obj); obj.parent=None
        obj.name='taxi_road_'+(label or name)
        turn=float(rng.random()*math.tau) if yaw is None else yaw-road_heading(z)
        pose=Matrix.Rotation(turn,4,'Z') @ Matrix.Scale(scale,4) @ Matrix.Translation(-foot) @ src.matrix_world
        if name not in plant_vertices:
            plant_vertices[name]=np.array([(*v.co,1) for v in src.data.vertices],dtype=np.float64)
        side=1 if offset>0 else -1
        for _ in range(6):
            obj.matrix_world=Matrix.Translation(w(road_point(offset,lift,z))) @ pose
            if clear is None: break
            points=plant_vertices[name] @ np.array(obj.matrix_world,dtype=np.float64).T
            low=points[points[:,2]<2.8]
            if not len(low): break
            clearance=float(np.min(side*road_lateral(-low[:,0],-low[:,1])))
            if clearance>=clear: break
            offset+=side*(clear-clearance+.04)
        else: raise RuntimeError('Vegetation intrudes on taxi road: '+obj.name)
        obj.hide_render=False; obj.hide_set(False)
        return obj
    far_templates=[]
    for name in giants[-3:-1]:
        obj=templates[name].copy();obj.data=templates[name].data.copy();scene.collection.objects.link(obj)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        mod=obj.modifiers.new('Distant canopy LOD','DECIMATE');mod.ratio=.4
        bpy.ops.object.modifier_apply(modifier=mod.name)
        templates['far_'+name]=obj;far_templates.append(obj)
    # Keep the set pieces' ground clear of trunks so they read in the headlights.
    def clearing(side,z):
        if side>0 and abs(z-RITUAL_Z)<7: return True
        return False
    # Old-growth jungle closes both sides as tightly as at the village: giants with lianas,
    # saplings under them, dead snags and termite mounds, and a second wall behind.
    for side in [-1,1]:
        z=-24+float(rng.random()*6)
        while z<510:
            kind=str(rng.choice(giants+['bamboo_0','coco_0','palm_0']+dead,p=None))
            if kind in ['coco_0','palm_0','bamboo_0'] and rng.random()<.6: kind=str(rng.choice(giants))
            if kind in dead and rng.random()<.5: kind=str(rng.choice(giants))
            # Behind the rite the giants stand back and frame the clearing.
            lateral=float(rng.uniform(9.5,12)) if clearing(side,z) else float(rng.uniform(4.2,9.5))
            plant(kind,side*lateral,z,float(rng.uniform(.55,1.0) if kind in giants else rng.uniform(.8,1.15)))
            z+=float(rng.uniform(3.0,5.2))
        # A middle wall of full crowns, unshadowed like the far wall, fills the gaps between trunks.
        z=-24+float(rng.random()*5)
        while z<510:
            kind=str(rng.choice(giants))
            plant('far_'+str(rng.choice(giants[-3:-1])),side*float(rng.uniform(9,13)),z,float(rng.uniform(.6,.95)))
            z+=float(rng.uniform(4.0,6.5))
        z=-24+float(rng.random()*5)
        while z<510:
            if not clearing(side,z):
                # Young growth under the giants: snags, bamboo, sugar palms, the odd sapling.
                kind=str(rng.choice(dead+['bamboo_0','palm_0',str(rng.choice(giants))],p=None))
                scale=float(rng.uniform(.22,.38) if kind in giants else rng.uniform(.5,.85))
                plant(kind,side*float(rng.uniform(3.6,6.5)),z,scale)
            z+=float(rng.uniform(4.5,7.5))
        z=-24+float(rng.random()*4)
        while z<510:
            plant('far_'+str(rng.choice(giants[-3:-1])),side*float(rng.uniform(13,21)),z,float(rng.uniform(.6,1.0)))
            z+=float(rng.uniform(4.5,7.0))
        # Deeper still, sparser crowns, then painted walls of forest beyond them, so no
        # gap or horizon ever opens between the trunks.
        z=-24+float(rng.random()*6)
        while z<510:
            plant('far_'+str(rng.choice(giants[-3:-1])),side*float(rng.uniform(22,31)),z,float(rng.uniform(.8,1.15)))
            z+=float(rng.uniform(6,9))
        forest_wall(side,rng)
        # A continuous understory and leaf-litter floor beyond the shoulder, as under the village canopy.
        z=-24+float(rng.random()*3)
        while z<510:
            if clearing(side,z): z+=3; continue
            plant(str(rng.choice(understory)),side*float(rng.uniform(3.8,7.5)),z,float(rng.uniform(.9,1.25)))
            if rng.random()<.6: plant(str(rng.choice(litter)),side*float(rng.uniform(4,9)),z+float(rng.uniform(-2,2)),1.0)
            z+=float(rng.uniform(3.2,4.6))
        z=-24+float(rng.random()*3)
        while z<510:
            if clearing(side,z): z+=3; continue
            plant(str(rng.choice(sedge)),side*float(rng.uniform(3.6,4.4)),z,float(rng.uniform(.7,1.0)))
            z+=float(rng.uniform(5,8))
        for i in range(420):
            z=float(rng.uniform(-24,510))
            if clearing(side,z): continue
            plant(str(rng.choice(small)),side*float(rng.uniform(3.4,9)),z,float(rng.uniform(.65,1.35)))
        for i in range(26):
            z=float(rng.uniform(-20,505))
            if not clearing(side,z): plant(str(rng.choice(mounds)),side*float(rng.uniform(5,12)),z,float(rng.uniform(.7,1.1)))
        z=-24+float(rng.random()*4)
        while z<510:
            plant('fern_02_a.001',side*float(rng.uniform(3.5,4.2)),z,float(rng.uniform(.4,.72)))
            z+=float(rng.uniform(3.0,6.0))
    road_surface(mats,rng)
    telegraph_line(mats,rng)
    # Roadside omens: rotting funeral flags, threads strung through the trees, incense
    # left at the foot of trunks and the Ting Mong guarding the village approach.
    for z,side,flag in [(96,-1,'old_flag_0'),(171,1,'old_flag_2'),(302,1,'old_flag_1'),(418,-1,'old_flag_3'),(461,1,'old_flag_0')]:
        plant(flag,side*3.9,z,1,yaw=float(rng.uniform(-.4,.4)),clear=3.2,label='omen_'+flag+'_'+str(z),ground=True,lift=-.25)
    for z,side,thread in [(148,-1,'path_threads_0'),(364,1,'path_threads_1'),(489,-1,'path_threads_0')]:
        plant(thread,side*4.6,z,1,yaw=math.pi/2,clear=None,label='omen_'+thread+'_'+str(z),lift=.2)
    for z,side in [(61,1),(128,-1),(338,-1),(402,1)]:
        plant(family_pick(templates,'altar_incense'),side*3.75,z,1,yaw=0,clear=None,label='omen_incense_'+str(z),lift=-.16,ground=True)
        plant(family_pick(templates,'step_candle'),side*3.85,z+.3,1,yaw=0,clear=None,label='omen_candle_'+str(z),lift=-.16,ground=True)
    for z,side,guard in [(474,-1,'tingmong_0'),(477,1,'tingmong_1')]:
        plant(guard,side*4.1,z,1,yaw=math.pi if side>0 else 0,clear=3.4,label='guardian_'+guard,ground=True,lift=-.22)
    for z,side in [(38,-1),(238,-1),(438,-1)]:
        plant('milestone',side*3.45,z,1,yaw=math.pi/2,clear=None,label='milestone_'+str(z),lift=-.2,ground=True)
    roadside_rite(dead[-1],plant,mats,rng)
    for obj in far_templates:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.scenes.remove(original)
    bpy.data.orphans_purge(do_recursive=True)
    export('ep1_taxi_roadside')

def family_pick(templates,prefix):
    return next(name for name in templates if name.startswith(prefix) and templates[name])

def smooth(obj):
    # Shared smooth normals keep one vertex per grid point instead of four.
    for poly in obj.data.polygons: poly.use_smooth=True
    return obj

FOREST_WALL=None
def forest_wall(side,rng):
    """Overlapping cut-out cards of trunks, lianas and canopy at 34 and 44 metres, black-
    green under the storm: the forest goes on past the far plane on both sides."""
    global FOREST_WALL
    if FOREST_WALL is None:
        n=512; r=np.random.default_rng(77); alpha=np.zeros((n,n)); shade=np.zeros((n,n))
        yy,xx=np.mgrid[:n,:n]/n
        for k in range(26):  # trunks, a few leaning, flaring at the foot
            x0=r.uniform(0,1); w=r.uniform(.006,.03); lean=r.normal(0,.03)
            d=np.abs(xx-(x0+lean*(1-yy)))-w*(1+1.5*np.clip(.15-yy,0,1)/.15)
            alpha=np.maximum(alpha,(d<0)*(yy<r.uniform(.55,.85))); shade+=(d<0)*r.uniform(-.2,.2)
        for k in range(60):  # canopy masses
            cx,cy,rad=r.uniform(-.05,1.05),r.uniform(.45,.98),r.uniform(.05,.16)
            alpha=np.maximum(alpha,((xx-cx)**2+((yy-cy)*1.3)**2<rad**2)*1.0)
        for k in range(40):  # undergrowth along the foot
            cx,cy,rad=r.uniform(0,1),r.uniform(-.02,.12),r.uniform(.03,.08)
            alpha=np.maximum(alpha,((xx-cx)**2+((yy-cy)*2)**2<rad**2)*1.0)
        ragged=r.random((n,n))<.86
        alpha=alpha*np.where(yy>.5,ragged,1)
        colour=np.stack([.012+.004*shade,.019+.006*shade,.014+.004*shade],axis=-1).clip(0,1)
        rgba=np.concatenate([colour,alpha[...,None]],axis=-1)
        img=bpy.data.images.new('T_taxi_forest_wall',width=n,height=n,alpha=True)
        img.pixels.foreach_set(rgba.astype(np.float32).ravel())
        img.filepath_raw=str(TEX/'T_taxi_forest_wall_BC.png'); img.file_format='PNG'; img.save()
        mat=plain('M_taxi_forest_wall',(1,1,1),.95); nodes=mat.node_tree.nodes; bs=nodes['Principled BSDF']
        t=nodes.new('ShaderNodeTexImage'); t.image=img; mat.node_tree.links.new(t.outputs['Color'],bs.inputs['Base Color'])
        cut=nodes.new('ShaderNodeMath'); cut.operation='GREATER_THAN'; cut.inputs[1].default_value=.5
        mat.node_tree.links.new(t.outputs['Alpha'],cut.inputs[0]); mat.node_tree.links.new(cut.outputs[0],bs.inputs['Alpha'])
        mat.use_backface_culling=False; FOREST_WALL=mat
    for lateral,width,height in [(34,18,24),(44,22,30)]:
        z=-30+float(rng.random()*8)
        while z<520:
            l=lateral+float(rng.uniform(-2,2)); w_=width*float(rng.uniform(.85,1.15)); h=height*float(rng.uniform(.85,1.1))
            corners=[road_point(side*l,-.4,z),road_point(side*l,-.4,z+w_),road_point(side*l,h,z+w_),road_point(side*l,h,z)]
            o=quad('taxi_road_far_tree_wall',corners if side>0 else [corners[1],corners[0],corners[3],corners[2]],FOREST_WALL)
            z+=w_*float(rng.uniform(.55,.75))

def road_surface(mats,rng):
    """A laterite cart track: two deep wheel ruts with mud pushed up beside them, a grassy
    centre hump, a crumbling edge into flooded ditches, gravel, and pools in the ruts."""
    floor=mats['M_wet_forest_floor']; mud=mats['M_wet_mud']
    columns=[-70,-52,-40,-32,-26,-20,-15,-11,-8.5,-6.5,-5.2,-4.4,-3.9,-3.65,-3.45,-3.3,-3.15,-3.0,-2.85,-2.6,-2.0,-1.0]
    columns=columns+[0]+[-x for x in reversed(columns)]
    def ditch(x): return .17*math.exp(-((abs(x)-3.3)/.34)**2)
    vs=[];fs=[];rows=540
    for i in range(rows+1):
        z=-28+i
        for x in columns:
            y=-.22+.028*math.sin(x*.7+z*.3)+.018*math.sin(z*.8+x*2)-ditch(x)
            vs.append(road_point(x,y,z))
    n=len(columns)
    for i in range(rows):
        for j in range(n-1): a=i*n+j; fs.append((a,a+n,a+n+1,a+1))
    smooth(mesh('taxi_road_ground',vs,fs,floor))
    vs=[];fs=[];rows=1080;steps=32;span=ROAD_HALF_WIDTH
    for i in range(rows+1):
        z=-28+i*.5
        for j in range(steps+1):
            x=-span+2*span*j/steps; a=abs(x)
            rut=math.exp(-((a-.72)/.19)**2)*.07
            berm=math.exp(-((a-1.0)/.12)**2)*.022+math.exp(-((a-.44)/.1)**2)*.018
            edge=.06*min(1,max(0,(a-2.25)/.55))**2
            grain=.008*math.sin(z*1.8+x*3)+.005*math.sin(z*4.3-x*7.1)+.003*math.sin(z*11.7+x*5.3)
            y=-.13+.055*(1-(x/span)**2)-rut+berm-edge+grain
            vs.append(road_point(x,y,z))
    for i in range(rows):
        for j in range(steps): a=i*(steps+1)+j; fs.append((a,a+steps+1,a+steps+2,a+1))
    smooth(mesh('taxi_muddy_track',vs,fs,mud))
    puddle=mats['M_puddle']
    def water_patch(x,z,radius,long,name='taxi_rut_water',y=-.058,limit=ROAD_HALF_WIDTH-.08):
        # Shallow standing water lies above the road crown, never buried beneath mud.
        vs=[road_point(x,y,z)]; count=24
        for j in range(count):
            a=j/count*math.tau; r=radius*(.90+.07*math.sin(j*2.7)+.03*math.sin(j*4.1))
            lateral=max(-limit,min(limit,x+math.cos(a)*r)) if limit else x+math.cos(a)*r
            vs.append(road_point(lateral,y,z+math.sin(a)*long))
        mesh(name,vs,[(0,(j+1)%count+1,j+1) for j in range(count)],puddle)
    for i in range(170):
        x=float(rng.choice([-1,1]))*.74+float(rng.normal(0,.22)); z=-24+float(rng.random()*532)
        water_patch(x,z,float(rng.uniform(.4,.95)),float(rng.uniform(.8,2.7)))
    for i in range(48):
        water_patch(float(rng.uniform(-.15,.15)),-22+i*11.1+float(rng.uniform(-2,2)),float(rng.uniform(2.1,2.65)),float(rng.uniform(3.5,6.2)))
    # Run-off standing in the ditches, broken where the bank has slumped.
    for side in [-1,1]:
        z=-26.0
        while z<510:
            length=float(rng.uniform(5,22)); r=float(rng.uniform(.18,.27))
            vs=[];fs=[]
            for k in range(int(length)+1):
                zz=z+k; wobble=.05*math.sin(zz*.9+side)
                vs+= [road_point(side*3.3-r+wobble,-.31,zz),road_point(side*3.3+r+wobble,-.31,zz)]
            for k in range(int(length)): a=k*2; fs.append((a,a+2,a+3,a+1))
            mesh('taxi_ditch_water',vs,fs,puddle)
            z+=length+float(rng.uniform(2,9))
    # Laterite gravel and pebbles kicked out of the ruts, mostly on the crown and verges.
    stone=mud
    pebbles=[]
    for k in range(4):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1)
        p=bpy.context.object; p.name='taxi_road_pebble_shape_'+str(k)
        for v in p.data.vertices: v.co=Vector((v.co.x*(1+.35*rng.random()),v.co.y*(1+.35*rng.random()),v.co.z*(.45+.2*rng.random())))
        p.data.materials.append(stone); plain_uvs(p); pebbles.append(p)
    for i in range(900):
        z=float(rng.uniform(-26,508)); a=float(rng.choice([rng.uniform(0,.35),rng.uniform(1.05,2.7),rng.uniform(.45,1.0)],p=[.3,.55,.15]))
        x=float(rng.choice([-1,1]))*a
        src=pebbles[int(rng.integers(len(pebbles)))]
        o=src.copy(); o.data=src.data; bpy.context.collection.objects.link(o); o.name='taxi_road_pebble'
        size=float(rng.uniform(.018,.06))
        crown=-.13+.055*(1-(x/ROAD_HALF_WIDTH)**2)-math.exp(-((abs(x)-.72)/.19)**2)*.07+math.exp(-((abs(x)-1.0)/.12)**2)*.022
        o.matrix_world=Matrix.Translation(w(road_point(x,crown+size*.2,z)))@Matrix.Rotation(float(rng.random()*math.tau),4,'Z')@Matrix.Scale(size,4)
    for p in pebbles: bpy.data.objects.remove(p,do_unlink=True)
    # Grass grows along the untouched centre hump between the wheel ruts.
    grass=mats['M_forest_grass']
    blades=[];faces=[]
    tufts=[]
    for i in range(2600):
        z=float(rng.uniform(-26,508)); x=float(rng.normal(0,.08))
        if rng.random()<.3: x=float(rng.choice([-1,1])*rng.uniform(1.25,2.55))
        tufts.append((x,z))
    for i in range(11000):
        tx,tz=tufts[i%len(tufts)]
        x=tx+float(rng.normal(0,.035)); z=tz+float(rng.normal(0,.05))
        h=float(rng.uniform(.05,.16)); lean=float(rng.uniform(0,math.tau)); bend=float(rng.uniform(.01,.06))
        base=-.13+.055*(1-(x/ROAD_HALF_WIDTH)**2)+math.exp(-((abs(x)-1.0)/.12)**2)*.022-.004
        width=float(rng.uniform(.006,.012))
        k=len(blades)
        root=Vector(road_point(x,base,z)); tip=Vector(road_point(x+math.cos(lean)*bend,base+h,z+math.sin(lean)*bend))
        across=Vector((math.cos(lean+1.57)*width,0,math.sin(lean+1.57)*width))
        blades+=[tuple(root-across),tuple(root+across),tuple(tip)]
        faces.append((k,k+1,k+2))
    o=mesh('taxi_median_grass',blades,faces,grass)
    for poly in o.data.polygons: poly.use_smooth=True
    grass.use_backface_culling=False

def telegraph_line(mats,rng):
    """The colonial telegraph follows the road on the left: tarred posts, cross-arms with
    glass insulators and two sagging wires; some posts lean and one arm hangs broken."""
    post=mats.get('M_wet_tarred_post',mats['M_wet_bark']); arm=mats.get('M_wet_old_planks',post)
    glass=mats.get('M_glass_insulator',post); iron=mats.get('M_iron',post)
    tops=[]
    z=-18.0; k=0
    while z<512:
        x=-3.95-float(rng.uniform(0,.35)); lean=float(rng.normal(0,.035)); roll=float(rng.normal(0,.03))
        if k%5==3: lean+=float(rng.choice([-1,1]))*.09
        h=float(rng.uniform(5.6,6.2))
        heading=road_heading(z)
        def at(lateral,up,along=0.0):
            # Lean the post about its foot, then sit it beside the road.
            return road_point(x+lateral+up*roll,-.2+up,z+along+up*lean)
        tube('taxi_telegraph_post',[at(0,-.4),at(0,h)],.085,post)
        broken=k==7
        if broken:
            tube('taxi_telegraph_arm_broken',[at(-.05,h-.25),at(.25,h-1.2,.1)],.035,arm)
        else:
            tube('taxi_telegraph_arm',[at(-.62,h-.28),at(.62,h-.28)],.04,arm)
        pins=[]
        for lateral in [-.5,.5]:
            if broken: lateral=.25 if lateral>0 else -.05
            ups=h-.28 if not broken else (h-1.2 if lateral>0 else h-.25)
            tube('taxi_telegraph_pin',[at(lateral,ups),at(lateral,ups+.11)],.008,iron)
            ellipsoid('taxi_telegraph_insulator',at(lateral,ups+.14),(.065,.09,.065),glass)
            pins.append(Vector(at(lateral,ups+.17)))
        tops.append(pins)
        z+=float(rng.uniform(38,47)); k+=1
    for a,b in zip(tops,tops[1:]):
        for p,q in zip(a,b):
            sag=float(rng.uniform(.55,.9)); points=[]
            for i in range(13):
                t=i/12; v=p.lerp(q,t); v.y-=sag*4*t*(1-t); points.append(tuple(v))
            tube('taxi_telegraph_wire',points,.0045,iron)

def roadside_rite(dead,plant,mats,rng):
    """A sending-away rite left where the forest meets the road (advisor review): a lone
    dead tree bound in white cloth, the spirit house and offerings at its foot, flags,
    a Ting Mong keeping watch, and inside a ring of bamboo stakes and white thread a
    banana-stem raft carrying a cloth-wrapped effigy among candles still burning in the rain."""
    z0=RITUAL_Z
    cotton=mats.get('M_funeral_linen',mats.get('M_tent_cotton')); thread=mats.get('M_white_thread',cotton)
    bamboo=mats.get('M_bamboo',mats['M_wet_bark']); banana=mats.get('M_banana_stem',bamboo)
    leaf=mats.get('M_shrine_folded_banana_leaf',mats.get('M_banana_leaf',banana))
    wax=mats.get('M_candle_wax',mats.get('M_funeral_wax',cotton)); clay=mats.get('M_shrine_clay',mats.get('M_clay',cotton))
    incense=mats.get('M_incense',bamboo); red=mats.get('M_wet_cloth_red',cotton); ash=mats.get('M_shrine_ash',clay)
    flame=plain('M_taxi_ritual_flame',(1,.62,.25),.5,emission=(1,.55,.18),strength=6)
    tree=plant(dead,7.6,z0+1.0,1.2,yaw=.3,clear=6.4,label='rite_dead_tree')
    if tree:
        foot=tree.matrix_world.translation
        bark=Vector((-foot.x,foot.z,-foot.y))
        for h,r in [(1.05,.42),(1.22,.44),(1.4,.41)]:
            tube('taxi_rite_trunk_cloth',[tuple(bark+Vector((math.cos(a)*r,h+.03*math.sin(a*3),math.sin(a)*r))) for a in [i/24*math.tau for i in range(25)]],.06,cotton)
    plant('spirit_house',4.3,z0-2.9,1,yaw=-1.57,clear=None,label='rite_spirit_house',lift=-.18,ground=True)
    plant('ground_offering_0',4.15,z0-1.4,1,yaw=0,clear=None,label='rite_offering_0',lift=-.2,ground=True)
    plant('ground_offering_1',4.2,z0-3.0,1,yaw=.6,clear=None,label='rite_offering_1',lift=-.2,ground=True)
    plant('old_flag_1',4.4,z0-5.0,1,yaw=.2,clear=None,label='rite_flag_0',ground=True,lift=-.25)
    plant('old_flag_3',5.2,z0+5.2,1,yaw=-.3,clear=None,label='rite_flag_1',ground=True,lift=-.25)
    plant('tingmong_1',4.3,z0+3.8,1,yaw=math.pi,clear=None,label='rite_tingmong',ground=True,lift=-.22)
    plant('path_threads_1',4.15,z0+.2,1,yaw=math.pi/2,clear=None,label='rite_threads',lift=.15)
    # The ring: ten bamboo stakes with a white cotton cord run three times round their tops.
    cx=5.4; r=1.45; stakes=[]
    for i in range(10):
        a=i/10*math.tau+.2
        lat=cx+math.cos(a)*r; zz=z0+math.sin(a)*r*1.25; h=float(rng.uniform(.68,.86)); tilt=float(rng.normal(0,.04))
        tube('taxi_rite_stake',[road_point(lat,-.3,zz),road_point(lat+tilt,h-.2,zz+tilt)],.018,bamboo)
        stakes.append((lat+tilt,h-.24,zz+tilt))
    for loop,drop in enumerate([0,.08,.16]):
        points=[]
        for i in range(11):
            a=stakes[i%10]; b=stakes[(i+1)%10]
            points.append(road_point(a[0],a[1]-drop,a[2]))
            points.append(road_point((a[0]+b[0])/2,(a[1]+b[1])/2-drop-.05,(a[2]+b[2])/2))
        if loop==2: points=points[:13]+[road_point(stakes[6][0]-.1,-.2,stakes[6][2]+.15)]  # snapped, trailing in the mud
        tube('taxi_rite_cord',points,.0045,thread)
    # Banana-stem raft carrying a life-size effigy bound in white cloth, its face covered.
    for k,dx in enumerate([-.2,-.07,.07,.2]):
        tube('taxi_rite_raft_stem',[road_point(cx+dx,-.17,z0-1.0),road_point(cx+dx,-.17,z0+1.0)],.07,banana)
    for dz in [-.75,0,.75]:
        tube('taxi_rite_raft_pin',[road_point(cx-.32,-.12,z0+dz),road_point(cx+.32,-.12,z0+dz)],.009,bamboo)
    body=[(-.62,.07,.17,.14),(-.42,.1,.3,.15),(-.15,.11,.34,.16),(.12,.1,.3,.15),(.38,.08,.24,.13),(.62,.06,.18,.11)]
    for along,height,width,length in body:
        ellipsoid('taxi_rite_effigy_wrap',road_point(cx,-.05+height*.5,z0+along),(width,height*1.6,length*2.4),cotton)
    ellipsoid('taxi_rite_effigy_head',road_point(cx,.0,z0-.86),(.2,.17,.22),cotton)
    for along in [-.86,-.7,-.48,-.2,.1,.36,.6,.78]:
        loop=[road_point(cx+math.cos(a)*.16,-.02+math.sin(a)*.1,z0+along) for a in [i/18*math.tau for i in range(19)]]
        tube('taxi_rite_effigy_binding',loop,.004,thread)
    ellipsoid('taxi_rite_effigy_red_cloth',road_point(cx,.0,z0+.74),(.3,.07,.26),red)
    # Two bamboo poles hung with long white banners at the road edge catch the headlights first.
    for k,(lat,zz,h) in enumerate([(3.65,z0-1.6,3.1),(3.75,z0+1.9,2.7)]):
        tube('taxi_rite_banner_pole',[road_point(lat,-.3,zz),road_point(lat+.05,h,zz+.04)],.025,bamboo)
        vs=[];fs=[]
        for i in range(13):
            t=i/12; y=h-.12-t*1.9; sway=.06*math.sin(t*4+k)*t
            for u in [-.13,.13]: vs.append(road_point(lat+.04+sway,y,zz+.04+u+.02*math.sin(t*7)))
        for i in range(12): a=i*2; fs.append((a,a+1,a+3,a+2))
        banner=mesh('taxi_rite_banner',vs,fs,cotton)
    cotton.use_backface_culling=False
    # Banana-leaf cones, a clay bowl of incense ash, and candles round the raft and the stakes.
    for k in range(8):
        a=k/8*math.tau+.4; lat=cx+math.cos(a)*.72; zz=z0+math.sin(a)*1.15
        ellipsoid('taxi_rite_leaf_cone',road_point(lat,-.06,zz),(.08,.24,.08),leaf)
    ellipsoid('taxi_rite_bowl',road_point(cx-.75,-.2,z0-.1),(.26,.11,.26),clay)
    ellipsoid('taxi_rite_ash',road_point(cx-.75,-.15,z0-.1),(.22,.02,.22),ash)
    for k in range(11):
        a=float(rng.uniform(0,math.tau)); rr=float(rng.uniform(0,.08)); tilt=float(rng.normal(0,.05))
        base=road_point(cx-.75+math.cos(a)*rr,-.16,z0-.1+math.sin(a)*rr)
        tube('taxi_rite_incense',[base,(base[0]+tilt,base[1]+.26,base[2]+tilt*.5)],.003,incense)
    spots=[(-.5,-1.15),(.5,-1.15),(-.5,1.15),(.5,1.15),(-.95,.4),(.95,-.3),(.8,.6)]
    spots+=[(stake[0]-cx+.06,stake[2]-z0) for stake in stakes[::2]]
    for k,(dx,dz) in enumerate(spots):
        h=float(rng.uniform(.09,.18)); base=road_point(cx+dx,-.2,z0+dz)
        tube('taxi_rite_candle',[base,(base[0],base[1]+h,base[2])],.013,wax)
        ellipsoid('taxi_rite_candle_flame',(base[0],base[1]+h+.024,base[2]),(.013,.036,.013),flame)

mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'all'
if mode in ['all','roadside']: roadside()
if mode in ['all','cabin']: cabin()
