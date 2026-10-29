"""Original carved-wood household effigy. No human skin, clothing or eye assets.
blender -b --factory-startup -P tools/characters/build-shrine-effigy.py
"""
import bpy, math, random
from pathlib import Path
from mathutils import Vector
R = Path(__file__).resolve().parents[2]
OUT = R/'art-source/props/phra-phum'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
rng = random.Random(6319)

def sphere(name, at, scale, segments=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=at)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o

def join(parts, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]; bpy.ops.object.join()
    o=parts[0]; o.name=name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o

def cut(obj, cutter):
    bpy.context.view_layer.objects.active=obj
    m=obj.modifiers.new('Chisel cut', 'BOOLEAN'); m.operation='DIFFERENCE'; m.object=cutter
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

def groove(obj, name, points, radius):
    data=bpy.data.curves.new(name,'CURVE'); data.dimensions='3D'; data.bevel_depth=radius; data.bevel_resolution=1; data.resolution_u=1; data.use_fill_caps=True
    s=data.splines.new('POLY');s.points.add(len(points)-1)
    for p,co in zip(s.points,points):p.co=(*co,1)
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH')
    cut(obj,o)

# One stocky block of timber: seated folded legs, sloping shoulders, hands in lap.
parts=[sphere('trunk',(0,.008,.206),(.073,.052,.104)),
       sphere('shoulders',(0,.006,.276),(.091,.050,.044)),
       sphere('lap',(0,-.019,.092),(.107,.072,.057))]
for side in [-1,1]:
    knee=sphere('folded knee',(side*.073,-.030,.052),(.065,.068,.035),20,12);knee.rotation_euler.z=side*.24;parts.append(knee)
    arm=sphere('hewn upper arm',(side*.083,.0,.221),(.022,.025,.066),16,12);arm.rotation_euler.y=side*-.25;parts.append(arm)
    forearm=sphere('forearm',(side*.062,-.046,.157),(.046,.023,.020),16,12);forearm.rotation_euler.z=side*.30;parts.append(forearm)
    parts.append(sphere('block hand',(side*.026,-.066,.148),(.031,.019,.012),16,10))
# A carved neck, with a visible dark seam at the turning wooden joint.
parts.append(sphere('neck',(0,.004,.319),(.032,.029,.033),16,12))
body=join(parts,'effigy_body')
m=body.modifiers.new('Timber block union','REMESH');m.mode='VOXEL';m.voxel_size=.0017;m.use_smooth_shade=False
bpy.context.view_layer.objects.active=body;bpy.ops.object.modifier_apply(modifier=m.name)
m=body.modifiers.new('Worn chisel ridges','SMOOTH');m.factor=.75;m.iterations=3;bpy.ops.object.modifier_apply(modifier=m.name)
m=body.modifiers.new('Broad hand cut planes','DECIMATE');m.ratio=.18;bpy.ops.object.modifier_apply(modifier=m.name)
for side in [-1,1]:
    # Three shallow straight finger separations, cut into the same wooden hand.
    for k in range(3):
        x=side*(.015+k*.009)
        groove(body,'carved finger division',[(x,-.084,.139),(x,-.083,.151),(x+side*.002,-.075,.156)],.0010)
# Long splits, not skin veins or painted spots.
groove(body,'shoulder grain split',[(.046,-.034,.297),(.049,-.044,.267),(.045,-.047,.234),(.048,-.043,.214)],.0016)
groove(body,'lap grain split',[(-.052,-.084,.078),(-.054,-.088,.058),(-.050,-.082,.027)],.0019)
# Simple incised robe folds read as rigid cuts in timber, not separate clothes.
for x in [-.049,-.024,.021,.046]:
    groove(body,'carved robe channel',[(x,-.042,.239),(x*.90,-.054,.204),(x*1.2,-.062,.176)],.0015)

# Place long grain splits on the actual front surface, not in empty air.
def surface_split(obj, name, samples, radius):
    points=[]
    for x,z in samples:
        hit,point,normal,index=obj.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))
        if hit:points.append((point.x,point.y+.0007,point.z))
    if len(points)>1:groove(obj,name,points,radius)
for x in [-.044,-.023,.018,.039]:
    surface_split(body,'incised vertical robe fold',[(x*.9,.265),(x,.239),(x*.92,.215),(x*1.12,.185)],.0015)
surface_split(body,'deep shoulder grain split',[(.041,.296),(.043,.275),(.039,.253),(.042,.224)],.0018)

# A mask-like, deliberately stylised carved head with broad cheeks and a long nose.
verts=[];faces=[];rows=36;cols=64
for j in range(rows+1):
    t=j/rows;z=.336+t*.143
    # Flattened jaw, broad cheek planes and a slightly asymmetric worn crown.
    rx=.047*(math.sin(math.pi*(.11+.85*t))**.45)
    ry=.039*(math.sin(math.pi*(.14+.80*t))**.35)
    for k in range(cols):
        a=k/cols*math.tau;x=rx*math.sin(a);y=-ry*math.cos(a)
        front=max(0,math.cos(a))**6
        def g(cx,cz,sx,sz):return math.exp(-((x-cx)/sx)**2-((z-cz)/sz)**2)
        relief=0
        # Deep orbital planes, lowered brow, long straight carved nose and spare lips.
        for side in [-1,1]:
            relief += .010*g(side*.022,.423,.016,.010)
            relief -= .010*g(side*.024,.438,.019,.006)
            relief -= .004*g(side*.033,.395,.018,.016)
        relief -= .027*g(.001,.407,.008,.030)
        relief -= .005*g(0,.371,.026,.005)
        relief += .005*g(0,.365,.027,.0025)
        y+=front*relief
        # Millimetre-scale chisel facets in the stock, not soft anatomical pores.
        y+=front*(math.sin(k*2.7+j*.87)*.00055)
        verts.append((x,y,z))
for j in range(rows):
    for k in range(cols):
        n=j*cols+k; q=j*cols+(k+1)%cols
        faces.append((n,q,q+cols,n+cols))
faces.append(tuple(reversed(range(cols))));faces.append(tuple(rows*cols+k for k in range(cols)))
mesh=bpy.data.meshes.new('Hewn wooden mask');mesh.from_pydata(verts,[],faces);mesh.update()
head=bpy.data.objects.new('effigy_head',mesh);bpy.context.collection.objects.link(head)
for side in [-1,1]:
    cut(head,sphere('empty carved eye socket',(side*.022,-.030,.421),(.0155,.030,.0065),32,16))
groove(head,'closed incised mouth',[(-.026,-.035,.367),(-.012,-.040,.366),(0,-.041,.366),(.013,-.039,.365),(.025,-.033,.364)],.0018)
groove(head,'forehead timber split',[(-.012,-.025,.474),(-.014,-.034,.457),(-.011,-.044,.441),(-.013,-.036,.429)],.00165)
groove(head,'cheek chip',[(.035,-.024,.398),(.039,-.030,.384),(.034,-.025,.369)],.0015)
surface_split(head,'open forehead grain split',[(-.007,.476),(-.010,.46),(-.008,.445),(-.012,.434)],.0017)
surface_split(head,'worn cheek timber check',[(.032,.400),(.035,.386),(.030,.370)],.0014)
ears=[sphere('carved ear',(side*.047,.0,.408),(.010,.013,.025),12,10) for side in [-1,1]]
head=join([head]+ears,'effigy_head')
# Solid plinth cut from the same stock.
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,.012));base=bpy.context.object;base.name='effigy_integral_plinth';base.scale=(.248,.169,.024)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
m=base.modifiers.new('Worn plinth arris','BEVEL');m.width=.003;m.segments=1;bpy.context.view_layer.objects.active=base;bpy.ops.object.modifier_apply(modifier=m.name)
body=join([body,base],'effigy_body')
for o in [body,head]:
    # Mixed planes: small flat cuts remain visible along a soft, worn outline.
    for p in o.data.polygons:p.use_smooth=False
    bpy.context.view_layer.objects.active=o;o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.018);bpy.ops.object.mode_set(mode='OBJECT');o.select_set(False)

# Photo-backed, continuous vertical wood grain, desaturated by a century of soot.
wood=bpy.data.materials.new('M_phra_effigy_split_wood');wood.use_nodes=True
n=wood.node_tree.nodes;l=wood.node_tree.links;p=n.get('Principled BSDF')
p.inputs['Roughness'].default_value=.87;p.inputs['Specular IOR Level'].default_value=.23
coords=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');l.new(coords.outputs['Generated'],sep.inputs[0])
# World-space projection keeps the grain upright over face, fingers and folds.
origin=bpy.data.objects.new('wood_grain_origin',None);bpy.context.collection.objects.link(origin);coords.object=origin
separate=n.new('ShaderNodeSeparateXYZ');l.new(coords.outputs['Object'],separate.inputs[0]);comb=n.new('ShaderNodeCombineXYZ')
for source,target,factor in [('Z','X',1.8),('X','Y',3)]:
    m=n.new('ShaderNodeMath');m.operation='MULTIPLY_ADD';m.inputs[1].default_value=factor;m.inputs[2].default_value=.51;l.new(separate.outputs[source],m.inputs[0]);l.new(m.outputs[0],comb.inputs[target])
tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'art-source/library/materials/dark_wood/dark_wood_BC.jpg'));tex.extension='REPEAT';l.new(comb.outputs[0],tex.inputs['Vector'])
hue=n.new('ShaderNodeHueSaturation');hue.inputs['Saturation'].default_value=.48;hue.inputs['Value'].default_value=.70;l.new(tex.outputs['Color'],hue.inputs['Color']);l.new(hue.outputs[0],p.inputs['Base Color'])
noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=155;noise.inputs['Detail'].default_value=2;l.new(coords.outputs['Object'],noise.inputs['Vector'])
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.25;bump.inputs['Distance'].default_value=.0006;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1
# Bake both objects into one shared pair of atlases, then export portable PBR maps.
# Pack both UV sets together so each has its own space in the same atlas.
bpy.ops.object.select_all(action='DESELECT')
for o in [body,head]:
    o.select_set(True);o.data.materials.clear();o.data.materials.append(wood)
    for polygon in o.data.polygons:polygon.material_index=0
bpy.context.view_layer.objects.active=body;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.pack_islands(margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
colour=bpy.data.images.new('phra-effigy-wood-BC',2048,2048);dest=n.new('ShaderNodeTexImage');dest.image=colour;n.active=dest
scene.render.bake.use_clear=True;scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True
bpy.ops.object.bake(type='DIFFUSE',margin=8,use_clear=True)
colour.filepath_raw=str(OUT/'effigy-wood-BC.png');colour.file_format='PNG';colour.save()
normal=bpy.data.images.new('phra-effigy-wood-N',2048,2048);normal.colorspace_settings.name='Non-Color';nd=n.new('ShaderNodeTexImage');nd.image=normal;n.active=nd
bpy.ops.object.bake(type='NORMAL',margin=8,use_clear=True)
normal.filepath_raw=str(OUT/'effigy-wood-N.png');normal.file_format='PNG';normal.save()
for node in list(n):
    if node not in [p,n.get('Material Output'),dest,nd]:n.remove(node)
l.new(dest.outputs['Color'],p.inputs['Base Color']);nm=n.new('ShaderNodeNormalMap');l.new(nd.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],p.inputs['Normal'])
colour.pack();normal.pack()
# Head pivots at a cut timber neck. Animation rotates a rigid wooden piece.
pivot=Vector((0,0,.331))
for v in head.data.vertices:v.co-=pivot
head.location=(0,0,0)
joint=bpy.data.objects.new('effigy_head_joint',None);bpy.context.collection.objects.link(joint)
joint.location=pivot;head.parent=joint
for o in [head,body]:o['hand_carved_wood']=True;o['front']='-Y'
# Source is an editable sculpture with the baked projection retained in textures.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'shrine-effigy.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in [body,head,joint]:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(R/'public/assets/ep1/phra_phum_effigy.glb'),export_format='GLB',use_selection=True,export_yup=True,export_extras=True,export_cameras=False,export_lights=False)
print('WOOD EFFIGY:',sum(len(o.data.polygons) for o in [head,body]),'faces',flush=True)
