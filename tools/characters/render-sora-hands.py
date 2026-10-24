"""Neutral-light proof of the actual anatomical mesh, not a generated mockup."""
import bpy,math,sys
from mathutils import Vector
from pathlib import Path
r=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(r/'art-source/characters/sora/sora-hands.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
detail='--detail' in sys.argv
scene.render.resolution_x=1000 if detail else 600;scene.render.resolution_y=1000 if detail else 800;scene.render.resolution_percentage=100
scene.world.color=(.15,.15,.15);scene.view_settings.view_transform='AgX'
bpy.ops.object.camera_add(location=(0,.04 if detail else -.045,-.75));cam=bpy.context.object;cam.rotation_euler=(0,math.pi,0);cam.data.type='ORTHO';cam.data.ortho_scale=.205 if detail else .43;scene.camera=cam
lights=[((-.18,.14,-.15),1.5,.18),((.2,-.1,-.25),1,.3)] if detail else [((-.22,.22,-.32),8,.35),((.25,-.1,-.25),6,.4),((0,.2,.25),8,.25)]
for at,power,size in lights:
 bpy.ops.object.light_add(type='AREA',location=at);l=bpy.context.object;l.data.energy=power;l.data.shape='DISK';l.data.size=size;l.rotation_euler=(-l.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(r/'debug-shots'/('sora_hand_skin_detail.png' if detail else 'sora_hand_anatomical_preview.png'));bpy.ops.render.render(write_still=True)
