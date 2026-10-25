"""Focused update of the two filled funeral stands and their Khmer banners.

Run drawings first: npm run drawings -- ep1 funeral_tribute_banner
blender -b art-source/blender/ep1/ep1_area_village.blend \
  -P tools/areas/rebuild-floral-tributes.py -- /tmp/floral-tributes.glb

Compress the banner with UASTC and the geometry with meshopt. Merge the focused
export with update-funeral-glb.mjs ... --reuse-materials to retain the existing
compressed flower/wood/cloth textures and all unrelated village geometry.
"""
import json
import os
import sys
import bpy

sys.path.insert(0,os.path.dirname(__file__))
from funeral import floral_stand

filepath=bpy.data.filepath;modified=os.stat(filepath).st_mtime_ns
coll=bpy.data.collections['ep1_area_village']
for img in bpy.data.images:
    if os.path.basename(img.filepath)=='T_ep1_funeral_tribute_banner_BC.png':
        img.reload()
names=[f'funeral_wreath_{i}' for i in range(2)]
old=[bpy.data.objects[name] for name in names]
unchanged={o.name:(o.matrix_world.copy(),o.data) for o in bpy.data.objects if o not in old}
# Use the existing craft materials: this pass changes two arrangements only.
f={}
for mat in bpy.data.materials:
    if mat.name.startswith('M_funeral_') and not mat.name.rsplit('.',1)[-1].isdigit():
        f[mat.name[len('M_funeral_'):]]=mat
f['lacquer']=(bpy.data.materials.get('M_funeral_coffin_lacquer')
              or bpy.data.materials.get('M_lacquer') or f['wood'])
m={'_funeral':f}
for obj in old:
    data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
    if data.users==0:bpy.data.meshes.remove(data)
for i,side in enumerate((-1,1)):
    floral_stand(coll,m,side*2.20,5.68,.31,i)
bpy.context.view_layer.update()
for name,(matrix,data) in unchanged.items():
    obj=bpy.data.objects.get(name)
    assert obj and obj.matrix_world==matrix and obj.data==data,f'Unrelated object changed: {name}'
for name in names:
    obj=bpy.data.objects[name]
    assert obj['filled_center'] and obj['center_blooms']==110
    assert any(mat.name=='M_funeral_condolence_banner' for mat in obj.data.materials)
assert os.stat(filepath).st_mtime_ns==modified,'Village was saved by another task; rerun against its latest version'
bpy.ops.wm.save_as_mainfile(filepath=filepath)
print(f'Two filled floral tributes rebuilt; preserved {len(unchanged)} unrelated objects.',flush=True)
if '--' in sys.argv:
    destination=sys.argv[sys.argv.index('--')+1]
    bpy.ops.object.select_all(action='DESELECT')
    for name in names:bpy.data.objects[name].select_set(True)
    bpy.ops.export_scene.gltf(filepath=destination,export_format='GLB',use_selection=True,
        export_extras=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False)
    with open(destination+'.json','w') as stream:
        json.dump({'remove':names,'required':names,'created':names},stream,indent=2)
