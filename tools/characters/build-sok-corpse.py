"""Build Sok's funeral body from CC0 MakeHuman anatomy (Blender 4+).

blender -b -P tools/characters/build-sok-corpse.py
Source downloads / licence: art-source/characters/sok/README.md.
The five baked morph poses preserve the offscreen-only encounter without a live rig.
"""
import bpy, json, gzip, math, sys
from pathlib import Path
from mathutils import Vector, Quaternion, Matrix

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'art-source/library/makehuman-sok'
OUT = ROOT / 'public/assets/ep1/sok_corpse.glb'
sys.path.insert(0,str(ROOT/'tools/characters'))
from sok_lotus import build_lotus
from sok_age import sculpt_age, age_surface
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
verts, uvs, faces, faceuv = [], [], [], []
group = ''
for line in (SRC/'base.obj').read_text().splitlines():
    a=line.split()
    if not a: continue
    if a[0]=='v': verts.append(Vector(map(float,a[1:4])))
    elif a[0]=='vt': uvs.append(tuple(map(float,a[1:3])))
    elif a[0]=='g': group=a[1]
    elif a[0]=='f' and group=='body':
        p=[x.split('/') for x in a[1:]]
        faces.append([int(x[0])-1 for x in p]);faceuv.append([int(x[1])-1 for x in p])

def target(name, weight):
    p=SRC/name
    text=gzip.decompress(p.read_bytes()).decode() if name.endswith('.gz') else p.read_text()
    for line in text.splitlines():
        if not line or line.startswith('#'): continue
        a=line.split();verts[int(a[0])] += Vector(map(float,a[1:4]))*weight

for name,weight in [('asian-male-old.target',1),('universal-male-old-minmuscle-averageweight.target',.7),('universal-male-old-averagemuscle-minweight.target',.3),('eye-left-closure.target.gz',1),('eye-right-closure.target.gz',1),('mouth-open.target.gz',.075),('neck-platysma.target.gz',.3)]:target(name,weight)
used=sorted(set(i for face in faces for i in face));remap={v:i for i,v in enumerate(used)}
sculpt_age(verts,used)
mesh=bpy.data.meshes.new('Sok_anatomical_surface');mesh.from_pydata([verts[i] for i in used],[],[[remap[i] for i in f] for f in faces]);mesh.update()
uv=mesh.uv_layers.new(name='MakeHumanUV')
for poly,indices in zip(mesh.polygons,faceuv):
    for loop,i in zip(poly.loop_indices,indices):uv.data[loop].uv=uvs[i]
body=bpy.data.objects.new('sok_anatomical_body',mesh);bpy.context.collection.objects.link(body)
for p in mesh.polygons:p.use_smooth=True
rigdata=json.loads((SRC/'default.mhskel').read_text())
def joint(n):return sum((verts[i] for i in rigdata['joints'][n]),Vector())/len(rigdata['joints'][n])
arm=bpy.data.armatures.new('Sok_authoring_rig');rig=bpy.data.objects.new('Sok_authoring_rig',arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,b in rigdata['bones'].items():
    bone=arm.edit_bones.new(name);bone.head=joint(b['head']);bone.tail=joint(b['tail'])
for name,b in rigdata['bones'].items():
    if b['parent']:arm.edit_bones[name].parent=arm.edit_bones[b['parent']]
bpy.ops.object.mode_set(mode='OBJECT')
for name,weights in json.loads((SRC/'default_weights.mhw').read_text())['weights'].items():
    g=body.vertex_groups.new(name=name)
    for i,w in weights:
        if i in remap:g.add([remap[i]],w,'REPLACE')
mod=body.modifiers.new('Anatomical_pose','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True

def rotate(name,axis,angle):
    bone=rig.pose.bones[name];r=bone.bone.matrix_local.to_quaternion()
    bone.rotation_mode='QUATERNION';bone.rotation_quaternion=bone.rotation_quaternion @ (r.inverted() @ Quaternion(Vector(axis),math.radians(angle)) @ r)

def pose(index):
    for b in rig.pose.bones:b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion()
    for side,sign in [('L',-1),('R',1)]:
        # Relax the ankles: a supine body's toes should not keep a standing pose.
        rotate('foot.'+side,(1,0,0),30)
        rotate('upperarm01.'+side,(0,0,1),sign*41)
        rotate('lowerarm01.'+side,(0,0,1),sign*13)
        rotate('lowerarm01.'+side,(1,0,0),30)
        # Fingers retain individual joints and nails, with a slack mortuary curl.
        for finger in range(1,6):
            for part in [2,3]:
                if finger==1:rotate(f'finger{finger}-{part}.{side}',(1,0,0),12 if part==2 else 8)
                else:rotate(f'finger{finger}-{part}.{side}',(0,1,0),sign*(25 if part==2 else 18))
    if index>=1:rotate('head',(0,1,0),-22)
    if index>=2:rotate('lowerarm01.R',(1,0,0),-15)
    if index>=3:
        rotate('upperarm01.R',(0,0,1),48)
        rotate('lowerarm01.R',(1,0,0),-27)
        rotate('wrist.R',(1,0,0),-22)
    if index>=4:
        rotate('neck01',(1,0,0),18)
        rotate('head',(0,1,0),-35)
    bpy.context.view_layer.update()

# glTF Blender coordinates: head -X, face +Z; Babylon reflects X on import.
def laid(v):return Vector((-(v.y+.25)*.108,v.x*.108,v.z*.108+.14))
# Face changes remain part of the final saved pose, never a live animation.
def expression_delta(name):
    result={}
    for line in gzip.decompress((SRC/name).read_bytes()).decode().splitlines():
        if line and not line.startswith('#'):
            a=line.split();result[int(a[0])]=Vector(map(float,a[1:4]))
    return result
ajar=expression_delta('eye-left-closure.target.gz')
slack=expression_delta('mouth-open.target.gz')
lay_matrix=Matrix(((0,-.108,0,-.027),(.108,0,0,0),(0,0,.108,.14),(0,0,0,1)))
poses=[];wrist_frames=[];head_frames=[]
for index in range(5):
    for vertex,original in zip(mesh.vertices,used):
        vertex.co=verts[original]
        if index==4:vertex.co += ajar.get(original,Vector())*-.38 + slack.get(original,Vector())*.18
    mesh.update();body.update_tag(refresh={'DATA'})
    pose(index)
    wrist_frames.append(lay_matrix @ rig.pose.bones['wrist.R'].matrix.copy())
    head_frames.append(lay_matrix @ rig.pose.bones['head'].matrix.copy())
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=evaluated.to_mesh();poses.append([laid(v.co) for v in m.vertices]);evaluated.to_mesh_clear()
eye_centers=[laid(joint('eye.'+side+'____head')) for side in ['L','R']]
body.modifiers.clear();bpy.data.objects.remove(rig,do_unlink=True)
for vertex,p in zip(mesh.vertices,poses[0]):vertex.co=p
mesh.update()
body.update_tag(refresh={'DATA'})
body.shape_key_add(name='Basis')
for index in range(1,5):
    key=body.shape_key_add(name=f'Sok_pose_{index}');key.value=0
    for vertex,p in zip(key.data,poses[index]):vertex.co=p
# Retain an optional authoring subdivision modifier; runtime uses the anatomical base cage.
sub=body.modifiers.new('Facial_surface','SUBSURF');sub.levels=1;sub.render_levels=1
bpy.context.view_layer.objects.active=body;body.select_set(True)
# The glTF exporter supports subdivision with shape keys when export_apply=False.

skin=bpy.data.materials.new('sok_aged_skin');skin.use_nodes=True
n=skin.node_tree.nodes;l=skin.node_tree.links;p=n.get('Principled BSDF');p.inputs['Roughness'].default_value=.82;p.inputs['Specular IOR Level'].default_value=.22
tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(SRC/'old_lightskinned_male_diffuse2.png'))
# Desaturated, cool pallor; the source carries pores, age spots, lips, nails and wrinkles.
hue=n.new('ShaderNodeHueSaturation');hue.inputs['Saturation'].default_value=.36;hue.inputs['Value'].default_value=.78;l.new(tex.outputs['Color'],hue.inputs['Color'])
orbital=mesh.color_attributes.new(name='Mortuary_undertone',type='FLOAT_COLOR',domain='POINT')
for vertex,original in zip(mesh.vertices,used):
    point=verts[original];mask=0
    for side in ['L','R']:
        center=joint('eye.'+side+'____head')
        d=point-center;mask=max(mask,math.exp(-((d.x/.46)**2+((d.y+.16)/.25)**2+(d.z/.55)**2))*.24)
    orbital.data[vertex.index].color=(mask,mask,mask,1)
attribute=n.new('ShaderNodeVertexColor');attribute.layer_name=orbital.name
undertone=n.new('ShaderNodeMixRGB');undertone.inputs[2].default_value=(.12,.10,.14,1)
l.new(attribute.outputs['Color'],undertone.inputs[0]);l.new(hue.outputs['Color'],undertone.inputs[1]);l.new(undertone.outputs[0],p.inputs['Base Color'])
aged_color,age_height=age_surface(mesh,verts,used,n,l,undertone.outputs[0])
l.new(aged_color,p.inputs['Base Color'])
# Bake the colour adjustment into a texture, so Babylon receives the same glTF material.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1
image=bpy.data.images.new('Sok_pallor_2k',2048,2048);bake=n.new('ShaderNodeTexImage');bake.image=image;n.active=bake
body.data.materials.append(skin)
for o in bpy.context.selected_objects:o.select_set(False)
body.select_set(True);bpy.context.view_layer.objects.active=body
scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True
bpy.ops.object.bake(type='DIFFUSE',margin=8)
l.new(bake.outputs['Color'],p.inputs['Base Color']);# Keep the original nodes connected to the relief bake until the normal is baked.
# Exportable normal-map bake from aged diffuse luminance plus fine pores.
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.85;bump.inputs['Distance'].default_value=.003
l.new(age_height,bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
normal=bpy.data.images.new('Sok_skin_micro_normal',2048,2048);normal.colorspace_settings.name='Non-Color';normalnode=n.new('ShaderNodeTexImage');normalnode.image=normal;n.active=normalnode
bpy.ops.object.bake(type='NORMAL',margin=8)
n.remove(bump);nm=n.new('ShaderNodeNormalMap');l.new(normalnode.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
image.pack();normal.pack()

# Anatomical eyeballs stay under closed lids until the final slight, unequal opening.
eyes=[]
eye_material=bpy.data.materials.new('sok_clouded_sclera');eye_material.use_nodes=True
shader=eye_material.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.34,.32,.27,1);shader.inputs['Roughness'].default_value=.52;shader.inputs['Specular IOR Level'].default_value=.18
for side,center in zip(['L','R'],eye_centers):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.0105,location=(0,0,0))
    eye=bpy.context.object;eye.name='sok_anatomical_eye_'+side
    for vertex in eye.data.vertices:vertex.co+=center
    for polygon in eye.data.polygons:polygon.use_smooth=True
    eye.data.materials.append(eye_material);eye.shape_key_add(name='Basis')
    for index in range(1,5):
        delta=head_frames[index] @ head_frames[0].inverted();key=eye.shape_key_add(name=f'Sok_pose_{index}');key.value=0
        for vertex,rest in zip(key.data,eye.data.shape_keys.key_blocks[0].data):vertex.co=delta @ rest.co
    eyes.append(eye)
lotus=build_lotus(wrist_frames)

# Collide the sheet against the torso and upper arms. The bare hands rest over
# the sheet, holding the lotus; covering the hand meshes would hide the grip.
hand_groups={g.index for g in body.vertex_groups if g.name.startswith(('finger','wrist','lowerarm02'))}
hand_weight=[sum(g.weight for g in v.groups if g.group in hand_groups) for v in mesh.vertices]
collision_faces=[list(p.vertices) for p in mesh.polygons if sum(hand_weight[i] for i in p.vertices)/len(p.vertices)<.25]
collision_mesh=bpy.data.meshes.new('Sok_shroud_body_contact');collision_mesh.from_pydata([v.co for v in mesh.vertices],[],collision_faces);collision_mesh.update()
collider=bpy.data.objects.new('_Sok_shroud_contact',collision_mesh);bpy.context.collection.objects.link(collider);collider.hide_render=True;collider.modifiers.new('Cloth_collision','COLLISION')
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.008));floor=bpy.context.object;floor.name='_coffin_support';floor.modifiers.new('Cloth_support','COLLISION')
# Tuck the shroud into the lining. Pin its outer hem so gravity cannot bunch
# the whole rectangle into a small pile on the abdomen.
from mathutils.bvhtree import BVHTree
bpy.context.view_layer.update()
bvh=BVHTree.FromObject(collider,bpy.context.evaluated_depsgraph_get())
rows,cols=85,49;points=[];polys=[]
for i in range(rows):
    x=-.55+i/(rows-1)*1.47
    for j in range(cols):
        y=(j/(cols-1)-.5)*.57
        hit,_,_,_=bvh.ray_cast(Vector((x,y,1)),Vector((0,0,-1)))
        h=max(.028,hit.z+.012 if hit is not None else .028)
        fold=.012*math.sin(x*32+y*31)*math.sin(math.pi*j/(cols-1))
        points.append((x,y,h+abs(fold)))
for i in range(rows-1):
    for j in range(cols-1):a=i*cols+j;polys.append((a,a+1,a+cols+1,a+cols))
cm=bpy.data.meshes.new('Cotton_drape');cm.from_pydata(points,[],polys);cm.update();cloth=bpy.data.objects.new('sok_gravity_draped_shroud',cm);bpy.context.collection.objects.link(cloth)
pins=cloth.vertex_groups.new(name='Tucked_hem');pins.add([i*cols+j for i in range(rows) for j in range(cols) if i in (0,rows-1) or j in (0,cols-1)],1,'REPLACE')
clothmod=cloth.modifiers.new('Gravity_and_body_contact','CLOTH');cs=clothmod.settings;cs.vertex_group_mass=pins.name;cs.quality=6;cs.mass=.19;cs.tension_stiffness=18;cs.compression_stiffness=18;cs.shear_stiffness=8;cs.bending_stiffness=.12
cc=clothmod.collision_settings;cc.use_collision=True;cc.distance_min=.003;cc.collision_quality=4;cc.use_self_collision=False;cc.self_distance_min=.004
clothmod.point_cache.frame_start=1;clothmod.point_cache.frame_end=36
for frame in range(1,37):
    scene.frame_set(frame)
    if frame%10==0:print('Cloth frame',frame,flush=True)
# Bake the settled surface; no runtime physics overhead.
bpy.context.view_layer.objects.active=cloth;bpy.ops.object.modifier_apply(modifier=clothmod.name)
bpy.data.objects.remove(floor,do_unlink=True)
for p in cloth.data.polygons:p.use_smooth=True
solid=cloth.modifiers.new('Cotton_hem_thickness','SOLIDIFY');solid.thickness=.0018
sub=cloth.modifiers.new('Soft_folds','SUBSURF');sub.levels=1
bpy.ops.object.modifier_apply(modifier=solid.name);bpy.ops.object.modifier_apply(modifier=sub.name)
# Smooth the cloth envelope over narrow fingers / toes, where point collision
# can leave pinholes after subdivision. A small contact patch bridges those
# gaps and keeps the shroud continuous without erasing the larger folds.
def contact_height(vertex):
    heights=[]
    for dx in [-.014,0,.014]:
        for dy in [-.014,0,.014]:
            hit,_,_,_=bvh.ray_cast(Vector((vertex.co.x+dx,vertex.co.y+dy,1)),Vector((0,0,-1)))
            if hit is not None:heights.append(hit.z)
    return max(heights)+.008 if heights else -.1
for vertex in cloth.data.vertices:vertex.co.z=max(vertex.co.z,contact_height(vertex))
cloth.data.update()
smooth=cloth.modifiers.new('Cotton_contact_smoothing','SMOOTH');smooth.factor=.6;smooth.iterations=3
bpy.ops.object.modifier_apply(modifier=smooth.name)
for vertex in cloth.data.vertices:vertex.co.z=max(vertex.co.z,contact_height(vertex))
cloth.data.update()
# Compress the sheet against the torso beneath the cupped palms. This leaves
# bare hands above the cloth without cutting holes in the shroud.
for vertex in cloth.data.vertices:
    x,y=vertex.co.x,vertex.co.y
    weight=math.exp(-((x+.015)/.17)**6-(y/.18)**6)
    if weight>.001:
        hit,_,_,_=bvh.ray_cast(Vector((x,y,1)),Vector((0,0,-1)))
        support=hit.z if hit is not None else .23
        height=support+.005+(.0015 if vertex.normal.z>0 else -.0003)
        vertex.co.z-=max(0,vertex.co.z-height)*weight
cloth.data.update()
bpy.data.objects.remove(collider,do_unlink=True)
linen=bpy.data.materials.new('funeral_unbleached_cotton');linen.diffuse_color=(.44,.405,.32,1);linen.use_nodes=True;p=linen.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=linen.diffuse_color;p.inputs['Roughness'].default_value=.97
cloth.data.materials.append(linen)
# Hands stay uncovered above the continuous sheet and cradle the lotus stem.

# Small square cloth support with compressed edges under the occiput.
bpy.ops.mesh.primitive_cube_add(size=1,location=(-.76,0,.035));pillow=bpy.context.object;pillow.name='sok_flat_funeral_pillow';pillow.dimensions=(.29,.29,.045);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bevel=pillow.modifiers.new('Compressed_cotton_edges','BEVEL');bevel.width=.025;bevel.segments=4;bpy.ops.object.modifier_apply(modifier=bevel.name)
for p in pillow.data.polygons:p.use_smooth=True
pillow.data.materials.append(linen)

# Export body subdivision explicitly as topology-stable baked morphs.
sub=body.modifiers.get('Facial_surface');sub.levels=0;sub.render_levels=0
# 13k quads with smooth normals preserve authored anatomy without a 100k runtime mesh.
objects=[body,cloth,pillow,lotus,*eyes]
for o in bpy.context.selected_objects:o.select_set(False)
for o in objects:o.select_set(True)
OUT.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(OUT),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_morph=True,export_morph_normal=True,export_animations=False,export_image_format='JPEG',export_jpeg_quality=94)
print('EXPORTED',OUT,OUT.stat().st_size,flush=True)
# Source file contains packed textures and all five editable pose keys.
source=ROOT/'art-source/characters/sok';source.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(source/'sok-corpse.blend'))
# Neutral authoring preview for anatomy / cloth inspection.
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.world.color=(.05,.05,.05)
bpy.ops.object.camera_add(location=(-1.45,-1.6,1.15));camera=bpy.context.object;camera.rotation_euler=(Vector((-.35,0,.12))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=60;scene.camera=camera
for loc,power,size in [((-1,-1,2),160,1.2),((.4,.6,1.3),65,1)]:
    bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(Vector((0,0,.1))-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.filepath=str(ROOT/'debug-shots/sok-anatomy-preview.png');bpy.ops.render.render(write_still=True)
