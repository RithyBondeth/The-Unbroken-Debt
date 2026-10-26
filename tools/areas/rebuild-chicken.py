"""Replace only the chicken in the current shrine, retaining the plate and scene.

blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/rebuild-chicken.py
Writes /tmp/unbroken-chicken.glb for update-shrine-glb.mjs, and a studio preview.
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0,os.path.dirname(__file__))
from chicken import skin_textures, whole_chicken
from khmer import join

shrine=bpy.data.objects['neakta_shrine']
original_matrix=shrine.matrix_world.copy()
unchanged={o.name:o.matrix_world.copy() for o in bpy.data.objects if o is not shrine}
# The previous chicken was the only geometry assigned to this material.
indices={i for i,mat in enumerate(shrine.data.materials)
         if mat and (mat.name=='M_rotten_meat' or mat.name.startswith('M_chicken_'))}
assert indices, 'No old chicken material found'
bm=bmesh.new();bm.from_mesh(shrine.data)
old=[face for face in bm.faces if face.material_index in indices]
assert old, 'No old chicken faces found'
bmesh.ops.delete(bm,geom=old,context='FACES')
bm.to_mesh(shrine.data);bm.free()
bpy.context.view_layer.objects.active=shrine
shrine.select_set(True)
bpy.ops.object.material_slot_remove_unused()
for mesh in list(bpy.data.meshes):
    if mesh.users==0 and mesh.name.startswith(('chicken_','neakta_chicken_')):
        bpy.data.meshes.remove(mesh)
for mat in list(bpy.data.materials):
    if mat.name.startswith('M_chicken_') and mat.users==0:bpy.data.materials.remove(mat)
skin_textures()
print('Skin albedo, normal and roughness maps generated',flush=True)
# Shrine-local plate centre: (-.25,-.28,.33), shrine at (-3.9,-34.9), facing east.
chicken=whole_chicken(shrine.users_collection[0],(-3.62,-35.15,.35),math.pi/2)
print(f'Whole chicken: {len(chicken.data.polygons)} faces',flush=True)
# Studio preview is made before the join; the working scene is saved without it.
preview=chicken.copy();preview.data=chicken.data.copy()
preview.name='chicken_studio_preview'
shrine=join([shrine,chicken],'neakta_shrine')
assert shrine.matrix_world==original_matrix
for name,matrix in unchanged.items():
    assert bpy.data.objects[name].matrix_world==matrix, f'Unrelated object moved: {name}'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
bpy.ops.object.select_all(action='DESELECT');shrine.select_set(True)
bpy.ops.export_scene.gltf(filepath='/tmp/unbroken-chicken.glb',export_format='GLB',use_selection=True,
                          export_extras=True,export_yup=True,export_apply=True,
                          export_cameras=False,export_lights=False)
print('Shrine exported; unrelated transforms preserved',flush=True)
# A neutral art inspection complements the in-game lamplight review.
scene=bpy.data.scenes.new('Chicken studio')
scene.collection.objects.link(preview)
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1100;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Chicken studio world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.10,.11,.13,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='AgX'
target=Vector((-3.62,-35.15,.43))
for name,offset,power,size in [('key',(.4,-.3,.65),45,.45),('fill',(-.4,.1,.3),20,.4)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=target+Vector(offset)
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('chicken-camera');camera=bpy.data.objects.new('chicken-camera',data)
scene.collection.objects.link(camera);camera.location=target+Vector((.48,-.42,.56))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=.43;scene.camera=camera
scene.render.image_settings.file_format='PNG';scene.render.filepath=os.path.join(os.getcwd(),'debug-shots','chicken-studio.png')
bpy.ops.render.render(write_still=True,scene=scene.name)
