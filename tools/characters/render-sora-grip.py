"""Close view of the authored hand gripping the actual shipped lamp geometry."""
import bpy,math
from pathlib import Path
from mathutils import Vector
r=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(r/'art-source/characters/sora/sora-hands.blend'))
hand=bpy.data.objects['sora_hand'];hand.data.shape_keys.key_blocks['lamp'].value=1
hand.scale=(.85,)*3;hand.location=(.005,.24,.005)
with bpy.data.libraries.load(str(r/'art-source/blender/shared/shared_lamp.blend'),link=False) as (src,dst):
 dst.objects=[n for n in src.objects if n in ['Lantern_01','Lantern_01_glass']]
for obj in dst.objects:
 vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
 mesh=bpy.data.meshes.new('Grip_reference_'+obj.name)
 mesh.from_pydata([(v.x,v.z,v.y) for v in vertices],[],[tuple(reversed(p.vertices)) for p in obj.data.polygons]);mesh.update()
 for mat in obj.data.materials:mesh.materials.append(mat)
 for a,b in zip(mesh.polygons,obj.data.polygons):a.material_index=b.material_index;a.use_smooth=True
 if obj.data.uv_layers.active:
  uv=mesh.uv_layers.new(name='UVMap')
  for a,b in zip(mesh.polygons,obj.data.polygons):
   for i,j in zip(a.loop_indices,reversed(b.loop_indices)):uv.data[i].uv=obj.data.uv_layers.active.data[j].uv
 ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.resolution_x=1000;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.world.color=(.1,.1,.1);s.view_settings.view_transform='AgX'
bpy.ops.object.camera_add(location=(0,.235,-.65));c=bpy.context.object;c.rotation_euler=(0,math.pi,0);c.data.type='ORTHO';c.data.ortho_scale=.235;s.camera=c
for at,power,size in [((-.18,.35,-.15),2,.18),((.2,.16,-.25),1,.3)]:
 bpy.ops.object.light_add(type='AREA',location=at);l=bpy.context.object;l.data.energy=power;l.data.shape='DISK';l.data.size=size;l.rotation_euler=(Vector((0,.24,0))-l.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(r/'debug-shots/sora_lamp_grip_detail.png');bpy.ops.render.render(write_still=True)
