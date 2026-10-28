"""Add/rebuild only the drawing morph, preserving every existing hand pose and texture."""
import bpy, json, struct, sys
from pathlib import Path
from mathutils import Vector
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_drawing_grip import drawing_grip, CONTACT, NIB_DIRECTION
source = ROOT/'art-source/characters/sora/sora-hands.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = bpy.data.objects['Sora_hand_authoring_rig']
body = bpy.data.objects['sora_anatomical_hand']
anatomy = bpy.data.objects['sora_hand']
wrist = rig.data.bones['wrist.L'].head_local
ay = (rig.data.bones['finger3-3.L'].tail_local - wrist).normalized()
ax = rig.data.bones['finger2-1.L'].head_local - rig.data.bones['finger5-1.L'].head_local
ax = (ax - ay * ax.dot(ay)).normalized()
az = -ax.cross(ay).normalized()
origin = wrist + ay * .32
for b in rig.pose.bones:
    b.rotation_mode = 'QUATERNION'
    b.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()
tips = drawing_grip(rig, ax, ay, az)
ob = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh = ob.to_mesh()
positions = []
for v in mesh.vertices:
    d = v.co - origin
    positions.append(Vector((d.dot(ax)*.108, d.dot(ay)*.108, d.dot(az)*.108)))
assert len(positions) == len(anatomy.data.vertices)
ob.to_mesh_clear()
key = anatomy.data.shape_keys.key_blocks.get('drawing') or anatomy.shape_key_add(name='drawing')
for v, p in zip(key.data, positions): v.co = p
real = anatomy.data
real.calc_loop_triangles()
lookup = {}; sourceidx = []; indices = []
layer = real.uv_layers.active
for tri in real.loop_triangles:
    for loopidx in tri.loops:
        vi = real.loops[loopidx].vertex_index
        uv = layer.data[loopidx].uv
        k = (vi, round(uv.x,7), round(uv.y,7))
        if k not in lookup:
            lookup[k] = len(lookup); sourceidx.append(vi)
        indices.append(lookup[k])
for i in range(0,len(indices),3): indices[i+1],indices[i+2]=indices[i+2],indices[i+1]
path = ROOT/'public/assets/shared/sora_hand.mesh'
data = path.read_bytes()
hsize = struct.unpack_from('<I',data,4)[0]
header = json.loads(data[8:8+hsize])
assert header['vertexCount'] == len(sourceidx)
existing_indices = np.frombuffer(data,dtype='<u4',count=len(indices),offset=8+hsize)
assert np.array_equal(existing_indices,np.array(indices))
for v,p in zip(real.vertices,positions): v.co=p
real.update()
packed = []
for i in sourceidx:
    v=real.vertices[i]; packed.extend((*v.co,*v.normal))
# Strip an older drawing morph if this script is rerun.
fixed = header['indexCount']*4+header['vertexCount']*8
base = data[8+hsize:8+hsize+fixed+6*header['vertexCount']*24]
header['poses'] = ['relaxed','lamp','phone','journal','pinch','reach','drawing']
encoded = json.dumps(header,separators=(',',':')).encode(); encoded += b' '*((-len(encoded))%4)
path.write_bytes(b'SORA'+struct.pack('<I',len(encoded))+encoded+base+np.array(packed,dtype='<f4').tobytes())
for v,p in zip(real.vertices,real.shape_keys.key_blocks['Basis'].data): v.co=p.co
real.update()
source.with_suffix('.drawing.json').write_text(json.dumps({'contact':list(CONTACT),'nibDirection':list(NIB_DIRECTION),'fingertips':tips},indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(source))
bpy.ops.object.select_all(action='DESELECT')
anatomy.select_set(True)
bpy.context.view_layer.objects.active = anatomy
bpy.ops.export_scene.gltf(filepath=str(source.with_suffix('.glb')), export_format='GLB', use_selection=True, export_morph=True, export_yup=False)
print('DRAWING_GRIP' ,json.dumps(tips),flush=True)
