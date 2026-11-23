"""Author the taxi cabin and roadside from the episode's existing CC0 materials/plants.
blender -b --factory-startup -P tools/travel/build-taxi.py
World helpers use Babylon axes (x right, y up, z forward); export uses project glTF conversion.
"""
import bpy, bmesh, math, sys, json, re, gzip
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/areas'))
sys.path.insert(0, str(ROOT/'tools/travel'))
from kit import library_material, plain, world_uvs
from taxi_cabin_details import apply_cabin_details
from taxi_roadside_details import apply_roadside_details
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

# ----------------------------------------------------------------- the car
# A real 1933 Citroën Rosalie (CC BY, art-source/library/scans/taxi_rosalie.glb, prepared
# by taxi_scans.py) is the taxi: its own body, dashboard, wheel, seats and doors, lined
# where its maps are flat colour with photo textures from the Poly Haven library.
CAR_SCAN=ROOT/'art-source/library/scans/taxi_rosalie.glb'
# The Rosalie's cabin floor in its own frame; the cabin is authored with it at height 0.
CAR_FLOOR=.375
# Measured from the car in cabin(): the driver's hands close on this rim.
WHEEL_CENTRE=(-.265,.755,.275); WHEEL_FACING=(0,.6,-.8); WHEEL_RADIUS=.2
# Hips on the front cushions, and Sora's eyes (game axes), set from the car in cabin().
DRIVER_HIP=[-.27,.40,-.07]
# Thigh and knee bends (degrees) for the low 1930s seats: knees up, feet on the floorboards.
DRIVER_LEGS=(-86,48)
SORA_LEGS=(-86,52,18)
SORA_HIP=[.27,.40,-.12]
SORA_EYE=[.27,1.06,-.07]

def game(v):
    """The car's own (Blender) coordinates as game axes, once its floor is at 0."""
    return Vector((-v.x,v.z,-v.y))

def anchor(name,p):
    """An empty the runtime reads: lamps, wipers, glass, mirror and seats."""
    o=bpy.data.objects.new('taxi_anchor_'+name,None); bpy.context.collection.objects.link(o)
    o.location=w(p); return o

def import_glb(path):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new=[o for o in bpy.data.objects if o not in before]
    meshes=[o for o in new if o.type=='MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0]
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    for o in new:
        if o.type!='MESH': bpy.data.objects.remove(o)
    return meshes

def islands(bm):
    """Loose parts of a bmesh, as lists of faces."""
    bm.faces.ensure_lookup_table()
    seen=[False]*len(bm.faces); out=[]
    for f in bm.faces:
        if seen[f.index]: continue
        seen[f.index]=True; stack=[f]; group=[]
        while stack:
            g=stack.pop(); group.append(g)
            for v in g.verts:
                for h in v.link_faces:
                    if not seen[h.index]: seen[h.index]=True; stack.append(h)
        out.append(group)
    return out

def box_of(faces):
    co=[v.co for f in faces for v in f.verts]
    lo=Vector((min(c.x for c in co),min(c.y for c in co),min(c.z for c in co)))
    hi=Vector((max(c.x for c in co),max(c.y for c in co),max(c.z for c in co)))
    return lo,hi

def base_pixels(mat):
    for nd in mat.node_tree.nodes:
        if nd.type=='TEX_IMAGE' and nd.image and 'baseColor' in nd.image.name:
            img=nd.image; return np.array(img.pixels[:],dtype=np.float32).reshape(img.size[1],img.size[0],4)
    return None

def slot(obj,mat):
    for i,m in enumerate(obj.data.materials):
        if m==mat: return i
    obj.data.materials.append(mat); return len(obj.data.materials)-1

def split_photo(obj,photo):
    """Faces given a photo material become their own object with box-projected UVs at
    that material's real size; the rest keep the car's own maps."""
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bpy.ops.mesh.separate(type='MATERIAL')
    for part in list(bpy.context.selected_objects):
        mats=[m for m in part.data.materials if m]
        if not mats: continue
        used={p.material_index for p in part.data.polygons}
        if len(used)==1:
            mat=part.data.materials[used.pop()]
            part.data.materials.clear(); part.data.materials.append(mat)
            for p in part.data.polygons: p.material_index=0
            if mat in photo:
                for layer in list(part.data.uv_layers): part.data.uv_layers.remove(layer)
                world_uvs(part)
            part.name=part.data.name='taxi_car_'+mat.name.removeprefix('M_').lower()

def ray_down(x,y,z=1.4):
    """Height of the first car surface below (x, y) in the car's frame."""
    dg=bpy.context.evaluated_depsgraph_get()
    hit,loc,*_=bpy.context.scene.ray_cast(dg,Vector((x,y,z)),Vector((0,0,-1)))
    return loc.z if hit else None

def cabin():
    global WHEEL_CENTRE,WHEEL_FACING,WHEEL_RADIUS
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # The importer reuses a "glTF Material Output" group and expects all its sockets.
    from io_scene_gltf2.blender.com.material_helpers import create_settings_group, get_gltf_node_name
    if get_gltf_node_name() not in bpy.data.node_groups: create_settings_group(get_gltf_node_name())
    parts={o.name.split('_M_')[0]+('' if '.0' not in o.name else o.name[-4:]):o for o in import_glb(CAR_SCAN)}
    for o in parts.values(): o.data.transform(Matrix.Translation((0,0,-CAR_FLOOR)))
    # Photo-textured linings for what the car's own maps leave as flat paint.
    headliner=library_material('rough_linen','M_taxi_headliner',tint=(.095,.088,.076),tile=.22)
    cloth=library_material('rough_linen','M_taxi_trim_cloth',tint=(.085,.078,.068),tile=.26)
    carpet=library_material('dirty_carpet','M_taxi_carpet',tint=(.42,.38,.33),tile=.7)
    fascia=library_material('rosewood_veneer1','M_taxi_dashboard_walnut',tint=(.26,.17,.11),tile=.28)
    steel=library_material('rusty_metal','M_taxi_painted_steel',colour=(.028,.03,.028),tile=.5)
    photo={headliner,cloth,carpet,fascia,steel}
    nickel=plain('M_taxi_aged_nickel',(.42,.41,.37),.34,.9)
    bakelite=plain('M_taxi_bakelite',(.018,.016,.014),.38)
    rubber=plain('M_taxi_rubber',(.016,.016,.015),.8)
    glass=plain('M_taxi_window_glass',(.07,.095,.11),.13,.05,alpha=.07); glass.use_backface_culling=False
    lens=plain('M_taxi_headlamp_glass',(.55,.52,.46),.08,.0)
    for mat in [carpet,cloth,steel,headliner]: mat.use_backface_culling=False
    for o in parts.values():
        name=o.name
        bm=bmesh.new(); bm.from_mesh(o.data)
        doomed=[]
        mat=o.data.materials[0] if o.data.materials else None
        pixels=base_pixels(mat) if mat else None
        uvl=bm.loops.layers.uv.active
        for group in islands(bm):
            lo,hi=box_of(group); c=(lo+hi)/2; d=hi-lo; size=max(d); thin=sorted(d)[1]
            def put(m):
                i=slot(o,m)
                for f in group: f.material_index=i
            if name.startswith('SM_Glass'):
                if -.52<c.y<-.42 and abs(c.x)<.1 and size>.6: doomed+=group   # windscreen: the runtime's wet glass
                elif c.y>1.7: doomed+=group                                       # tail lamps
                elif c.y<-1.5: put(lens)
                else: put(glass)
            elif name.startswith('SM_internal'):
                if thin<.03 and size>.12: put(nickel)                              # rods: gear, brake, stalks
                elif size<.13 and c.z<.25: put(rubber)                             # pedal pads
                elif size<.13 or (abs(c.x)<.1 and c.z>.95 and size<.2): put(bakelite)  # knobs, mirror back
            elif name.startswith('SM_interiorcarroserie'):
                for f in group:
                    n=f.normal; fc=f.calc_center_median()
                    if n.z>.6 and fc.z<.15: f.material_index=slot(o,carpet)
                    elif fc.z>.86: f.material_index=slot(o,headliner)
                    elif -.78<fc.y<-.40 and .35<fc.z<=.86 and abs(fc.x)<.62: f.material_index=slot(o,fascia)
                    elif fc.y<-.42: f.material_index=slot(o,steel)
                    elif fc.z>.72: f.material_index=slot(o,headliner)
                    else: f.material_index=slot(o,cloth)
            elif name.startswith('SM_door') or name.startswith('Object136') or name.startswith('SM_external'):
                rgb=Vector((0,0,0))
                if pixels is not None and uvl is not None:
                    hgt,wid=pixels.shape[:2]
                    for f in group[:40]:
                        uv=sum((l[uvl].uv for l in f.loops),Vector((0,0)))/len(f.loops)
                        px=pixels[int((uv.y%1)*(hgt-1)),int((uv.x%1)*(wid-1))]; rgb+=Vector(px[:3])
                    rgb/=min(40,len(group))
                bright=(rgb.x+rgb.y+rgb.z)/3
                if size<.4 and bright>.45 and rgb.z>=rgb.x*.85:                    # handles, cranks, trim
                    put(nickel); continue
                # A door is one part inside and out: line its inner face below the sill with
                # cloth, and the roof skin seen from the seats with the headliner.
                for f in group:
                    fc=f.calc_center_median(); n=f.normal
                    inside=abs(fc.x)<.68 and -.52<fc.y<1.62
                    # Pillars and roof are cloth-covered above the sills, as the headlining ran down them.
                    if inside and abs(fc.x)<.645 and fc.z>.72 and fc.y>-.62 and (fc.y>-.46 or abs(fc.x)>.47): f.material_index=slot(o,headliner)
                    # (The car's normals here are not reliable: the inner skin lies inboard of the outer.)
                    elif abs(fc.x)<.645 and -.48<fc.y<1.62 and .0<fc.z<.72 and abs(n.x)>.5: f.material_index=slot(o,cloth)
        bm.faces.ensure_lookup_table()
        if doomed: bmesh.ops.delete(bm,geom=list(set(doomed)),context='FACES')
        bm.to_mesh(o.data); bm.free(); o.data.update()
    # The bonnet, wings and scuttle in old lacquer, which the runtime wets with rain.
    for key in ['SM_door.001','SM_external','Sm_gardeboue','Sm_gardeboue.001']:
        o=parts.get(key)
        if not o: continue
        for i,m in enumerate(list(o.data.materials)):
            if not m or m.name not in ('M_door','M_external','M_gardeboue'): continue
            lacquer=bpy.data.materials.get('M_taxi_body_lacquer_'+m.name[2:])
            if lacquer is None: lacquer=m.copy(); lacquer.name='M_taxi_body_lacquer_'+m.name[2:]
            k=slot(o,lacquer)
            for p in o.data.polygons:
                if p.material_index==i and p.center.y<-.45: p.material_index=k
    for o in list(parts.values()):
        if any(m in photo for m in o.data.materials): split_photo(o,photo)
    # Sora's side window, for the marks left on it.
    for o in [o for o in bpy.data.objects if o.type=='MESH' and any(m==glass for m in o.data.materials)]:
        bm=bmesh.new(); bm.from_mesh(o.data)
        sora=[f for f in bm.faces if f.calc_center_median().x<-.5 and -.4<f.calc_center_median().y<.4 and f.material_index==slot(o,glass)]
        if sora:
            pane=bmesh.new()
            for f in sora:
                pane.faces.new([pane.verts.new(v.co) for v in f.verts])
            data=bpy.data.meshes.new('taxi_side_glass_sora'); pane.to_mesh(data); pane.free()
            data.materials.append(glass)
            plain_layer=data.uv_layers.new(name='UVMap')
            lo,hi=Vector((min(v.co.x for v in data.vertices),min(v.co.y for v in data.vertices),min(v.co.z for v in data.vertices))),Vector((max(v.co.x for v in data.vertices),max(v.co.y for v in data.vertices),max(v.co.z for v in data.vertices)))
            for li,loop in enumerate(data.loops):
                v=data.vertices[loop.vertex_index].co
                plain_layer.data[li].uv=((v.y-lo.y)/((hi.y-lo.y) or 1),(v.z-lo.z)/((hi.z-lo.z) or 1))
            pane_obj=bpy.data.objects.new('taxi_side_glass_sora',data); bpy.context.collection.objects.link(pane_obj)
            bmesh.ops.delete(bm,geom=sora,context='FACES'); bm.to_mesh(o.data)
        bm.free()
    bpy.context.view_layer.update()
    # The wheel the driver holds: the car's own rim, a plane fitted through it.
    inner=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('SM_internal')]
    best=None
    for o in inner:
        bm=bmesh.new(); bm.from_mesh(o.data)
        for group in islands(bm):
            lo,hi=box_of(group); c=(lo+hi)/2; size=max(hi-lo)
            if .35<size<.5 and .12<c.x<.42 and .55<c.z<.95 and (best is None or len(group)>best[0]):
                best=(len(group),np.array([tuple(v.co) for f in group for v in f.verts]))
        bm.free()
    if best is not None:
        pts=best[1]; centre=pts.mean(axis=0); _,_,vt=np.linalg.svd(pts-centre); normal=Vector(vt[2])
        radius=float(np.mean(np.linalg.norm((pts-centre)-np.outer((pts-centre)@vt[2],vt[2]),axis=1)))
        facing=game(normal)
        if facing.z>0: facing=-facing
        WHEEL_CENTRE=tuple(game(Vector(centre))); WHEEL_FACING=tuple(facing.normalized()); WHEEL_RADIUS=radius
    print('TAXI_WHEEL',[round(v,3) for v in WHEEL_CENTRE],[round(v,3) for v in WHEEL_FACING],round(WHEEL_RADIUS,3))
    # Hips sit on the cushions the car really has; Sora's eyes are a seated woman's above hers.
    for hip,bx in [(DRIVER_HIP,.27),(SORA_HIP,-.27)]:
        top=ray_down(bx,.02,1.2)
        if top is not None: hip[1]=top+.075
    SORA_EYE[1]=SORA_HIP[1]+.66; SORA_EYE[0]=SORA_HIP[0]; SORA_EYE[2]=SORA_HIP[2]+.06
    rear=ray_down(-.25,1.05,1.2) or .35
    print('TAXI_SEATS driver',DRIVER_HIP,'sora',SORA_HIP,'eye',SORA_EYE,'rear',round(rear,3))
    # What the runtime needs to find: lamps, glass, wipers, mirror, dials, seats.
    for side in [-1,1]: anchor(f'headlamp_{"l" if side<0 else "r"}',(side*.43,.485,1.74))
    anchor('windscreen_min',(-.485,.875,.49)); anchor('windscreen_max',(.485,1.115,.45))
    for side in [-1,1]: anchor(f'wiper_{"l" if side<0 else "r"}',(side*.23,1.112,.455))
    anchor('dials',(0,.72,.508)); anchor('sora_eye',tuple(SORA_EYE)); anchor('rear_seat',(.25,rear,-1.05))
    mirror_face=(0,1.102,.398)
    anchor('mirror',mirror_face)
    # The rear-view glass, just proud of the car's own mirror plate.
    quad('taxi_mirror_surface',[(-.075,1.071,.397),(.075,1.071,.397),(.075,1.133,.397),(-.075,1.133,.397)],nickel)
    mirror_charms(nickel,bakelite)
    taximeter(nickel,bakelite)
    mourners_leavings(rear)
    driver(bakelite)
    driver_on_scan()
    passenger_on_scan()
    apply_cabin_details(library_material, plain, world_uvs, neck_pos=DRIVER_SCAN_NECK)
    export('ep1_taxi_cabin')

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
    jasmine=plain('M_taxi_jasmine',(.2,.19,.15),.75)
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
    # Under the corner of the car's own mirror, short enough to clear most of the low glass.
    pivot.location=w(CHARM_TOP); pivot.scale=(.62,.62,.62)

# Where the charm's cord is tied: under the near corner of the rear-view mirror.
CHARM_TOP=(.055,1.068,.392)

def taximeter(chrome,black):
    """A mechanical taximeter clamped to the windscreen pillar on Sora's side, its flag
    raised: the fare is still running. Its case is the cabin's old painted steel."""
    case=bpy.data.materials['M_taxi_painted_steel']
    ink=plain('M_taxi_ivory_engraving',(.42,.39,.3),.8)
    rounded('taxi_meter_case',(.5,.78,.42),(.13,.10,.085),case,.012)
    rounded('taxi_meter_window',(.49,.795,.376),(.08,.03,.004),chrome,.003)
    rounded('taxi_meter_tariff_plate',(.49,.757,.376),(.055,.014,.003),ink,.002)
    tube('taxi_meter_bracket',[(.56,.78,.43),(.6,.8,.45)],.007,chrome)
    tube('taxi_meter_flag_arm',[(.44,.79,.42),(.43,.9,.42)],.005,chrome)
    rounded('taxi_meter_flag',(.405,.885,.42),(.06,.035,.005),plain('M_taxi_meter_flag_red',(.26,.035,.025),.65),.004)
    tube('taxi_meter_crank',[(.56,.76,.4),(.585,.745,.39)],.0045,chrome)

def mourners_leavings(rear):
    """What the morning's mourners left on the rear bench: a white lotus bud, a loose
    coil of blessing thread and a bundle of unlit incense on the floor."""
    petal=plain('M_taxi_lotus',(.62,.6,.53),.6); stem=plain('M_taxi_lotus_stem',(.07,.11,.05),.7)
    ellipsoid('taxi_rear_lotus_bud',(.3,rear+.03,-1.12),(.05,.05,.11),petal)
    tube('taxi_rear_lotus_stem',[(.3,rear+.015,-1.07),(.28,rear+.012,-.95),(.22,rear+.01,-.88)],.006,stem)
    thread=plain('M_taxi_blessing_thread',(.62,.6,.55),.9)
    tube('taxi_rear_thread_coil',[(-.2+math.cos(a)*(.05+.004*a),rear+.006+.002*math.sin(a*3),-1.14+math.sin(a)*(.05+.004*a)) for a in [i/6 for i in range(60)]],.0016,thread)
    incense=plain('M_taxi_incense_sticks',(.32,.12,.06),.8)
    for i in range(14):
        dx=(i%5)*.006-.012; dy=(i//5)*.006
        tube('taxi_rear_incense',[(.1+dx,.012+dy,-.8),(.12+dx,.017+dy,-.54)],.0022,incense)
    tube('taxi_rear_incense_band',[(.096+math.cos(a)*.02,.018+math.sin(a)*.016,-.67) for a in [i/16*math.tau for i in range(17)]],.002,plain('M_taxi_incense_paper',(.45,.05,.04),.7))

def character_skin(name,src,photo,relief=1024,image=None,strength=.3):
    mat=plain(name,(.30,.20,.13),.7)
    image=image or bpy.data.images.load(str(src/photo),check_existing=True)
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
    n=mat.node_tree.nodes.new('ShaderNodeNormalMap'); n.inputs['Strength'].default_value=strength
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
        rotate('upperleg01.'+side,SORA_LEGS[0]);rotate('lowerleg01.'+side,SORA_LEGS[1]);rotate('foot.'+side,SORA_LEGS[2])
    bpy.context.view_layer.update()
    baked=bpy.data.meshes.new_from_object(body.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    sx,sy,sz=SORA_HIP
    for v in baked.vertices:v.co=w((sx+v.co.x*.106,sy+(v.co.y-hip.y)*.106,sz+(v.co.z-hip.z)*.106))
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
        t=j/rows;z=sz-.14+t*.20
        row_top=max((v.y for v in posed if abs(v.z-z)<.04),default=sy+.05)
        for i in range(columns+1):
            u=i/columns;x=sx+(u-.5)*.43
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
        z0=min(v.z for v in points)-.015;z1=max(v.z for v in points)+.03
        width=(max(v.x for v in points)-min(v.x for v in points))*.54
        base=max(.008,min(v.y for v in points)-.005)
        shoevs=[];shoefs=[];sections=12;sides=16
        for k in range(sections+1):
            t=k/sections;zz=z0+(z1-z0)*t
            width_at=width*(.75+.35*math.sin(math.pi*t))*(.3 if k in [0,sections] else 1)
            height=.055+.05*math.exp(-((t-.35)/.24)**2)
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

def faded_cotton(name,tint,stains=0.):
    """The suit's denim map washed to grey so its weave, seams and folds carry a period cotton.
    `stains` (0–1) lays sweat tide-marks and ground-in grime over it."""
    image=bpy.data.images.load(str(DRIVER_SRC/'male_casualsuit01_diffuse.png'),check_existing=True)
    if image.size[0]>1024: image.scale(1024,1024)
    px=np.array(image.pixels[:],dtype=np.float32).reshape(image.size[1],image.size[0],4)
    grey=px[...,:3]@np.array([.2126,.7152,.0722]); grey=grey/max(grey.mean(),1e-4)*.5
    rgb=np.clip(grey[...,None]*np.array(tint)*2,0,1)
    if stains>0:
        n=rgb.shape[0]; rng=np.random.default_rng(1936)
        grime=_blur(rng.normal(size=(n,n)),24); grime=(grime-grime.mean())/(grime.std()+1e-6)
        sweat=np.zeros((n,n))
        yy,xx=np.mgrid[:n,:n]
        for _ in range(26):
            cx,cy,r=rng.uniform(0,n),rng.uniform(0,n),rng.uniform(.03,.11)*n
            d=np.hypot(xx-cx,yy-cy)/r
            # Dried sweat: a pale yellowed patch with a darker rim where the salt stopped.
            sweat+=np.clip(1-d,0,1)**.6*.5+np.exp(-((d-1)/.08)**2)*.7
        sweat=np.clip(sweat,0,1.4)
        rgb=rgb*(1-stains*(.1+.07*grime[...,None]).clip(0,.3))
        rgb=rgb*(1-stains*sweat[...,None]*np.array([.1,.14,.3]))
        rgb=np.clip(rgb,0,1)
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

def _pixels(path,size):
    image=bpy.data.images.load(str(path),check_existing=True)
    if image.size[0]!=size: image.scale(size,size)
    return np.array(image.pixels[:],dtype=np.float32).reshape(size,size,4)[...,:3]

def _blur(a,sigma):
    """Gaussian blur of a square H×W(×C) array through the FFT (wraps, which the atlas margins hide)."""
    n=a.shape[0]; fy=np.fft.fftfreq(n)[:,None]; fx=np.fft.rfftfreq(n)[None,:]
    g=np.exp(-2*(math.pi*sigma)**2*(fx*fx+fy*fy))
    if a.ndim==2: return np.fft.irfft2(np.fft.rfft2(a)*g,s=a.shape)
    return np.stack([np.fft.irfft2(np.fft.rfft2(a[...,c])*g,s=a.shape[:2]) for c in range(a.shape[2])],axis=-1)

def _raster(mask,tri,value):
    """Fills one UV triangle (pixel coordinates) of `mask` with max(value)."""
    (x0,y0),(x1,y1),(x2,y2)=tri
    xa=max(0,int(min(x0,x1,x2))); xb=min(mask.shape[1]-1,int(max(x0,x1,x2))+1)
    ya=max(0,int(min(y0,y1,y2))); yb=min(mask.shape[0]-1,int(max(y0,y1,y2))+1)
    if xb<xa or yb<ya: return
    yy,xx=np.mgrid[ya:yb+1,xa:xb+1]+.5
    d=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
    if abs(d)<1e-9: return
    a=((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/d; b=((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/d; c=1-a-b
    inside=(a>=-.02)&(b>=-.02)&(c>=-.02)
    patch=mask[ya:yb+1,xa:xb+1]
    if np.ndim(value)==0: np.maximum(patch,np.where(inside,value,0),out=patch)
    else:
        v=value[0]*a+value[1]*b+value[2]*c
        np.maximum(patch,np.where(inside,v,0),out=patch)

def khmer_driver_skin(verts,faces,faceuv,uvs,joint,size=2048):
    """Fifty-odd years of Phnom Penh sun on the old Asian male skin: the darker
    photo blended in for a Khmer complexion, wrinkles and pores drawn out of the
    photo's own detail, two days' grey stubble along the jaw, sweat-dark creases."""
    light=_pixels(DRIVER_SRC/'old_lightskinned_male_diffuse2.png',size)
    dark=_pixels(DRIVER_SRC/'old_darkskinned_male_diffuse.png',size)
    rgb=light*.58+dark*.42
    # Warm it: sun-browned, a little sallow (linear values).
    rgb*=np.array([.82,.75,.69],dtype=np.float32)
    lum=rgb@np.array([.2126,.7152,.0722],dtype=np.float32)
    # Age is mostly contrast in the fine detail: deepen the creases the photos already hold.
    detail=lum-_blur(lum,5)
    rgb*=np.clip(1+detail[...,None]/np.maximum(lum[...,None],1e-3)*1.4,.55,1.5)
    # Region masks are drawn in UV space from where each face sits on the head.
    chin=joint('jaw____tail'); hinge=joint('jaw____head'); mouth=(joint('oris01____head')+joint('oris05____head'))/2
    eyes=(joint('eye.L____head')+joint('eye.R____head'))/2
    head=joint('head____head'); crown=joint('head____tail')
    stubble=np.zeros((size,size),dtype=np.float32); creases=np.zeros((size,size),dtype=np.float32)
    weather=np.zeros((size,size),dtype=np.float32)
    span=eyes.y-chin.y
    for f,uvf in zip(faces,faceuv):
        c=sum((verts[i] for i in f),Vector())/len(f)
        tri=[(uvs[k][0]*size,uvs[k][1]*size) for k in uvf]  # Blender rows run bottom-up, like V
        if chin.y-span*.9<c.y<crown.y-span*.25:
            # The whole face and neck front catch the sun; the top of the scalp is hair.
            weather_amount=1.0 if c.z>hinge.z-span*.15 else .5
            for k in range(1,len(tri)-1): _raster(weather,(tri[0],tri[k],tri[k+1]),weather_amount)
        front=c.z>hinge.z-span*.05
        below_nose=c.y<mouth.y+span*.2
        above_neck=c.y>chin.y-span*.16
        lips=abs(c.x-mouth.x)<span*.19 and abs(c.y-mouth.y)<span*.075 and c.z>mouth.z-span*.15
        if front and below_nose and above_neck and not lips:
            # Thickest on the chin and upper lip, thinning up the cheeks towards the ears.
            amount=float(np.clip(1.2-max(0.,c.y-mouth.y)/(span*.25)-max(0.,abs(c.x)-span*.35)/(span*.5),.25,1))
            for k in range(1,len(tri)-1): _raster(stubble,(tri[0],tri[k],tri[k+1]),amount)
        # Nasolabial folds and the corners of the mouth hold sweat and grime.
        if front and abs(abs(c.x-mouth.x)-span*.2)<span*.08 and mouth.y-span*.12<c.y<mouth.y+span*.32:
            for k in range(1,len(tri)-1): _raster(creases,(tri[0],tri[k],tri[k+1]),1.0)
    stubble=_blur(stubble,6); creases=_blur(creases,8); weather=_blur(weather,10)
    rng=np.random.default_rng(1934)
    # Short grey-black hairs: a dense speckle, darker where the shadow of the beard is.
    hairs=(rng.random((size,size))<.24).astype(np.float32)
    hairs=np.maximum(hairs,_blur(hairs,.6)*1.8)
    grey=rng.random((size,size))<.45
    hair_colour=np.where(grey[...,None],np.array([.30,.29,.27],dtype=np.float32),np.array([.018,.015,.013],dtype=np.float32))
    shadow=np.clip(stubble,0,1)[...,None]
    rgb=rgb*(1-shadow*.2)
    k=np.clip(stubble*hairs*.7,0,1)[...,None]
    rgb=rgb*(1-k)+hair_colour*k
    # Sun-darkened, blotchy where the face and neck were never covered.
    blotch=_blur(rng.normal(size=(size,size)).astype(np.float32),18)
    blotch=blotch/(blotch.std()+1e-6)
    rgb*=(1-weather[...,None]*(.1+.06*blotch[...,None])*np.array([.6,.9,1.15],dtype=np.float32))
    rgb*=(1-creases[...,None]*.22)
    rgb=np.clip(rgb,0,1).astype(np.float32)
    out=bpy.data.images.new('T_taxi_driver_skin_BC',width=size,height=size,alpha=True)
    out.pixels.foreach_set(np.concatenate([rgb,np.ones((size,size,1),dtype=np.float32)],axis=-1).ravel())
    out.filepath_raw=str(TEX/'T_taxi_driver_skin_BC.png'); out.file_format='PNG'; out.save()
    return out

def krama_material():
    """A faded red-and-white chequered krama, soft from a thousand washes."""
    n=256; rng=np.random.default_rng(1932)
    yy,xx=np.mgrid[:n,:n]
    check=16
    a=(xx//check)%2; b=(yy//check)%2
    red=np.array([.30,.035,.03]); white=np.array([.62,.57,.48]); pink=(red+white)/2
    rgb=np.where((a&b)[...,None]==1,red,np.where((a^b)[...,None]==1,pink,white))
    # The weave: fine warp and weft lines and slubs in the thread.
    weave=.92+.08*np.sin(xx*math.pi/1.5)*np.sin(yy*math.pi/1.5)+rng.normal(0,.035,(n,n))
    rgb=rgb*weave[...,None]*(1-.18*_blur(rng.random((n,n)),10)[...,None])
    img=bpy.data.images.new('T_taxi_driver_krama_BC',width=n,height=n,alpha=True)
    img.pixels.foreach_set(np.concatenate([np.clip(rgb,0,1),np.ones((n,n,1))],axis=-1).astype(np.float32).ravel())
    img.filepath_raw=str(TEX/'T_taxi_driver_krama_BC.png'); img.file_format='PNG'; img.save()
    mat=plain('M_taxi_driver_krama',(1,1,1),.92); nodes=mat.node_tree.nodes
    t=nodes.new('ShaderNodeTexImage'); t.image=img
    mat.node_tree.links.new(t.outputs['Color'],nodes['Principled BSDF'].inputs['Base Color'])
    mat.use_backface_culling=False
    return mat

def krama(surface_points,joint,rig):
    """A krama wound once round his neck, both ends hanging down the shirt front.
    Built at rest in MakeHuman space (decimetres) over the skin and shirt
    (`surface_points`: position, outward normal, bone weights) and weighted from
    the nearest of them, so the pose and every glance carry it."""
    from mathutils.kdtree import KDTree
    tree=KDTree(len(surface_points))
    for k,(co,_,_) in enumerate(surface_points): tree.insert(co,k)
    tree.balance()
    def surface(p,lift):
        _,k,_=tree.find(p); co,nrm,_=surface_points[k]; return co+nrm*lift, nrm
    base=joint('neck01____head'); top=joint('neck02____head'); centre=base.lerp(top,.15)
    ring=[]; steps=28
    for s in range(steps):
        a=s/steps*math.tau
        p=centre+Vector((math.sin(a)*.9,-.2*max(0.,math.cos(a))**2,math.cos(a)*.9))
        q,_=surface(p,.1); q.y=p.y; ring.append(q)
    # Smooth the wound band so it reads as cloth rather than a cast of the neck.
    for _ in range(3): ring=[(ring[s-1]+ring[s]*2+ring[(s+1)%steps])/4 for s in range(steps)]
    vs=[]; fs=[]; uvs=[]
    def sweep(path,closed,section,width,thick,ustart):
        start=len(vs); sides=12
        for s,p in enumerate(path):
            nxt=path[(s+1)%len(path)] if closed or s+1<len(path) else p+(p-path[s-1])
            prv=path[s-1] if closed or s>0 else p-(nxt-p)
            tangent=(nxt-prv).normalized()
            out,across=section(p,tangent)
            for k in range(sides):
                b=k/sides*math.tau
                vs.append(p+out*math.cos(b)*thick+across*math.sin(b)*width)
                uvs.append((ustart+s/len(path)*6,k/sides))
        rows=len(path) if closed else len(path)-1
        for s in range(rows):
            for k in range(sides):
                a=start+s*sides+k; b=start+((s+1)%len(path))*sides+k
                fs.append((a,start+s*sides+(k+1)%sides,start+((s+1)%len(path))*sides+(k+1)%sides,b))
    def band_section(p,tangent):
        out=(p-centre); out.y=0; out.normalize()
        return out, Vector((0,1,0))
    sweep(ring,True,band_section,.2,.075,0)
    # Both ends tucked under the front of the band and falling down the chest, one longer.
    for side,length in [(-1,7),(1,5)]:
        path=[]
        for s in range(length):
            p=Vector((side*.3+side*.03*s,centre.y-.24-s*.36,0))
            p.z=max(v.z for v in ring)+.6
            q,_=surface(p,.12); path.append(q)
        for _ in range(2): path=[path[0]]+[(path[s-1]+path[s]*2+path[s+1])/4 for s in range(1,len(path)-1)]+[path[-1]]
        def tail_section(p,tangent):
            _,nrm=surface(p,0); across=tangent.cross(nrm).normalized()
            return nrm, across
        sweep(path,False,tail_section,.36,.025,.5+side)
    m=bpy.data.meshes.new('taxi_driver_krama'); m.from_pydata(vs,[],fs); m.update()
    o=bpy.data.objects.new('taxi_driver_krama',m); bpy.context.collection.objects.link(o)
    layer=m.uv_layers.new(name='UVMap')
    for poly in m.polygons:
        poly.use_smooth=True
        for li,vi in zip(poly.loop_indices,poly.vertices): layer.data[li].uv=uvs[vi]
    groups={}
    for vi,v in enumerate(vs):
        _,k,_=tree.find(v)
        for bone,weight in surface_points[k][2].items():
            g=groups.get(bone) or groups.setdefault(bone,o.vertex_groups.new(name=bone))
            g.add([vi],weight,'ADD')
    mod=o.modifiers.new('Seated anatomical driving pose','ARMATURE'); mod.object=rig
    return o

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
    # Lean and wiry from years of heat and work: fully old Asian proportions, below average weight.
    for name,weight in [('asian-male-old.target',1.0),('universal-male-old-averagemuscle-averageweight.target',.4),('universal-male-old-averagemuscle-minweight.target',.6)]:
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
    for name,stem in [('hair','short04'),('brows','eyebrow002'),('lashes','eyelashes01'),('eyes','high-poly'),('suit','male_casualsuit01')]:
        refs,scales,_=suit if stem=='male_casualsuit01' else read_mhclo(DRIVER_SRC/(stem+'.mhclo'))
        coords=fit_proxy(refs,scales,verts)
        proxies[name]=(proxy_object('taxi_driver_'+name,coords,DRIVER_SRC/(stem+'.obj'),refs,bone_weights,rig),refs,scales)
    def rotate(name,axis,degrees):
        bone=rig.pose.bones.get(name)
        if bone is None: return
        r=bone.bone.matrix_local.to_quaternion(); bone.rotation_mode='QUATERNION'; bone.rotation_quaternion=bone.rotation_quaternion @ (r.inverted() @ Quaternion(Vector(axis),math.radians(degrees)) @ r)
    for side,sign in [('L',-1),('R',1)]:
        rotate('upperleg01.'+side,(1,0,0),DRIVER_LEGS[0]); rotate('lowerleg01.'+side,(1,0,0),DRIVER_LEGS[1])
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
    hx,hy,hz=DRIVER_HIP
    def to_mh(p): return Vector(((p[0]-hx)/.1, hip_ref.y+(p[1]-hy)/.115, (p[2]-hz)/.1))
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
    def place(co): return w((hx+co.x*.10,hy+(co.y-hip.y)*.115,hz+co.z*.10))
    def posed(obj):
        bpy.context.view_layer.update()
        ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        return [place(v.co) for v in ev.data.vertices]
    points=[(verts[i].copy(),body.data.vertices[k].normal.copy(),bone_weights.get(i,{})) for k,i in enumerate(used)]
    suit_obj,suit_refs,_=proxies['suit']
    for k,v in enumerate(suit_obj.data.vertices):
        (i,j,l),(a,b,c),_=suit_refs[k]
        mixed={}
        for ref,share in ((i,a),(j,b),(l,c)):
            for bone,weight in bone_weights.get(ref,{}).items(): mixed[bone]=mixed.get(bone,0)+weight*share
        points.append((v.co.copy(),v.normal.copy(),mixed))
    proxies['krama']=(krama(points,joint,rig),None,None)
    driven=[body]+[proxies[n][0] for n in ['hair','brows','lashes','eyes','suit','krama']]
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
    # Where his neck meets his shoulders, for setting the head on the scanned body.
    global DRIVER_NECK
    DRIVER_NECK=Vector(place(rig.pose.bones['neck01'].head))
    baked=bake(body)
    skin=character_skin('M_taxi_driver_skin',src,None,image=khmer_driver_skin(verts,faces,faceuv,uvs,joint),strength=.6)
    baked.materials.append(skin)
    for poly in baked.polygons: poly.use_smooth=True
    for name in ['hair','brows','eyes','suit','lashes','krama']: bake(proxies[name][0])
    proxies['krama'][0].data.materials.append(krama_material())
    proxies['hair'][0].data.materials.append(proxy_material('M_taxi_driver_hair','short04_diffuse.png',.74,clip=True,tint=(.3,.29,.275)))
    proxies['brows'][0].data.materials.append(proxy_material('M_taxi_driver_brows','eyebrow002.png',.7,clip=True,tint=(.35,.3,.27)))
    proxies['lashes'][0].data.materials.append(proxy_material('M_taxi_driver_lashes','eyelashes01.png',.7,clip=True))
    proxies['eyes'][0].data.materials.append(proxy_material('M_taxi_driver_eye','brown_eye.png',.12,tint=(.82,.78,.72)))
    # Washed cotton shirt over faded dark trousers, split at his waist.
    shirt=faded_cotton('M_taxi_driver_cotton',(.6,.56,.46),stains=1); trousers=faded_cotton('M_taxi_driver_trousers',(.13,.13,.12),stains=.6)
    suit_mesh=proxies['suit'][0].data; suit_mesh.materials.append(shirt); suit_mesh.materials.append(trousers)
    waist=place(Vector((0,hip.y+1.0,0))).z
    for poly in suit_mesh.polygons:
        poly.material_index=0 if sum(suit_mesh.vertices[i].co.z for i in poly.vertices)/len(poly.vertices)>waist else 1
    def world(v): return Vector((hx+v.x*.10,hy+(v.y-hip.y)*.115,hz+v.z*.10))
    for target in ik_targets: bpy.data.objects.remove(target,do_unlink=True)
    bpy.data.objects.remove(rig,do_unlink=True)
    print('TAXI_DRIVER_HIP',hip[:], 'bounds',min(v.co.z for v in baked.vertices),max(v.co.z for v in baked.vertices))

def road_x(z): return 3.8*math.sin(z*.018)+2.2*math.sin(z*.037)
def road_heading(z): return math.atan(3.8*.018*math.cos(z*.018)+2.2*.037*math.cos(z*.037))
# The Rosalie's floor is the cabin's height 0 and stands .375 m off the road: the whole
# roadside sits this much lower than it was authored (taxiMotion.ts TAXI_GROUND_DROP).
ROAD_DROP=-.27
def road_point(x,y,z):
    a=road_heading(z)
    return (road_x(z)+x*math.cos(a),y+ROAD_DROP,z-x*math.sin(a))

ROAD_HALF_WIDTH=2.8
PLANT_CLEARANCE=ROAD_HALF_WIDTH+.6
# Out of Phnom Penh the road runs on a laterite embankment across flooded paddies; the
# old growth closes over it from FOREST_START (taxiMotion.ts TAXI_PADDY_END/FOREST_START).
PADDY_END=140.0
FOREST_START=150.0
PADDY_WATER=-.88
PADDY_FLOOR=-.98
# Where the Neak Ta's shrine stands at the forest's edge, on Sora's side (the roadside
# figure waits beside it: taxiApparitions.ts TAXI_STANDER).
SHRINE=(6.6,157.5)

def open_land(z):
    """1 across the paddies, 0 under the forest, eased between."""
    t=min(1.,max(0.,(z-PADDY_END)/(FOREST_START-PADDY_END)))
    return 1-t*t*(3-2*t)

def embankment(x):
    """The raised road's cross-section over the paddies: shoulders, then a slope to the fields."""
    a=abs(x)
    if a<3.3: return -.2
    if a>5.6: return PADDY_FLOOR
    t=(a-3.3)/2.3
    return -.2+(PADDY_FLOOR+.2)*(1-math.cos(t*math.pi))/2

def road_lateral(x,z):
    # Nearest centreline parameter, including the normal offset around bends.
    t=np.array(z,copy=True)
    for _ in range(5):
        centre=3.8*np.sin(t*.018)+2.2*np.sin(t*.037)
        slope=3.8*.018*np.cos(t*.018)+2.2*.037*np.cos(t*.037)
        t+=((x-centre)*slope+z-t)/(1+slope*slope)
    angle=np.arctan(3.8*.018*np.cos(t*.018)+2.2*.037*np.cos(t*.037))
    return (x-3.8*np.sin(t*.018)-2.2*np.sin(t*.037))*np.cos(angle)-(z-t)*np.sin(angle)

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
    names=giants+dead+mounds+understory+litter+sedge+small+rite+['bamboo_0','coco_0','coco_2','palm_0','neakta_shrine','neakta_stone_watch']
    templates={name:objects.get(name) for name in names}
    missing=[name for name,obj in templates.items() if obj is None]
    if missing: print('TAXI_MISSING_TEMPLATES',missing)
    mats={m.name:m for m in bpy.data.materials}
    scene=bpy.data.scenes.new('Taxi_monsson_road'); bpy.context.window.scene=scene
    rng=np.random.default_rng(2008)
    plant_vertices={}
    def plant(name,offset,z,scale=1,yaw=None,label=None,clear=PLANT_CLEARANCE,lift=-.12,ground=False,anywhere=False):
        src=templates.get(name)
        if not src: return None
        # The forest's ragged edge: nothing of it grows out on the paddies.
        if not anywhere and z<FOREST_START+3.5*math.sin(offset*.23+z*.05): return None
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
    # Old growth closes both sides as Episode 2's forest does: rank after rank of tall
    # giants, trunks behind trunks behind trunks, with only a little young growth, the odd
    # sugar palm and dead snag under them, and almost no bamboo. Past the last modelled
    # rank the runtime's far tree cards (taxiFarForest.ts) carry the forest on to the haze.
    tallest=giants[len(giants)//2:]
    for side in [-1,1]:
        z=-24+float(rng.random()*6)
        while z<510:
            kind=str(rng.choice(tallest)) if rng.random()<.6 else str(rng.choice(giants))
            roll=rng.random()
            if roll<.05: kind='palm_0'
            elif roll<.11: kind=str(rng.choice(dead))
            plant(kind,side*float(rng.uniform(4.2,9.0)),z,float(rng.uniform(.85,1.3) if kind in giants else rng.uniform(.85,1.15)))
            z+=float(rng.uniform(3.2,5.4))
        # A second rank of full giants close behind the first, offset so the gaps never line up.
        z=-22+float(rng.random()*5)
        while z<510:
            plant(str(rng.choice(tallest)),side*float(rng.uniform(9.5,14)),z,float(rng.uniform(.9,1.3)))
            z+=float(rng.uniform(3.8,6.0))
        z=-24+float(rng.random()*5)
        while z<510:
            # Young growth under the giants: saplings, snags, sugar palms; bamboo only rarely.
            roll=rng.random()
            kind='bamboo_0' if roll<.02 else 'palm_0' if roll<.16 else str(rng.choice(dead)) if roll<.45 else str(rng.choice(giants))
            scale=float(rng.uniform(.22,.4) if kind in giants else rng.uniform(.5,.85))
            plant(kind,side*float(rng.uniform(3.6,6.5)),z,scale)
            z+=float(rng.uniform(4.5,7.5))
        # Lighter crowns for the deeper ranks, ever taller towards the back.
        # (Past 29 m the far tree cards carry the forest on: no modelled rank there.)
        for near,far,step,lo,hi in [(14,21,(4.0,6.0),.95,1.3),(21,29,(5.0,7.5),1.0,1.4)]:
            z=-24+float(rng.random()*5)
            while z<510:
                plant('far_'+str(rng.choice(giants[-3:-1])),side*float(rng.uniform(near,far)),z,float(rng.uniform(lo,hi)))
                z+=float(rng.uniform(*step))
        # A continuous understory and leaf-litter floor beyond the shoulder, as under the village canopy.
        z=-24+float(rng.random()*3)
        while z<510:
            plant(str(rng.choice(understory)),side*float(rng.uniform(3.8,7.5)),z,float(rng.uniform(.9,1.25)))
            if rng.random()<.6: plant(str(rng.choice(litter)),side*float(rng.uniform(4,9)),z+float(rng.uniform(-2,2)),1.0)
            z+=float(rng.uniform(3.2,4.6))
        z=-24+float(rng.random()*3)
        while z<510:
            plant(str(rng.choice(sedge)),side*float(rng.uniform(3.6,4.4)),z,float(rng.uniform(.7,1.0)))
            z+=float(rng.uniform(5,8))
        for i in range(420):
            z=float(rng.uniform(-24,510))
            plant(str(rng.choice(small)),side*float(rng.uniform(3.4,9)),z,float(rng.uniform(.65,1.35)))
        for i in range(26):
            z=float(rng.uniform(-20,505))
            plant(str(rng.choice(mounds)),side*float(rng.uniform(5,12)),z,float(rng.uniform(.7,1.1)))
        z=-24+float(rng.random()*4)
        while z<510:
            plant('fern_02_a.001',side*float(rng.uniform(3.5,4.2)),z,float(rng.uniform(.4,.72)))
            z+=float(rng.uniform(3.0,6.0))
    road_surface(mats,rng)
    telegraph_line(mats,rng)
    paddies(mats,rng)
    countryside(mats,rng,plant)
    # The Neak Ta's shrine where the trees begin, under a giant, with the village's own
    # stone watcher, offerings and incense (all advisor review).
    sx,sz=SHRINE
    plant(tallest[-1],sx+5.5,sz+2.5,1.25,anywhere=True,clear=None,label='shrine_tree')
    shrine=[plant('neakta_shrine',sx,sz,1,yaw=-math.pi/2,clear=None,label='roadside_neakta_shrine',ground=True,lift=-.22,anywhere=True),
            plant('neakta_stone_watch',sx-1.2,sz-1.9,1,yaw=-math.pi/2+.3,clear=None,label='roadside_neakta_stone',ground=True,lift=-.22,anywhere=True)]
    # The village's shrine and stone are sculpted for its yard; by the road they are seen
    # for a few seconds in a candle's light: a third of their faces is plenty (applied on export).
    for obj in shrine:
        if obj:
            obj.data=obj.data.copy()
            mod=obj.modifiers.new('roadside LOD','DECIMATE'); mod.ratio=.33; mod.use_collapse_triangulate=True
    plant('ground_offering_0',sx-1.5,sz+.6,1,yaw=0,clear=None,label='roadside_neakta_offering',ground=True,lift=-.2,anywhere=True)
    plant(family_pick(templates,'altar_incense'),sx-1.6,sz-.4,1,yaw=0,clear=None,label='roadside_neakta_incense',ground=True,lift=-.18,anywhere=True)
    plant('old_flag_2',sx-1.0,sz+2.4,1,yaw=.2,clear=None,label='roadside_neakta_flag',ground=True,lift=-.25,anywhere=True)
    # Roadside omens in the forest: rotting funeral flags, threads strung through the
    # trees, incense left at the foot of trunks and the Ting Mong guarding the village approach.
    for z,side,flag in [(171,1,'old_flag_2'),(302,1,'old_flag_1'),(418,-1,'old_flag_3'),(461,1,'old_flag_0')]:
        plant(flag,side*3.9,z,1,yaw=float(rng.uniform(-.4,.4)),clear=3.2,label='omen_'+flag+'_'+str(z),ground=True,lift=-.25)
    for z,side,thread in [(176,-1,'path_threads_0'),(364,1,'path_threads_1'),(489,-1,'path_threads_0')]:
        plant(thread,side*4.6,z,1,yaw=math.pi/2,clear=None,label='omen_'+thread+'_'+str(z),lift=.2)
    for z,side in [(205,1),(268,-1),(338,-1),(402,1)]:
        plant(family_pick(templates,'altar_incense'),side*3.75,z,1,yaw=0,clear=None,label='omen_incense_'+str(z),lift=-.16,ground=True)
        plant(family_pick(templates,'step_candle'),side*3.85,z+.3,1,yaw=0,clear=None,label='omen_candle_'+str(z),lift=-.16,ground=True)
    for z,side,guard in [(474,-1,'tingmong_0'),(477,1,'tingmong_1')]:
        plant(guard,side*4.1,z,1,yaw=math.pi if side>0 else 0,clear=3.4,label='guardian_'+guard,ground=True,lift=-.22)
    # French colonial kilometre stones on the shoulder.
    for z,side in [(38,-1),(238,-1),(438,-1)]:
        plant('milestone',side*3.2,z,1,yaw=math.pi/2,clear=None,label='milestone_'+str(z),lift=-.2,ground=True,anywhere=True)
    apply_roadside_details(mats,rng,w,road_point,road_heading,PADDY_WATER,library_material,plain,world_uvs,full_gltf_group,import_glb,plant)
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

def road_surface(mats,rng):
    """A laterite cart track: two deep wheel ruts with mud pushed up beside them, a grassy
    centre hump, a crumbling edge into flooded ditches, gravel, and pools in the ruts."""
    floor=mats['M_wet_forest_floor']; mud=mats['M_wet_mud']
    columns=[-70,-52,-40,-32,-26,-20,-15,-11,-8.5,-6.5,-5.2,-4.4,-3.9,-3.65,-3.45,-3.3,-3.15,-3.0,-2.85,-2.6,-2.0,-1.0]
    columns=columns+[0]+[-x for x in reversed(columns)]
    def ditch(x): return .17*math.exp(-((abs(x)-3.3)/.34)**2)
    vs=[];fs=[];rows=540
    for i in range(rows+1):
        z=-28+i; o=open_land(z)
        for x in columns:
            forest=-.22+.028*math.sin(x*.7+z*.3)+.018*math.sin(z*.8+x*2)-ditch(x)
            # Over the paddies: the embankment's slopes down to the field mud under the flood.
            field=embankment(x)+.012*math.sin(x*1.3+z*.7)
            vs.append(road_point(x,forest*(1-o)+field*o,z))
    n=len(columns)
    for i in range(rows):
        for j in range(n-1): a=i*n+j; fs.append((a,a+n,a+n+1,a+1))
    smooth(mesh('taxi_road_ground',vs,fs,floor))
    # Laterite on the embankment across the paddies, forest mud under the trees.
    laterite=library_material('red_laterite_soil_stones','M_taxi_laterite',tint=(.6,.48,.4),tile=1.8)
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
    split=int((FOREST_START-4+28)/.5)
    for name,material,r0,r1 in [('taxi_laterite_track',laterite,0,split),('taxi_muddy_track',mud,split,rows)]:
        fs=[]
        for i in range(r0,r1):
            for j in range(steps): a=(i-r0)*(steps+1)+j; fs.append((a,a+steps+1,a+steps+2,a+1))
        smooth(mesh(name,vs[r0*(steps+1):(r1+1)*(steps+1)],fs,material))
    puddle=mats['M_puddle']
    ditch_water=puddle.copy(); ditch_water.name='M_ditch_water'
    puddle.blend_method='BLEND'
    if puddle.node_tree and 'Principled BSDF' in puddle.node_tree.nodes:
        pbs=puddle.node_tree.nodes['Principled BSDF']
        pbs.inputs['Base Color'].default_value=(0.011,0.014,0.017,1.0)
        pbs.inputs['Roughness'].default_value=0.036
        pbs.inputs['Alpha'].default_value=0.92
    ditch_water.blend_method='OPAQUE'
    if ditch_water.node_tree and 'Principled BSDF' in ditch_water.node_tree.nodes:
        dbs=ditch_water.node_tree.nodes['Principled BSDF']
        dbs.inputs['Base Color'].default_value=(0.018,0.021,0.024,1.0)
        dbs.inputs['Roughness'].default_value=0.055
        dbs.inputs['Alpha'].default_value=1.0
    def water_patch(x,z,radius,long,name='taxi_rut_water',y=-.058,limit=ROAD_HALF_WIDTH-.08):
        # Shallow standing water lies above the road crown, never buried beneath mud.
        # Radial UVs ((0.5, 0.5) at center -> rim on r=0.5 circle) let runtime feather puddle edges into wet mud!
        vs=[road_point(x,y,z)]; count=24
        angles=[]
        for j in range(count):
            a=j/count*math.tau; r=radius*(.90+.07*math.sin(j*2.7)+.03*math.sin(j*4.1))
            lateral=max(-limit,min(limit,x+math.cos(a)*r)) if limit else x+math.cos(a)*r
            vs.append(road_point(lateral,y,z+math.sin(a)*long))
            angles.append(a)
        o=mesh(name,vs,[(0,(j+1)%count+1,j+1) for j in range(count)],puddle)
        uvl=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
        for p in o.data.polygons:
            for li in p.loop_indices:
                vi=o.data.loops[li].vertex_index
                if vi==0: uvl.data[li].uv=(0.5,0.5)
                else:
                    a=angles[vi-1]
                    uvl.data[li].uv=(0.5+0.49*math.cos(a),0.5+0.49*math.sin(a))
    for i in range(170):
        x=float(rng.choice([-1,1]))*.74+float(rng.normal(0,.22)); z=-24+float(rng.random()*532)
        water_patch(x,z,float(rng.uniform(.4,.95)),float(rng.uniform(.8,2.7)))
    for i in range(48):
        water_patch(float(rng.uniform(-.15,.15)),-22+i*11.1+float(rng.uniform(-2,2)),float(rng.uniform(2.1,2.65)),float(rng.uniform(3.5,6.2)))
    # Run-off standing in the ditches, broken where the bank has slumped.
    for side in [-1,1]:
        z=FOREST_START+2
        while z<510:
            length=float(rng.uniform(5,22)); r=float(rng.uniform(.18,.27))
            vs=[];fs=[]
            for k in range(int(length)+1):
                zz=z+k; wobble=.05*math.sin(zz*.9+side)
                vs+= [road_point(side*3.3-r+wobble,-.31,zz),road_point(side*3.3+r+wobble,-.31,zz)]
            for k in range(int(length)): a=k*2; fs.append((a,a+2,a+3,a+1))
            mesh('taxi_ditch_water',vs,fs,ditch_water)
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
        h=float(rng.uniform(.035,.095)); lean=float(rng.uniform(0,math.tau)); bend=float(rng.uniform(.015,.048))
        base=-.13+.055*(1-(x/ROAD_HALF_WIDTH)**2)+math.exp(-((abs(x)-1.0)/.12)**2)*.022-.008
        width=float(rng.uniform(.0035,.0065))
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

SCANS=ROOT/'art-source/library/scans'
PALM_CARD=TEX/'T_taxi_palm_card.png'
# The palm card's frame: the scanned palm's height fills the image's height (metres).
PALM_CARD_SIZE=(7.25,14.5)

def full_gltf_group():
    """The glTF importer reuses any "glTF Material Output" group and expects all of its
    sockets; the village file's (and kit's) has only Occlusion. Give it the rest."""
    from io_scene_gltf2.blender.com.material_helpers import create_settings_group, get_gltf_node_name
    name=get_gltf_node_name(); group=bpy.data.node_groups.get(name)
    if group is None: create_settings_group(name); return
    full=create_settings_group('glTF full sockets')
    have={item.name for item in group.interface.items_tree}
    for item in full.interface.items_tree:
        if item.item_type=='SOCKET' and item.in_out=='INPUT' and item.name not in have:
            group.interface.new_socket(item.name,in_out='INPUT',socket_type=item.socket_type)
    bpy.data.node_groups.remove(full)

def import_scan(key):
    """A prepared scan (taxi_scans.py) as hidden templates: upright, life size, credited."""
    path=SCANS/f'{key}.glb'
    if not path.exists():
        print('TAXI_SCAN_MISSING',key); return []
    full_gltf_group()
    objs=import_glb(path)
    for o in objs: o.hide_render=True
    return objs

def place_scan(objs,label,lateral,z,yaw=0.,scale=1.,y=0.):
    """Linked copies of a scan's parts, stood at a point beside the road."""
    at=Matrix.Translation(w(road_point(lateral,y,z)))@Matrix.Rotation(yaw-road_heading(z),4,'Z')@Matrix.Scale(scale,4)
    out=[]
    for o in objs:
        c=o.copy(); c.data=o.data; bpy.context.scene.collection.objects.link(c)
        c.matrix_world=at@o.matrix_world; c.hide_render=False; c.name='taxi_road_'+label; out.append(c)
    return out

def palm_card():
    """The scanned palm drawn once, side on, for the far palms across the paddies."""
    if PALM_CARD.exists(): return
    bpy.ops.wm.read_factory_settings(use_empty=True)
    full_gltf_group()
    import_glb(SCANS/'taxi_fan_palm.glb')
    sc=bpy.context.scene
    sc.render.engine='BLENDER_EEVEE'; sc.render.film_transparent=True
    sc.render.resolution_x,sc.render.resolution_y=512,1024
    sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'
    world=bpy.data.worlds.new('card'); sc.world=world; world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.3,.32,.34,1)
    sun=bpy.data.objects.new('sun',bpy.data.lights.new('sun','SUN')); sun.data.energy=2.2
    sun.rotation_euler=(.9,0,.4); sc.collection.objects.link(sun)
    cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
    cam.data.type='ORTHO'; cam.data.ortho_scale=PALM_CARD_SIZE[1]
    cam.location=(0,-40,PALM_CARD_SIZE[1]/2); cam.rotation_euler=(math.pi/2,0,0)
    sc.render.filepath=str(PALM_CARD); bpy.ops.render.render(write_still=True)
    print('TAXI_PALM_CARD',PALM_CARD)

def dike(points,material,name,width=.8,top=.34,rise=.2):
    """A low earth dike between fields: a trapezoid ribbon along (lateral, z) points."""
    vs=[];fs=[]
    for k,(lat,z) in enumerate(points):
        a=points[min(k+1,len(points)-1)]; b=points[max(k-1,0)]
        dl,dz=a[0]-b[0],a[1]-b[1]; length=math.hypot(dl,dz) or 1
        nl,nz=-dz/length,dl/length
        crest=PADDY_WATER+rise+.03*math.sin(z*.9+lat*.7)
        for off,y in [(-width/2,PADDY_FLOOR),(-top/2,crest),(top/2,crest),(width/2,PADDY_FLOOR)]:
            vs.append(road_point(lat+nl*off,y,z+nz*off))
    for k in range(len(points)-1):
        for j in range(3):
            a=k*4+j; fs.append((a,a+1,a+5,a+4))
    return mesh(name,vs,fs,material)

def blades(tufts,material,name,frame=None):
    """Grass and rice as thin blades: (lateral, base y, z, height, count, splay) per tuft,
    beside the road, or in a piece's own frame (x across, z along) when `frame` is given."""
    frame=frame or road_point
    rng=np.random.default_rng(len(tufts)+17)
    vs=[];fs=[]
    for lat,y,z,h,count,splay in tufts:
        for _ in range(count):
            a=float(rng.uniform(0,math.tau)); lean=float(rng.uniform(.15,1.))*splay
            width=float(rng.uniform(.006,.011)); hh=h*float(rng.uniform(.75,1.15))
            ox,oz=float(rng.normal(0,.02)),float(rng.normal(0,.02))
            root=Vector(frame(lat+ox,y,z+oz)); tip=Vector(frame(lat+ox+math.cos(a)*lean*hh,y+hh,z+oz+math.sin(a)*lean*hh))
            across=Vector((math.cos(a+1.57)*width,0,math.sin(a+1.57)*width))
            k=len(vs); vs+=[tuple(root-across),tuple(root+across),tuple(tip)]; fs.append((k,k+1,k+2))
    o=mesh(name,vs,fs,material)
    for p in o.data.polygons: p.use_smooth=True
    return o

def paddies(mats,rng):
    """Flooded rice fields either side of the embankment: the flood's surface, the earth
    dikes that divide it, young rice in rows in most fields and grass along the dikes."""
    water=plain('M_taxi_paddy_water',(.028,.038,.045),.05)
    earth=mats['M_wet_forest_floor'].copy(); earth.name='M_taxi_dike_earth'; earth.use_backface_culling=False
    rice=mats['M_forest_grass'].copy(); rice.name='M_taxi_rice'; rice.use_backface_culling=False
    grass=mats['M_forest_grass']
    reach=150.; z0,z1=-30.,PADDY_END+12
    # Six 4 m pieces of a row of young rice: a clump every 30 cm, each a few blades.
    rows=[]
    for v in range(6):
        tufts=[]; zz=float(rng.uniform(0,.15)); stage=float(rng.uniform(.8,1.15))
        while zz<4.:
            tufts.append((float(rng.normal(0,.03)),PADDY_WATER-.03,zz,.46*stage,4,.3)); zz+=float(rng.uniform(.26,.36))
        rows.append(blades(tufts,rice,'taxi_paddy_rice_row',frame=lambda x,y,z:(x,y,z)))
    for side in [-1,1]:
        z=z0
        while z<z1:
            vs=[];fs=[];cols=[4.4,9,18,35,65,105,reach]; n=len(cols)
            for k in range(7):
                zz=min(z1,z+k*5)
                for lat in cols: vs.append(road_point(side*lat,PADDY_WATER,zz))
            for k in range(6):
                for j in range(n-1):
                    a=k*n+j; fs.append((a,a+n,a+n+1,a+1) if side>0 else (a,a+1,a+n+1,a+n))
            mesh('taxi_paddy_water',vs,fs,water)
            z+=30
        # The dikes: long ones parallel to the road, and cross dikes from the embankment out.
        lanes=[5.0]; lat=float(rng.uniform(16,22))
        while lat<reach-8: lanes.append(lat); lat+=float(rng.uniform(19,30))
        lanes.append(reach)
        seed=float(rng.uniform(0,6))
        for lat in lanes[1:-1]:
            pts=[(side*(lat+.7*math.sin(zz*.045+seed+lat)),zz) for zz in np.arange(z0,z1,3.)]
            dike(pts,earth,'taxi_paddy_dike')
        cross=[z0]; zz=z0+float(rng.uniform(10,20))
        while zz<z1-6: cross.append(zz); zz+=float(rng.uniform(22,38))
        cross.append(z1)
        for zc in cross[1:-1]:
            pts=[(side*l,zc+.8*math.sin(l*.09+zc)) for l in np.arange(5.0,reach,3.)]
            dike(pts,earth,'taxi_paddy_dike')
        # Fields between them: most near the road planted with young rice in rows, laid as
        # copies of a few 4 m pieces of row so the download carries each blade once.
        dike_grass=[]
        for a,b in zip(lanes,lanes[1:]):
            for zA,zB in zip(cross,cross[1:]):
                if a<60:
                    for zz in np.arange(zA+.6,zB-.4,.45 if a<30 else .9):
                        dike_grass.append((side*(b-.05),PADDY_WATER+.18,float(zz),.22,4,.5))
                if a>20 or rng.random()>.72: continue
                for l in np.arange(a+.5,min(b,24.)-.4,.36):
                    for zz in np.arange(zA+.4,zB-4.3,4.):
                        piece=rows[int(rng.integers(len(rows)))]
                        c=piece.copy(); c.data=piece.data; bpy.context.scene.collection.objects.link(c)
                        c.name='taxi_paddy_rice'
                        c.matrix_world=Matrix.Translation(w(road_point(side*float(l),0,float(zz))))@Matrix.Rotation(-road_heading(float(zz)),4,'Z')
        blades(dike_grass,grass,'taxi_paddy_dike_grass')
    for piece in rows: bpy.data.objects.remove(piece)

def mound(lateral,z,radius,material,name,top=-.42):
    """A raised house plot above the flood: earth sloping into the water."""
    vs=[road_point(lateral,top,z)]; fs=[]; rings=[(radius*.7,top-.02),(radius,PADDY_WATER+.05),(radius*1.25,PADDY_FLOOR)]
    count=24
    for r,y in rings:
        for j in range(count):
            a=j/count*math.tau; wob=1+.08*math.sin(j*2.3)
            vs.append(road_point(lateral+math.cos(a)*r*wob,y,z+math.sin(a)*r*wob))
    for j in range(count): fs.append((0,1+j,1+(j+1)%count))
    for ring in range(len(rings)-1):
        for j in range(count):
            a=1+ring*count+j; b=1+ring*count+(j+1)%count
            fs.append((a,a+count,b+count,b))
    return mesh(name,vs,fs,material)

def countryside(mats,rng,plant):
    """What stands out on the paddies: stilt houses on their plots with banana clumps and a
    lamp in one window, sugar-palm silhouettes on the dikes, and the scanned mud ruts in the
    forest road beyond."""
    earth=bpy.data.materials.get('M_taxi_dike_earth') or mats['M_wet_forest_floor']
    house=import_scan('taxi_stilt_house'); palm=import_scan('taxi_fan_palm')
    banana=import_scan('taxi_banana'); ruts=import_scan('taxi_mud_puddle')
    for lat,z,yaw,lit in [(-27,92,math.pi/2,True),(62,40,-math.pi/2+.3,False),(-78,128,math.pi/2-.2,False)]:
        mound(lat,z,7.5,earth,'taxi_road_house_plot')
        place_scan(house,'stilt_house',lat,z,yaw,1.,-.42)
        if lit:
            # An oil lamp behind the shutters: the runtime hangs a flickering light here.
            lamp=bpy.data.objects.new('taxi_road_anchor_house_lamp',None); bpy.context.scene.collection.objects.link(lamp)
            lamp.location=w(road_point(lat+2.2,2.55,z+.6))
        if lit or lat<-60:
            # The lamp's own flame and glass, seen through the open front from the road.
            glow=plain('M_taxi_oil_lamp_flame',(.9,.6,.3),.5,emission=(1,.55,.22),strength=6 if lit else 3)
            ellipsoid('taxi_road_house_lamp_flame',road_point(lat+2.2,2.3,z+.6),(.07,.12,.07),glow)
        for k in range(5 if lit else 2):
            a=k/5*math.tau+float(rng.uniform(-.3,.3)); r=float(rng.uniform(4.4,6.2))
            place_scan(banana,'banana',lat+math.cos(a)*r,z+math.sin(a)*r,float(rng.uniform(0,math.tau)),float(rng.uniform(.8,1.12)),-.44)
        plant('coco_2',lat+(4.5 if lat<0 else -4.5),z+4,float(rng.uniform(.85,1.05)),clear=None,lift=-.44,anywhere=True,label='house_coconut')
    # Three palms near enough to need their own leaves; the rest stand as cards.
    near=[(15.5,58),(-21,99),(18,121)]
    for lat,z in near:
        place_scan(palm,'sugar_palm',lat,z,float(rng.uniform(0,math.tau)),float(rng.uniform(.95,1.15)),PADDY_WATER+.12)
    card=plain('M_taxi_palm_card',(1,1,1),.8)
    if PALM_CARD.exists():
        nodes=card.node_tree.nodes; links=card.node_tree.links; bs=nodes['Principled BSDF']
        tex=nodes.new('ShaderNodeTexImage'); tex.image=bpy.data.images.load(str(PALM_CARD),check_existing=True)
        links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        cut=nodes.new('ShaderNodeMath'); cut.operation='GREATER_THAN'; cut.inputs[1].default_value=.4
        links.new(tex.outputs['Alpha'],cut.inputs[0]); links.new(cut.outputs[0],bs.inputs['Alpha'])
    card.use_backface_culling=False
    vs=[];fs=[];uv=[];placed=0
    while placed<46:
        side=-1 if rng.random()<.5 else 1; lat=float(rng.uniform(24,145)); z=float(rng.uniform(-25,PADDY_END+4))
        if any(abs(side*lat-a)<14 and abs(z-b)<14 for a,b in near): continue
        for _ in range(1+int(rng.random()*3)):
            l=side*lat+float(rng.normal(0,3)); zz=z+float(rng.normal(0,3)); s=float(rng.uniform(.8,1.25))
            cw,ch=PALM_CARD_SIZE[0]*s/2,PALM_CARD_SIZE[1]*s
            spin=float(rng.uniform(0,math.pi))
            for turn in [spin,spin+math.pi/2]:
                dx,dz=math.cos(turn)*cw,math.sin(turn)*cw; k=len(vs)
                for (ox,oz,y) in [(-dx,-dz,0),(dx,dz,0),(dx,dz,ch),(-dx,-dz,ch)]:
                    vs.append(road_point(l+ox,PADDY_WATER+.1+y,zz+oz))
                fs.append((k,k+1,k+2,k+3)); uv+= [(0,0),(1,0),(1,1),(0,1)]
            placed+=1
    cards=mesh('taxi_road_palm_cards',vs,fs,card,uv=False)
    layer=cards.data.uv_layers.new(name='UVMap')
    for poly in cards.data.polygons:
        for li in poly.loop_indices:
            # mesh() reverses each face: map back to the authored corner order.
            corner=list(reversed(range(4)))[li-poly.loop_start]
            layer.data[li].uv=[(0,0),(1,0),(1,1),(0,1)][corner]
    # The scanned mud ruts, water standing in them, along the forest road.
    z=FOREST_START+6.
    while z<505:
        x=(-1 if rng.random()<.5 else 1)*.74
        crown=-.13+.055*(1-(x/ROAD_HALF_WIDTH)**2)-.07
        place_scan(ruts,'mud_rut',x,z,math.pi/2+float(rng.normal(0,.04)),float(rng.uniform(.85,1.05)),crown-.31)
        z+=float(rng.uniform(26,44))
    for o in house+palm+banana+ruts: bpy.data.objects.remove(o)

# ------------------------------------------------------------ real people
# The driver's body and Sora's legs are Renderpeople photoscans (CC BY, prepared by
# taxi_scans.py), posed here on their own skeletons into the Rosalie's seats. The driver's
# head stays the Khmer driver built above, set into the scanned collar.
DRIVER_NECK=None

def import_rigged(key):
    full_gltf_group()
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SCANS/f'{key}.glb'))
    new=[o for o in bpy.data.objects if o not in before]
    arm=next(o for o in new if o.type=='ARMATURE')
    # The skinned scan, not the importer's joint-display spheres.
    body=max((o for o in new if o.type=='MESH'),key=lambda o:len(o.data.polygons))
    for o in new:
        if o not in (arm,body) and o.type!='EMPTY': bpy.data.objects.remove(o)
    return arm,body

def joint(arm,name):
    bpy.context.view_layer.update()
    return arm.matrix_world@arm.pose.bones[name].head

def turn_bone(arm,name,axis,angle):
    """Turn a pose bone about its head by `angle` around a world axis."""
    bpy.context.view_layer.update()
    pb=arm.pose.bones[name]; inv=arm.matrix_world.inverted().to_3x3()
    R=Matrix.Rotation(angle,4,(inv@Vector(axis)).normalized())
    pb.matrix=Matrix.Translation(pb.head)@R@Matrix.Translation(-pb.head)@pb.matrix
    bpy.context.view_layer.update()

def aim(arm,name,child,target):
    """Turn bone `name` so its child joint lies along the line to a world point."""
    head=joint(arm,name); cur=joint(arm,child)-head; want=Vector(target)-head
    if cur.length<1e-6 or want.length<1e-6: return
    axis,angle=cur.rotation_difference(want).to_axis_angle()
    turn_bone(arm,name,axis,angle)

def reach(arm,upper,lower,hand,wrist,pole):
    """Two-bone arm IK: the elbow bends towards `pole`, the wrist lands at `wrist`."""
    s=joint(arm,upper); a=(joint(arm,lower)-s).length; b=(joint(arm,hand)-joint(arm,lower)).length
    to=Vector(wrist)-s; d=min(to.length,(a+b)*.995); f=to.normalized()
    cosA=max(-1,min(1,(a*a+d*d-b*b)/(2*a*d)))
    p=Vector(pole)-s; perp=(p-f*p.dot(f)).normalized()
    elbow=s+f*a*cosA+perp*a*math.sqrt(1-cosA*cosA)
    aim(arm,upper,lower,elbow); aim(arm,lower,hand,s+f*d)

def knuckles(arm,side):
    """The hand's knuckle line (index to little finger) and its fingers' direction."""
    k1=joint(arm,bone(arm,f'index_01_{side}')); k4=joint(arm,bone(arm,f'pinky_01_{side}'))
    wrist=joint(arm,bone(arm,f'hand_{side}')); mid=joint(arm,bone(arm,f'middle_01_{side}'))
    return (k1-k4).normalized(),(mid-wrist).normalized()

def palm_of(arm,side):
    """Which way the palm faces: flexion closes the fingers towards it."""
    across,d=knuckles(arm,side)
    return (across.cross(d) if side=='r' else d.cross(across)).normalized()

def curl(arm,side,angle_main,angle_thumb):
    """Fingers closed round a rim: each joint flexed about the hand's knuckle line,
    towards the palm (the sense differs between the hands)."""
    across,_=knuckles(arm,side)
    if side=='l': across=-across
    for finger in ['index','middle','ring','pinky']:
        for seg in ['01','02','03']:
            name=next(b.name for b in arm.pose.bones if b.name.startswith(f'{finger}_{seg}_{side}'))
            turn_bone(arm,name,across,angle_main)
    for seg in ['02','03']:
        name=next(b.name for b in arm.pose.bones if b.name.startswith(f'thumb_{seg}_{side}'))
        turn_bone(arm,name,across,angle_thumb)

def bone(arm,prefix):
    return next(b.name for b in arm.pose.bones if b.name.startswith(prefix))

def bake_pose(arm,body):
    """The posed scan as a plain mesh: its skeleton and skin weights go."""
    bpy.context.view_layer.update()
    mats=[slot.material for slot in body.material_slots]
    ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data=bpy.data.meshes.new_from_object(ev); data.transform(body.matrix_world)
    data.materials.clear()
    for m in mats: data.materials.append(m)
    body.modifiers.clear(); body.parent=None; body.matrix_world=Matrix.Identity(4); body.data=data
    body.vertex_groups.clear()
    bpy.data.objects.remove(arm)

def scan_colour(body):
    """Mean base colour per face, sampled from the scan's own map."""
    mat=body.data.materials[0]; px=base_pixels(mat)
    uvl=body.data.uv_layers.active.data; h,wd=px.shape[:2]; out=[]
    for p in body.data.polygons:
        uv=sum((uvl[li].uv for li in p.loop_indices),Vector((0,0)))/len(p.loop_indices)
        out.append(Vector(px[int((uv.y%1)*(h-1)),int((uv.x%1)*(wd-1))][:3]))
    return out

def skin_like(c):
    return c.x>.18 and c.x>c.y*1.06 and c.y>c.z*1.0 and min(c)<.72

def tinted(mat,name,tint):
    """A copy of the scan's material with its colour multiplied (kept as a glTF factor)."""
    m=mat.copy(); m.name=name
    bs=m.node_tree.nodes.get('Principled BSDF')
    for link in list(m.node_tree.links):
        if link.to_socket==bs.inputs['Base Color']:
            mix=m.node_tree.nodes.new('ShaderNodeMix'); mix.data_type='RGBA'; mix.blend_type='MULTIPLY'
            mix.inputs['Factor'].default_value=1; mix.inputs[7].default_value=(*tint,1)
            source=link.from_socket
            m.node_tree.links.new(source,mix.inputs[6]); m.node_tree.links.new(mix.outputs[2],bs.inputs['Base Color'])
            break
    return m

def driver_photo(photo):
    """Eric's photo map recoloured for the driver, per pixel: skin (warm, red over blue) in
    the sun-browned curve of his face; the white shirt (bright, unsaturated) as a plain
    washed cream that keeps only its soft large folds; everything else as photographed."""
    wd,ht=photo.size; px=np.empty(wd*ht*4,np.float32); photo.pixels.foreach_get(px); px=px.reshape(ht,wd,4)
    rgb=px[...,:3]
    lo,hi=rgb.min(-1),rgb.max(-1)
    lin=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    for ch,ys in enumerate([(0,.36,.8),(0,.25,.66),(0,.17,.52)]):
        lin[...,ch]=np.interp(lin[...,ch],(0,.5,1),ys)
    browned=np.where(lin<=.0031308,lin*12.92,1.055*np.power(np.maximum(lin,0),1/2.4)-.055)
    skin=np.clip(((rgb[...,0]-rgb[...,2])-.07)/.06,0,1)*np.clip((rgb[...,0]-rgb[...,1]+.02)/.04,0,1)*np.clip((hi-.12)/.08,0,1)
    shade=soft_shading(photo,20); mean=float(np.median(shade[(lo>.5)&(hi-lo<.08)])) if ((lo>.5)&(hi-lo<.08)).any() else .7
    yy_w,xx_w=np.mgrid[:ht,:wd]
    weave=(0.95+0.05*np.sin(xx_w*1.1)*np.sin(yy_w*1.1)).astype(np.float32)
    cream=np.array((.42,.37,.30),np.float32)*np.clip(shade/mean,.72,1.12)[...,None]*weave[...,None]
    shirt=np.clip((lo-.34)/.12,0,1)*np.clip((.14-(hi-lo))/.05,0,1)
    suit=rgb*np.array((.62,.58,.54),np.float32)
    out=suit*(1-skin[...,None])+browned*skin[...,None]
    out=out*(1-shirt[...,None])+cream*shirt[...,None]
    img=bpy.data.images.new('T_taxi_driver_clothes',wd,ht); img.pixels.foreach_set(np.concatenate([np.clip(out,0,1),np.ones((ht,wd,1),np.float32)],-1).astype(np.float32).ravel()); img.pack()
    return img

def simulate_sleeves(arm,body,rest,kinds):
    """His shirt sleeves as cotton: split from the scan, subdivided, and cloth-simulated in
    Blender while the arms move from the scan's A-pose to the wheel, over a collider just
    inside them. The cotton bunches at the elbow and hangs from the forearm as a real
    sleeve does; the scan's own sleeves were stiff tubes printed with A-pose shadows."""
    sc=bpy.context.scene
    posed={pb.name:pb.matrix_basis.copy() for pb in arm.pose.bones}
    def key(frame):
        for pb in arm.pose.bones:
            pb.keyframe_insert('location',frame=frame)
            pb.keyframe_insert('rotation_quaternion' if pb.rotation_mode=='QUATERNION' else 'rotation_euler',frame=frame)
    for pb in arm.pose.bones: pb.matrix_basis=Matrix.Identity(4)
    key(1)
    for pb in arm.pose.bones: pb.matrix_basis=posed[pb.name]
    key(34)
    sc.frame_start,sc.frame_end=1,58
    sc.frame_set(1)
    # The sleeves: shirt beyond the shoulder seam, in his rest.
    arm_faces=[]
    for f in body.data.polygons:
        x=sum(abs(rest[v].x) for v in f.vertices)/len(f.vertices); z=sum(rest[v].z for v in f.vertices)/len(f.vertices)
        if kinds[f.index]==2 and x>.215 and z>.9: arm_faces.append(f.index)
    bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active=body
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_mode(type='FACE'); bpy.ops.mesh.select_all(action='DESELECT')
    bm=bmesh.from_edit_mesh(body.data); bm.faces.ensure_lookup_table()
    for i in arm_faces: bm.faces[i].select=True
    bmesh.update_edit_mesh(body.data); bpy.ops.mesh.separate(type='SELECTED'); bpy.ops.object.mode_set(mode='OBJECT')
    sleeves=next(o for o in bpy.context.selected_objects if o is not body)
    sleeves.name=sleeves.data.name='taxi_driver_sleeves_scan'
    bpy.ops.object.select_all(action='DESELECT'); sleeves.select_set(True); bpy.context.view_layer.objects.active=sleeves
    # Simulated coarse (about 2 cm), so cotton folds broad and heavy instead of crumpling
    # like paper; smoothed by subdivision once it has settled.
    sub=sleeves.modifiers.new('fine','SUBSURF'); sub.subdivision_type='SIMPLE'; sub.levels=1
    bpy.ops.object.modifier_move_to_index(modifier='fine',index=0); bpy.ops.object.modifier_apply(modifier='fine')
    # Pinned where the sleeve is sewn to the shoulder and where the cuff closes round the wrist.
    bm=bmesh.new(); bm.from_mesh(sleeves.data); bm.verts.ensure_lookup_table()
    edge=[v.co.copy() for v in bm.verts if v.is_boundary]
    from mathutils.kdtree import KDTree
    tree=KDTree(len(edge))
    for i,c in enumerate(edge): tree.insert(c,i)
    tree.balance()
    pin=sleeves.vertex_groups.new(name='pin')
    for v in bm.verts:
        d=tree.find(v.co)[2]
        if d<.03: pin.add([v.index],max(0.,1-d/.03)**2,'REPLACE')
    bm.free()
    # The arm inside: the sleeve itself, 1.5 cm in, moving with the skeleton.
    body_arm=sleeves.copy(); body_arm.data=sleeves.data.copy(); body_arm.name='_sleeve_collider'
    bpy.context.collection.objects.link(body_arm)
    shrink=body_arm.modifiers.new('in','DISPLACE'); shrink.strength=-.01; shrink.mid_level=0
    bpy.context.view_layer.objects.active=body_arm
    bpy.ops.object.modifier_move_to_index(modifier='in',index=0)
    col=body_arm.modifiers.new('collide','COLLISION'); body_arm.collision.thickness_outer=.004; body_arm.collision.cloth_friction=8
    body_arm.hide_render=True
    cloth=sleeves.modifiers.new('cotton','CLOTH'); cs=cloth.settings
    cs.quality=5; cs.mass=.18; cs.air_damping=2
    cs.tension_stiffness=cs.compression_stiffness=40; cs.shear_stiffness=10; cs.bending_stiffness=25
    cs.vertex_group_mass='pin'; cs.pin_stiffness=1
    # (Self-collision costs twenty minutes here and the folds are fine without it.)
    cc=cloth.collision_settings; cc.distance_min=.003; cc.use_self_collision=False; cc.collision_quality=2
    cloth.point_cache.frame_start=1; cloth.point_cache.frame_end=58
    import time; t0=time.time()
    for f in range(1,59):
        sc.frame_set(f)
        if f%10==0: print('TAXI_SLEEVE_FRAME',f,round(time.time()-t0,1),flush=True)
    ev=sleeves.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data=bpy.data.meshes.new_from_object(ev); data.transform(sleeves.matrix_world)
    sleeves.modifiers.clear(); sleeves.parent=None; sleeves.matrix_world=Matrix.Identity(4); sleeves.data=data
    sleeves.vertex_groups.clear()
    # The settled cotton smoothed: two light passes, then one level of subdivision.
    bm=bmesh.new(); bm.from_mesh(sleeves.data)
    inner=[v for v in bm.verts if not v.is_boundary]
    for _ in range(2): bmesh.ops.smooth_vert(bm,verts=inner,factor=.35,use_axis_x=True,use_axis_y=True,use_axis_z=True)
    bm.to_mesh(sleeves.data); bm.free()
    bpy.ops.object.select_all(action='DESELECT'); sleeves.select_set(True); bpy.context.view_layer.objects.active=sleeves
    smooth=sleeves.modifiers.new('smooth','SUBSURF'); smooth.levels=1; smooth.boundary_smooth='PRESERVE_CORNERS'
    bpy.ops.object.modifier_apply(modifier='smooth')
    for p in sleeves.data.polygons: p.use_smooth=True
    bpy.data.objects.remove(body_arm)
    print('TAXI_DRIVER_SLEEVES faces',len(sleeves.data.polygons),'pinned edge verts',len(edge))
    return sleeves

def driver_on_scan():
    """Eric's photoscanned shirt, waistcoat, tie, trousers, hands and shoes, seated and
    driving; the Khmer driver's head (built above) set into the collar."""
    arm,body=import_rigged('taxi_driver_scan')
    rest=[(body.matrix_world@v.co).copy() for v in body.data.vertices]
    hip=Vector(w(DRIVER_HIP))
    arm.location+=hip-joint(arm,bone(arm,'hip_'))
    # Seated: thighs forward and a little up, the right foot on the accelerator, the left by the clutch.
    for side,x,knee,ankle,ball in [('l',.36,(.38,-.35,.47),(.37,-.58,.12),(.37,-.72,.05)),
                                   ('r',.18,(.17,-.35,.46),(.15,-.6,.14),(.13,-.75,.08))]:
        aim(arm,bone(arm,f'upperleg_{side}'),bone(arm,f'lowerleg_{side}'),knee)
        aim(arm,bone(arm,f'lowerleg_{side}'),bone(arm,f'foot_{side}'),ankle)
        aim(arm,bone(arm,f'foot_{side}'),bone(arm,f'ball_{side}'),ball)
    # Sitting back against the seat, then hunched a little over the wheel at the shoulders.
    s1,s2,s3,neck,head=[bone(arm,p) for p in ['spine_01','spine_02','spine_03','neck_','head_']]
    for name,child,lean in [(s1,s2,.10),(s2,s3,.02),(s3,neck,-.12),(neck,head,-.22)]:
        j=joint(arm,name); aim(arm,name,child,j+Vector((0,lean,1)))
    # Hands on the rim at a little above nine and three, from outside, fingers round it.
    C=Vector(w(WHEEL_CENTRE)); F=Vector(w(WHEEL_FACING))-Vector(w((0,0,0))); F.normalize()
    R=Vector((1,0,0)); R=(R-F*R.dot(F)).normalized(); U=F.cross(R)
    if U.z<0: U=-U
    for side,sign in [('l',1),('r',-1)]:
        grip=C+R*sign*WHEEL_RADIUS*math.cos(.2)+U*WHEEL_RADIUS*math.sin(.2)
        wrist=grip+F*.06+R*sign*.035
        reach(arm,bone(arm,f'upperarm_{side}'),bone(arm,f'lowerarm_{side}'),bone(arm,f'hand_{side}'),wrist,
              joint(arm,bone(arm,f'upperarm_{side}'))+Vector((sign*.5,.3,-1)))
        # Fingers forward through the wheel, the palm turned in against the rim's outside.
        hand=bone(arm,f'hand_{side}'); w0=joint(arm,hand)
        aim(arm,hand,bone(arm,f'middle_01_{side}'),w0+(-F-R*sign*.3).normalized())
        _,d=knuckles(arm,side); want=-R*sign; want=(want-d*want.dot(d)).normalized()
        have=palm_of(arm,side); have=(have-d*have.dot(d)).normalized()
        roll=math.atan2(have.cross(want).dot(d),have.dot(want))
        turn_bone(arm,hand,d,roll)
        curl(arm,side,math.radians(62),math.radians(25))
    global DRIVER_SCAN_NECK
    DRIVER_SCAN_NECK=joint(arm,neck).copy()
    # What each face is, from the photo and his A-pose rest, kept on the faces themselves
    # (the sleeves are split off below): 0 waistcoat/trousers/shoes, 1 hands, 2 shirt, 3 his own head.
    colour=scan_colour(body)
    kinds=[]
    for f in body.data.polygons:
        z=sum(rest[v].z for v in f.vertices)/len(f.vertices); x=sum(abs(rest[v].x) for v in f.vertices)/len(f.vertices)
        r=math.hypot(*(sum((rest[v].xy for v in f.vertices),Vector((0,0)))/len(f.vertices)))
        c=colour[f.index]; white=min(c)>.36 and max(c)-min(c)<.12
        # His own neck, head and hair go cleanly (prevents stray chin triangles poking into 4K head scan!).
        if (z>1.445 and x<.14) or z>1.54: kinds.append(3)
        # The hands beyond the cuffs (in his A-pose rest), the wrist's shaded skin included.
        elif x>.5 and z<1.2 and not white and (skin_like(c) or x>.58): kinds.append(1)
        elif white or (x>.215 and z>.95 and max(c)>.2 and not skin_like(c)): kinds.append(2)
        else: kinds.append(0)
    body.data.attributes.new('drv_kind','INT','FACE').data.foreach_set('value',kinds)
    sleeves=simulate_sleeves(arm,body,rest,kinds)
    bake_pose(arm,body)
    kinds=[0]*len(body.data.polygons); body.data.attributes['drv_kind'].data.foreach_get('value',kinds)
    base=body.data.materials[0]
    # One recoloured photo for all of him, decided pixel by pixel (so every edge follows the
    # photo, not the mesh): his skin in the sun-browned grade of his face, the shirt a plain
    # washed cream under its own soft folds, the waistcoat, trousers and shoes as scanned.
    clothes=with_colour_map(base,'M_taxi_driver_clothes_scan',driver_photo(scan_photo(base)))
    # (The scan's A-pose folds in the relief are kept, softened, under the simulated ones.)
    for n in clothes.node_tree.nodes:
        if n.type=='NORMAL_MAP': n.inputs['Strength'].default_value=.6
    body.data.materials.clear(); body.data.materials.append(clothes)
    sleeves.data.materials.clear(); sleeves.data.materials.append(clothes)
    bm=bmesh.new(); bm.from_mesh(body.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if kinds[f.index]==3],context='FACES'); bm.to_mesh(body.data); bm.free()
    body.name=body.data.name='taxi_driver_body_scan'
    # His head is a real photoscanned face (tools/travel/taxi_driver_head.py): the
    # MakeHuman head, hair, brows, lashes, eyes, suit and krama all go.
    for name in ['taxi_driver_suit','taxi_driver_krama','taxi_driver_anatomy','taxi_driver_hair',
                 'taxi_driver_brows','taxi_driver_lashes','taxi_driver_eyes']:
        o=bpy.data.objects.get(name)
        if o: bpy.data.objects.remove(o)
    scanned_head(DRIVER_SCAN_NECK)

# The scanned head's own frame (metres, facing -Y like the car): the base of the neck, the
# pivot it turns on, the eyes, the mouth line and the jaw's hinge before the ear.
HEAD_NECK_BASE=Vector((-.004,.03,1.79))
HEAD_PIVOT=Vector((-.004,.03,1.83))
HEAD_EYES=[Vector((-.040,-.088,1.9695)),Vector((.034,-.088,1.970))]
HEAD_MOUTH_Z=1.890
HEAD_HINGE=Vector((0,-.004,1.936))
# At rest he looks past Sora into the trees on her side; his glances turn him from there.
HEAD_REST_YAW=-27

def _smooth(e0,e1,x):
    t=np.clip((x-e0)/(e1-e0),0,1); return t*t*(3-2*t)

def scanned_head(neck):
    """The driver's photoscanned head set on the scanned body's collar, with the shapes the
    runtime drives: look_road, look_sora, nod, talk and blink."""
    o=import_glb(SCANS/'taxi_driver_head.glb')[0]
    o.name='taxi_driver_head_scan'; o.data.name='taxi_driver_head_scan'
    for p in o.data.polygons: p.use_smooth=True
    co=np.array([v.co[:] for v in o.data.vertices])
    def turned(points,yaw=0.,pitch=0.,pivot=HEAD_PIVOT,weight=None):
        R=(Matrix.Rotation(math.radians(yaw),3,'Z')@Matrix.Rotation(math.radians(pitch),3,'X'))
        rel=points-np.array(pivot); moved=rel@np.array(R).T+np.array(pivot)
        w=_smooth(1.78,1.93,points[:,2])[:,None] if weight is None else weight[:,None]
        return points+(moved-points)*w
    shapes={}
    # Back to the road (from his rest look past Sora), round to Sora, and a small nod.
    shapes['look_road']=turned(co,yaw=-HEAD_REST_YAW*.92)
    shapes['look_sora']=turned(co,yaw=HEAD_REST_YAW*.75,pitch=5)
    shapes['nod']=turned(co,pitch=9)
    # Speech: the jaw drops on its hinge; lips stretch rather than part, as a mumble.
    jaw=_smooth(HEAD_MOUTH_Z+.003,HEAD_MOUTH_Z-.006,co[:,2])*_smooth(.012,-.03,co[:,1])*_smooth(1.80,1.845,co[:,2])
    jaw*=1-_smooth(.034,.06,np.abs(co[:,0]))*_smooth(HEAD_MOUTH_Z-.03,HEAD_MOUTH_Z,co[:,2])
    shapes['talk']=turned(co,pitch=11,pivot=HEAD_HINGE,weight=jaw)
    # Blink: each upper lid slides down over the eye, the lower lid rises to meet it.
    blink=co.copy()
    for e in HEAD_EYES:
        dx=(co[:,0]-e.x)/.019; front=_smooth(-.065,-.08,co[:,1])
        across=np.clip(1-dx*dx,0,1)
        upper=across*front*_smooth(e.z+.016,e.z+.004,co[:,2])*_smooth(e.z-.002,e.z+.003,co[:,2])
        lower=across*front*_smooth(e.z-.012,e.z-.004,co[:,2])*_smooth(e.z+.001,e.z-.003,co[:,2])
        blink[:,2]-=upper*.0085; blink[:,1]-=upper*.0012
        blink[:,2]+=lower*.0022
    shapes['blink']=blink
    # Into the car: neck base on the collar, turned past Sora, a little forward over the wheel.
    T=(Matrix.Translation(neck+Vector((0,-.026,-.04)))@Matrix.Rotation(math.radians(HEAD_REST_YAW),4,'Z')
       @Matrix.Rotation(math.radians(4),4,'X')@Matrix.Translation(-HEAD_NECK_BASE))
    o.shape_key_add(name='Basis',from_mix=False)
    for name,pts in shapes.items():
        key=o.shape_key_add(name=name,from_mix=False)
        key.data.foreach_set('co',pts.astype(np.float32).ravel()); key.value=0
    o.data.transform(T,shape_keys=True); o.data.update()
    print('TAXI_DRIVER_HEAD scan at',[round(v,3) for v in (T@HEAD_NECK_BASE)],'faces',len(o.data.polygons))

def scan_photo(base):
    return next(n.image for n in base.node_tree.nodes
                if n.type=='TEX_IMAGE' and n.image and n.image.colorspace_settings.name=='sRGB')

def soft_shading(image,radius=10):
    """A scan photo's light and shade with its weave or check blurred away: the folds,
    creases and seams of the cloth, ready to be dyed another plain colour."""
    wd,ht=image.size; px=np.empty(wd*ht*4,np.float32); image.pixels.foreach_get(px)
    lum=px.reshape(ht,wd,4)[...,:3]@np.array([.3,.59,.11],np.float32)
    def box(a,r):
        c=np.cumsum(np.pad(a,((r+1,r),(0,0)),mode='edge'),0); a=(c[2*r+1:]-c[:-2*r-1])/(2*r+1)
        c=np.cumsum(np.pad(a,((0,0),(r+1,r)),mode='edge'),1); return (c[:,2*r+1:]-c[:,:-2*r-1])/(2*r+1)
    return box(box(lum,radius),radius)

def shade_at(body,shade,faces):
    """The mean of a soft shading map at these faces' UV centres."""
    uvl=body.data.uv_layers.active.data; ht,wd=shade.shape; vals=[]
    for p in body.data.polygons:
        if p.index in faces:
            uv=sum((uvl[li].uv for li in p.loop_indices),Vector((0,0)))/len(p.loop_indices)
            vals.append(shade[int((uv.y%1)*(ht-1)),int((uv.x%1)*(wd-1))])
    return float(np.mean(vals)) if vals else .5

def with_colour_map(base,name,image):
    """A copy of the scan's material reading its colour from `image`."""
    m=base.copy(); m.name=name
    for n in m.node_tree.nodes:
        if n.type=='TEX_IMAGE' and n.image and n.image.colorspace_settings.name=='sRGB': n.image=image
    return m

def redyed(base,name,image_name,colour,shade,mean):
    """A copy of the scan's material whose colour map is `colour` (sRGB) under its own folds."""
    k=np.clip(shade/max(mean,1e-3),.62,1.25)[...,None]; ht,wd=shade.shape
    out=np.concatenate([np.array(colour,np.float32)*k,np.ones((ht,wd,1),np.float32)],-1)
    img=bpy.data.images.new(image_name,wd,ht); img.pixels.foreach_set(out.ravel()); img.pack()
    m=base.copy(); m.name=name
    for n in m.node_tree.nodes:
        if n.type=='TEX_IMAGE' and n.image and n.image.colorspace_settings.name=='sRGB': n.image=img
    return m

def passenger_on_scan():
    """Sora's full seated first-person human body from Carla's photoscan: cream woven
    cotton blouse & sleeves, warm posed forearms & articulated human hands resting on
    her thighs, tailored olive-taupe travel trousers, bare ankles, and black leather
    pumps on the passenger floor mat. Only her head & upper neck are removed so the
    first-person eye camera never clips inside her chin or collar."""
    for o in [o for o in bpy.data.objects if o.name.startswith('taxi_sora')]: bpy.data.objects.remove(o)
    arm,body=import_rigged('taxi_sora_scan')
    rest=[(body.matrix_world@v.co).copy() for v in body.data.vertices]
    hip=Vector(w(SORA_HIP))
    arm.location+=hip-joint(arm,bone(arm,'hip_'))
    # Subtle natural lean back against the front passenger backrest so her torso & shoulders sit
    # comfortably behind Sora's eye camera without obstructing downward view to her lap & shoes.
    for sp, deg in [('spine_01', -4.0), ('spine_02', -4.0), ('spine_03', -3.0)]:
        try: turn_bone(arm, bone(arm, sp), Vector((1, 0, 0)), math.radians(deg))
        except StopIteration: pass
    for side,knee,ankle,ball in [('l',(-.19,-.31,.44),(-.18,-.53,.12),(-.18,-.67,.03)),
                                 ('r',(-.35,-.31,.44),(-.37,-.53,.12),(-.38,-.67,.03))]:
        # Her heels and the balls of her feet on the Rosalie's own floorboards, not through them.
        fa=ray_down(ankle[0],ankle[1],.4); fb=ray_down(ball[0],ball[1],.4)
        if fa is not None: ankle=(ankle[0],ankle[1],max(ankle[2],fa+.105))
        if fb is not None: ball=(ball[0],ball[1],max(ball[2],fb+.045))
        aim(arm,bone(arm,f'upperleg_{side}'),bone(arm,f'lowerleg_{side}'),knee)
        aim(arm,bone(arm,f'lowerleg_{side}'),bone(arm,f'foot_{side}'),ankle)
        aim(arm,bone(arm,f'foot_{side}'),bone(arm,f'ball_{side}'),ball)
    # Pose both arms & realistic human hands resting naturally palms-down ON TOP of her thighs
    # (measured thigh tops: L=0.529->0.518, R=0.520->0.502; kept cleanly behind knees so shoes stay 100% visible!).
    reach(arm,bone(arm,'upperarm_l'),bone(arm,'lowerarm_l'),bone(arm,'hand_l'),
          Vector((-.190,-.215,.556)),Vector((-.05,.04,.49)))
    reach(arm,bone(arm,'upperarm_r'),bone(arm,'lowerarm_r'),bone(arm,'hand_r'),
          Vector((-.355,-.215,.548)),Vector((-.48,.04,.49)))
    for side,aim_pt,palm_dir in [
        ('l', Vector((-.225,-.335,.544)), Vector((-.16,-.08,-1.0))),
        ('r', Vector((-.320,-.335,.534)), Vector(( .16,-.08,-1.0))),
    ]:
        hand=bone(arm,f'hand_{side}')
        aim(arm,hand,bone(arm,f'middle_01_{side}'),aim_pt)
        _,d=knuckles(arm,side)
        want=palm_dir.normalized(); want=(want-d*want.dot(d)).normalized()
        have=palm_of(arm,side); have=(have-d*have.dot(d)).normalized()
        roll=math.atan2(have.cross(want).dot(d),have.dot(want))
        turn_bone(arm,hand,d,roll)
        curl(arm,side,0.16,0.10)
    neck_pos=joint(arm,bone(arm,'neck_')).copy()
    wrists={}
    for side in ('l','r'):
        w_pos=joint(arm,bone(arm,f'hand_{side}')).copy()
        e_pos=joint(arm,bone(arm,f'lowerarm_{side}')).copy()
        across,fwd=knuckles(arm,side)
        arm_dir=(w_pos-e_pos).normalized()
        up_dir=palm_of(arm,side)*(-1.0)
        up_dir=(up_dir-arm_dir*up_dir.dot(arm_dir)).normalized()
        side_dir=up_dir.cross(arm_dir).normalized()
        wrists[side]=(w_pos,arm_dir,side_dir,up_dir)
    bake_pose(arm,body)
    colour=scan_colour(body)
    base=body.data.materials[0]
    kinds=[]
    for f in body.data.polygons:
        z=sum(rest[v].z for v in f.vertices)/len(f.vertices)
        x=sum(abs(rest[v].x) for v in f.vertices)/len(f.vertices); c=colour[f.index]
        if z<.16 and max(c)<.22: kinds.append(2)                                  # her dark leather pumps
        elif x>.510 or (skin_like(c) and (z<.30 or x>.475)): kinds.append(1)      # full hands/fingers/wrists & bare ankles (clean cuffs, zero white fingertips!)
        elif z>.95 or x>.22: kinds.append(3)                                      # vintage cream 1930s linen blouse & sleeves
        else: kinds.append(0)                                                     # tailored travel trousers
    shade=soft_shading(scan_photo(base),16)
    def mean(k): return shade_at(body,shade,{i for i,kk in enumerate(kinds) if kk==k})
    trousers=redyed(base,'M_taxi_sora_trousers_scan','T_taxi_sora_trousers',(.28,.24,.19),shade,mean(0))
    blouse=redyed(base,'M_taxi_sora_blouse_scan','T_taxi_sora_blouse',(.54,.49,.41),shade,mean(3))
    skin=tinted(base,'M_taxi_sora_skin_scan',(.92,.72,.56))
    neck_shadow=plain('M_taxi_sora_neck_cap',(.14,.11,.09),.94)
    body.data.materials.clear()
    for m in (trousers,skin,base,blouse,neck_shadow): body.data.materials.append(m)
    base.name='M_taxi_sora_shoes_scan'
    bm=bmesh.new(); bm.from_mesh(body.data); bm.faces.ensure_lookup_table()
    for f in bm.faces:
        f.material_index=kinds[f.index]
    # Razor-smooth plane cut right at the base of Sora's neck (behind and below the eye camera)
    # so her shoulders & upper chest stay 100% smooth and intact with zero jagged sawtooth edges.
    cut_co=neck_pos-Vector((0.0,0.0,0.025))
    cut_no=Vector((0.0,-0.18,1.0)).normalized()
    res=bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
        plane_co=cut_co,
        plane_no=cut_no,
        clear_outer=True,
        use_snap_center=False,
    )
    cut_edges=[g for g in res['geom_cut'] if isinstance(g,bmesh.types.BMEdge)]
    if cut_edges:
        filled=bmesh.ops.holes_fill(bm,edges=cut_edges,sides=0)['faces']
        for f in filled: f.material_index=4
        bmesh.ops.triangulate(bm,faces=filled)
    bm.to_mesh(body.data); bm.free()
    for p in body.data.polygons: p.use_smooth=True
    body.name=body.data.name='taxi_sora_legs_scan'
    # Delicate 1930s rectangular antique-gold tank wristwatch on a dark brown leather strap
    # wrapped snugly around Sora's left wrist (dresses the wrist cleanly while preserving her natural scanned sleeve cuffs!).
    coll=bpy.context.collection
    watch_gold=plain('M_taxi_sora_watch_gold',(.58,.44,.18),.24,.92)
    watch_strap=plain('M_taxi_sora_watch_strap',(.14,.07,.04),.68)
    watch_dial=plain('M_taxi_sora_watch_dial',(.78,.72,.58),.22)
    bm_wgold,bm_wstrap,bm_wdial,bm_whands=bmesh.new(),bmesh.new(),bmesh.new(),bmesh.new()
    watch_hands=plain('M_taxi_sora_watch_hands',(.04,.05,.09),.28,.85)
    segs=20
    w_pos,arm_dir,side_dir,up_dir=wrists['l']
    # Seat forward onto Sora's bare left wrist skin (+arm_dir), cleanly clear of her blouse sleeve cuff!
    w_ctr=w_pos+arm_dir*0.015+up_dir*0.0025
    M_w=Matrix.Translation(w_ctr)@Matrix((side_dir,arm_dir,up_dir)).transposed().to_4x4()
    s_rings=[]
    for dy,rx,rz in [(-0.0055,0.0315,0.0255),(0.0055,0.0315,0.0255),(0.0055,0.0278,0.0222),(-0.0055,0.0278,0.0222)]:
        s_rings.append([bm_wstrap.verts.new(M_w@Vector((math.cos(k/segs*math.tau)*rx,dy,math.sin(k/segs*math.tau)*rz))) for k in range(segs)])
    for r_idx in range(4):
        rA,rB=s_rings[r_idx],s_rings[(r_idx+1)%4]
        for k in range(segs):
            bm_wstrap.faces.new((rA[k],rA[(k+1)%segs],rB[(k+1)%segs],rB[k]))
    def _wbox(bm_t,loc,sz,rot_z=0.0):
        M=M_w@Matrix.Translation(loc)@Matrix.Rotation(rot_z,4,'Z')@Matrix.Diagonal((*sz,1.0))
        ret=bmesh.ops.create_cube(bm_t,size=1.0,matrix=M)
        edges=list({e for v in ret['verts'] for e in v.link_edges})
        bmesh.ops.bevel(bm_t,geom=edges,offset=0.0007,segments=1,affect='EDGES',clamp_overlap=True)
    _wbox(bm_wgold,(0.0,0.0,0.0268),(0.0152,0.0205,0.0044))
    _wbox(bm_wgold,(0.0,0.0114,0.0266),(0.0030,0.0026,0.0028))
    _wbox(bm_wdial,(0.0,0.0,0.0290),(0.0114,0.0158,0.0014))
    # Delicate blued-steel hands set to 22:45 on the rectangular tank dial
    _wbox(bm_whands,(-0.0018,0.0012,0.0299),(0.0009,0.0046,0.0005),rot_z=0.65)
    _wbox(bm_whands,(-0.0026,-0.0004,0.0301),(0.0007,0.0062,0.0005),rot_z=1.57)
    for nm,bm_x,mt in [('taxi_sora_watch_case',bm_wgold,watch_gold),('taxi_sora_watch_strap',bm_wstrap,watch_strap),
                       ('taxi_sora_watch_dial',bm_wdial,watch_dial),('taxi_sora_watch_hands',bm_whands,watch_hands)]:
        bmesh.ops.recalc_face_normals(bm_x,faces=bm_x.faces)
        me=bpy.data.meshes.new(nm); bm_x.to_mesh(me); bm_x.free()
        for p in me.polygons: p.use_smooth=True
        o=bpy.data.objects.new(nm,me); coll.objects.link(o); o.data.materials.append(mt)
    print('TAXI_SORA_SCAN faces',len(body.data.polygons),'kinds',[kinds.count(k) for k in (0,1,2,3)])

mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'all'
if mode in ['all','roadside']: palm_card(); roadside()
if mode in ['all','cabin']: cabin()
