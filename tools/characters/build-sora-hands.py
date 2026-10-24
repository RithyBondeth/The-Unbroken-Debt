"""Build Sora's continuous anatomical female hand from CC0 MakeHuman data.
Writes editable Blender source, textured GLB, and a compact runtime pose mesh.
Run after fetch-sora-source.py. Blender supplies the subdivision and skin deformer.
"""
import bpy,json,math,sys,struct,hashlib,shutil
from pathlib import Path
from mathutils import Vector,Quaternion
import numpy as np
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'art-source/library/makehuman-sora';OUT=ROOT/'public/assets/shared'
OUT.mkdir(parents=True,exist_ok=True);EDIT=ROOT/'art-source/characters/sora';EDIT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
verts=[];uvs=[];faces=[];faceuv=[];group=''
for line in (SRC/'base.obj').read_text().splitlines():
 a=line.split()
 if not a:continue
 if a[0]=='v':verts.append(Vector(map(float,a[1:4])))
 elif a[0]=='vt':uvs.append(tuple(map(float,a[1:3])))
 elif a[0]=='g':group=a[1]
 elif a[0]=='f' and group=='body':
  p=[x.split('/') for x in a[1:]];faces.append([int(x[0])-1 for x in p]);faceuv.append([int(x[1])-1 for x in p])
for file in ['asian-female-young.target','universal-female-young-averagemuscle-averageweight.target']:
 for line in (SRC/file).read_text().splitlines():
  if line and not line.startswith('#'):
   a=line.split();verts[int(a[0])]+=Vector(map(float,a[1:4]))
skel=json.loads((SRC/'default.mhskel').read_text())
def joint(n):return sum((verts[i] for i in skel['joints'][n]),Vector())/len(skel['joints'][n])
def head(n):return joint(skel['bones'][n]['head'])
def tail(n):return joint(skel['bones'][n]['tail'])
wrist=head('wrist.L');ay=(tail('finger3-3.L')-wrist).normalized()
ax=head('finger2-1.L')-head('finger5-1.L');ax=(ax-ay*ax.dot(ay)).normalized();az=-ax.cross(ay).normalized()
origin=wrist+ay*.32;S=.108
# Coordinate space matches the existing camera hand: +Y fingers, +Z palm, +X thumb.
def local(v):
 d=v-origin;return Vector((d.dot(ax)*S,d.dot(ay)*S,d.dot(az)*S))
weights=json.loads((SRC/'default_weights.mhw').read_text())['weights']
sel=[];seluv=[]
for f,uv in zip(faces,faceuv):
 if all(verts[i].x>2.5 and -.24<local(verts[i]).y<.2 for i in f):sel.append(f);seluv.append(uv)
used=sorted({i for f in sel for i in f});remap={v:i for i,v in enumerate(used)}
mesh=bpy.data.meshes.new('Sora_continuous_hand_topology');mesh.from_pydata([verts[i] for i in used],[],[[remap[i] for i in f] for f in sel]);mesh.update()
uv=mesh.uv_layers.new(name='SkinUV')
for poly,indices in zip(mesh.polygons,seluv):
 for loop,i in zip(poly.loop_indices,indices):uv.data[loop].uv=uvs[i]
body=bpy.data.objects.new('sora_anatomical_hand',mesh);bpy.context.collection.objects.link(body)
for p in mesh.polygons:p.use_smooth=True
# Preserve the real weighted knuckle and thumb-web deformation.
arm=bpy.data.armatures.new('Sora_hand_authoring_rig');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for name,b in skel['bones'].items():
 bone=arm.edit_bones.new(name);bone.head=joint(b['head']);bone.tail=joint(b['tail'])
for name,b in skel['bones'].items():
 if b['parent']:arm.edit_bones[name].parent=arm.edit_bones[b['parent']]
bpy.ops.object.mode_set(mode='OBJECT')
for name,ws in weights.items():
 g=body.vertex_groups.new(name=name)
 for i,w in ws:
  if i in remap:g.add([remap[i]],w,'REPLACE')
mod=body.modifiers.new('Weighted_anatomical_finger_deformation','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True
sub=body.modifiers.new('Smooth_connected_skin','SUBSURF');sub.levels=2;sub.render_levels=2

def rotate(name,axis,angle):
 b=rig.pose.bones[name];q=b.bone.matrix_local.to_quaternion();b.rotation_mode='QUATERNION';b.rotation_quaternion=b.rotation_quaternion@(q.inverted()@Quaternion(axis,math.radians(angle))@q)
profiles={
 'relaxed':([10,18,8],[8,10,5],0),
 'lamp':([60,82,50],[25,38,25],70),
 'phone':([45,65,40],[20,32,22],64),
 'journal':([18,38,24],[8,12,5],8),
 'pinch':([65,82,55],[28,38,25],65),
 'reach':([0,4,2],[0,4,0],0),
}
def pose(name):
 for b in rig.pose.bones:b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion()
 finger,thumb,opp=profiles[name]
 for f in range(1,6):
  if f==1:rotate('finger1-1.L',az,-opp)
  for part in range(1,4):
   angle=thumb[part-1] if f==1 else finger[part-1]+(f-3)*2
   if name=='pinch' and f==2:angle=[26,48,26][part-1]
   rotate(f'finger{f}-{part}.L',ax,-angle)
 if name=='lamp':
  sys.path.insert(0,str(Path(__file__).resolve().parent))
  from sora_grip import lamp_grip
  lamp_grip(rig,ax,ay,az)
 bpy.context.view_layer.update()

def evaluated():
 deps=bpy.context.evaluated_depsgraph_get();ob=body.evaluated_get(deps);m=ob.to_mesh();p=[local(v.co) for v in m.vertices]
 # Keep quads and the source UVs for an editable, clean subdivided surface.
 f=[tuple(reversed(poly.vertices)) for poly in m.polygons]
 uv=[tuple(m.uv_layers.active.data[loop].uv) for poly in m.polygons for loop in reversed(poly.loop_indices)]
 ob.to_mesh_clear();return p,f,uv
poses={}
for name in profiles:
 pose(name);p,f,u=evaluated();poses[name]=p
 print('Pose',name,'verts',len(p),flush=True)
pose('reach');p,f,u=evaluated()
real=bpy.data.meshes.new('Sora_connected_female_hand');real.from_pydata(poses['relaxed'],[],f);real.update()
layer=real.uv_layers.new(name='SkinUV')
for loop,coord in zip(layer.data,u):loop.uv=coord
anatomy=bpy.data.objects.new('sora_hand',real);bpy.context.collection.objects.link(anatomy)
for poly in real.polygons:poly.use_smooth=True
anatomy.shape_key_add(name='Basis')
for name,data in poses.items():
 key=anatomy.shape_key_add(name=name);key.value=0
 for v,co in zip(key.data,data):v.co=co
# Crop only the arm/hand portion of the photo skin atlas; no unrelated body image ships.
image=bpy.data.images.load(str(SRC/'young_lightskinned_female_diffuse3.png'))
w,h=image.size;coords=np.array(u);lo=np.maximum(0,coords.min(axis=0)-.003);hi=np.minimum(1,coords.max(axis=0)+.003)
x0,y0=np.floor(lo*[w,h]).astype(int);x1,y1=np.ceil(hi*[w,h]).astype(int)
pixels=np.array(image.pixels[:],dtype=np.float32).reshape(h,w,4)[y0:y1,x0:x1,:]
crop=bpy.data.images.new('Sora_photo_skin',width=x1-x0,height=y1-y0,alpha=False)
crop.pixels.foreach_set(pixels.ravel());crop.filepath_raw=str(OUT/'sora_hand_skin.png');crop.file_format='PNG';crop.save();crop.pack()
for loop in layer.data:loop.uv=((loop.uv.x*w-x0)/(x1-x0),(loop.uv.y*h-y0)/(y1-y0))
# The material uses anatomical rest coordinates for folds, veins and pores.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sora_skin import build_skin
joints={(digit,part):(local(head(f'finger{digit}-{part}.L')),local(tail(f'finger{digit}-{part}.L'))) for digit in range(1,6) for part in range(1,4)}
build_skin(anatomy,crop,poses['reach'],f,joints,OUT)
# Remove the full body and rig from the presentation view, retaining editable authoring data.
body.hide_render=True;body.hide_set(True);rig.hide_render=True;rig.hide_set(True)
# Compact single-index mesh including UV splits; runtime mirrors for the other hand.
real.calc_loop_triangles();lookup={};indices=[];baseuv=[];sourceidx=[]
for tri in real.loop_triangles:
 for loopidx in tri.loops:
  vi=real.loops[loopidx].vertex_index;uv=tuple(layer.data[loopidx].uv);key=(vi,round(uv[0],7),round(uv[1],7))
  if key not in lookup:lookup[key]=len(lookup);sourceidx.append(vi);baseuv.extend(uv)
  indices.append(lookup[key])
# Blender basis was right-handed; converting z to camera LH reverses triangle winding.
for i in range(0,len(indices),3):indices[i+1],indices[i+2]=indices[i+2],indices[i+1]
# Normals are evaluated per posed mesh; UV splits reuse geometric vertex normals.
arrays=[]
for name,data in poses.items():
 for vertex,co in zip(real.vertices,data):vertex.co=co
 real.update();flat=[]
 for i in sourceidx:
  v=real.vertices[i];flat.extend((v.co.x,v.co.y,v.co.z,v.normal.x,v.normal.y,v.normal.z))
 arrays.append(np.array(flat,dtype='<f4'))
header={'version':1,'vertexCount':len(sourceidx),'indexCount':len(indices),'poses':list(poses),'texture':'sora_hand_skin.png','source':'MakeHuman CC0 anatomical female hand','bounds':[[min(v[k] for v in poses['reach']) for k in range(3)],[max(v[k] for v in poses['reach']) for k in range(3)]]}
encoded=json.dumps(header,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
with (OUT/'sora_hand.mesh').open('wb') as out:
 out.write(b'SORA');out.write(struct.pack('<I',len(encoded)));out.write(encoded);out.write(np.array(indices,dtype='<u4').tobytes());out.write(np.array(baseuv,dtype='<f4').tobytes())
 for array in arrays:out.write(array.tobytes())
# Restore a relaxed view, with palm facing the studio camera.
for v,co in zip(real.vertices,poses['relaxed']):v.co=co
real.update()
bpy.ops.object.select_all(action='DESELECT');anatomy.select_set(True);bpy.context.view_layer.objects.active=anatomy
bpy.ops.wm.save_as_mainfile(filepath=str(EDIT/'sora-hands.blend'))
bpy.ops.export_scene.gltf(filepath=str(EDIT/'sora-hands.glb'),export_format='GLB',use_selection=True,export_morph=True,export_yup=False)
print('HAND_ASSET',json.dumps(header),'atlas',x1-x0,y1-y0,flush=True)
