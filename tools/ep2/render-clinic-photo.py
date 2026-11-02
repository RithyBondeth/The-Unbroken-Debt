"""Render the physical 1920 contact print from the chapter's CC0 humans and Episode 1 kit.
blender -b --factory-startup -P tools/ep2/render-clinic-photo.py
"""
from pathlib import Path
import bpy,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
source=(ROOT/'tools/ep2/build-cinematics.py').read_text().split("wood=library_material")[0]
exec(compile(source,str(ROOT/'tools/ep2/build-cinematics.py'),'exec'),globals())
wood=library_material('weathered_brown_planks','clinic_deck',tint=(.55,.45,.31))
cloth=library_material('rough_linen','physician_cotton',colour=(.72,.68,.57))
indigo=library_material('rough_linen','mother_sampot',colour=(.12,.15,.13))
skirt=library_material('rough_linen','mother_wrap',colour=(.28,.18,.12))
# The contact print has its own staged, editable set. It is not exported as live scenery.
sok=anatomy('clinic_sok',old=True);sok.location=(-.45,0,.02)
sok.data.materials[1]=cloth
sok.data.materials[2]=indigo
garment('physician_coat_upper',sok,[(.17,.79),(.18,.9),(.23,1.05),(.25,1.18),(.2,1.30),(.07,1.35)],cloth,pleats=.002)
garment('physician_coat_hem',sok,[(.22,.35),(.24,.4),(.22,.65),(.17,.85)],cloth,pleats=.003)
mother=anatomy('clinic_mother');mother.location=(.43,0,.02)
mother.data.materials[1]=cloth;mother.data.materials[2]=skirt
hairmat=plain('mother_dark_hair',(.022,.018,.012),rough=.9)
height=max(v.co.z for v in mother.data.vertices)
faces=[list(p.vertices) for p in mother.data.polygons if sum(mother.data.vertices[i].co.z for i in p.vertices)/len(p.vertices)>height*.965 or (sum(mother.data.vertices[i].co.z for i in p.vertices)/len(p.vertices)>height*.88 and sum(mother.data.vertices[i].co.y for i in p.vertices)/len(p.vertices)>0)]
mesh=bpy.data.meshes.new('mother_pinned_hair');mesh.from_pydata([v.co+v.normal*.004 for v in mother.data.vertices],[],faces);mesh.materials.append(hairmat)
hair=bpy.data.objects.new('mother_pinned_hair',mesh);COL.objects.link(hair);hair.parent=mother
for p in mesh.polygons:p.use_smooth=True
garment('mother_skirt',mother,[(.26,.06),(.28,.14),(.26,.45),(.21,.78),(.16,.87)],skirt,pleats=.006)
garment('mother_blouse',mother,[(.2,.72),(.25,.84),(.25,.99),(.22,1.09),(.17,1.16),(.075,1.20)],cloth,center=(0,-.025,0),pleats=.004)
# Cloth has room over the pregnant abdomen, rather than a bare skin sphere.
bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,location=(.43,-.11,.88))
bump=bpy.context.object;bump.name='mother_pregnant_blouse';bump.scale=(.225,.185,.22);bump.data.materials.append(cloth)
for p in bump.data.polygons:p.use_smooth=True
box('floating_clinic_deck',COL,-2.8,2.8,-1.1,2.8,-.15,0,wood)
for x in [-2.4,2.4]:
 for y in [.7,2.5]:box('clinic_bamboo_post',COL,x-.045,x+.045,y-.045,y+.045,0,2.9,wood)
box('clinic_back_wall',COL,-2.5,2.5,2.5,2.6,0,2.4,wood)
box('clinic_roof',COL,-2.9,2.9,.55,2.9,2.6,2.72,wood)
# A small painted sign, legible in the raised photograph.
box('clinic_sign',COL,-1.4,1.4,.54,.56,2.2,2.55,cloth)
curve=bpy.data.curves.new('clinic_sign_lettering','FONT');curve.body='TONLE SAP  /  1920';curve.align_x='CENTER';curve.size=.18
text=bpy.data.objects.new('clinic_sign_lettering',curve);COL.objects.link(text);text.location=(0,.52,2.27);text.rotation_euler=(math.pi/2,0,0);text.data.materials.append(indigo)
water=plain('clinic_water',(.16,.18,.16),rough=.36)
box('river',COL,-100,100,-100,100,-.4,-.36,water)
world=bpy.data.worlds.new('overcast_1920');bpy.context.scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.61,.52,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65
light=bpy.data.lights.new('cloud_light','AREA');light.energy=700;light.shape='DISK';light.size=5
obj=bpy.data.objects.new('cloud_light',light);bpy.context.scene.collection.objects.link(obj);obj.location=(-3,-4,6);obj.rotation_euler=(Vector((0,1,1))-obj.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('contact_print_camera');camera=bpy.data.objects.new('contact_print_camera',cam);bpy.context.scene.collection.objects.link(camera)
camera.location=(.05,-6.2,2.1);camera.rotation_euler=(Vector((0,.5,1.35))-camera.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=5.6
scene=bpy.context.scene;scene.camera=camera;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=768;scene.render.resolution_y=576;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.4
# Low saturation and warm illumination give the same aged photographic palette as the game.
scene.render.filepath=str(ROOT/'public/assets/ep2/clinic_photo.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art-source/blender/ep2/clinic_photo.blend'))
bpy.ops.render.render(write_still=True)
