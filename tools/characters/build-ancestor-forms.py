"""Build original guardian forms from the user's village shrine photographs.
blender -b -P tools/characters/build-ancestor-forms.py
"""
import bpy,sys,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/characters'))
from ancestor_forms import build_effigy
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
sets={}
for name,seated,variant in [('ancestor_shadow',False,0),('ancestor_seated_a',True,0),('ancestor_seated_b',True,1)]:
    before=set(bpy.data.objects)
    parts=build_effigy(name,seated,variant)
    coll=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(coll)
    for o in parts:
        for c in list(o.users_collection):c.objects.unlink(o)
        coll.objects.link(o)
    sets[name]=parts
    print(name,'ready:',sum(len(o.data.polygons) for o in parts),'faces',flush=True)
# Packed editable source, including the anatomical poses and all cotton layers.
for img in bpy.data.images:
    if img.source=='FILE':img.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art-source/characters/ancestors/ancestor-forms.blend'))
(ROOT/'art-export/ep1').mkdir(parents=True,exist_ok=True)
for name,parts in sets.items():
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    out=ROOT/'art-export/ep1/neakta_shadow.glb' if name=='ancestor_shadow' else ROOT/f'art-export/{name}.glb'
    bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_extras=True,export_cameras=False,export_lights=False)
# Neutral, well-lit inspection exposes any modelling problems before night grading.
for o in bpy.data.objects:
    if o.type=='MESH':o.hide_render=o not in sets['ancestor_shadow']
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16
world=scene.world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.13,.14,1)
for pos,power,size in [((2,-4,5),650,4),((-3,-1,2),420,3),((0,3,4),700,3)]:
    data=bpy.data.lights.new('inspection_softbox','AREA');data.energy=power;data.shape='DISK';data.size=size
    o=bpy.data.objects.new(data.name,data);scene.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,1.3))-o.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('inspection_camera');o=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(o);scene.camera=o;o.location=(2.6,-5,2.4);o.rotation_euler=(Vector((0,0,1.3))-o.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=2.9
scene.render.resolution_x=900;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.filepath='/tmp/ancestor-standing-inspection.png';bpy.ops.render.render(write_still=True)
for o in bpy.data.objects:
    if o.type=='MESH':o.hide_render=o not in sets['ancestor_seated_a']
o=scene.camera;o.location=(1.5,-3.3,1.65);o.rotation_euler=(Vector((0,0,.6))-o.location).to_track_quat('-Z','Y').to_euler();camera.ortho_scale=1.6
scene.render.filepath='/tmp/ancestor-seated-inspection.png';bpy.ops.render.render(write_still=True)
