"""Rebuild garment regions on the existing neutral anatomy and pose targets."""
import bpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools/areas'), str(ROOT/'tools/ep3')]
from realism_scene import Craft
from human_anatomy import restore_topology
from cinematic_scene import clothe_people
from human_finish import finish_people
from compact_source import compact_source

collection = bpy.data.collections['ep3_area_village']
craft = Craft.__new__(Craft)
craft.coll = collection
craft.root = bpy.data.objects['ep3_realism']
craft.m = {key:bpy.data.materials[name] for key,name in {
    'cotton':'M_ep3_real_stained_cotton', 'curtain':'M_ep3_real_rotten_muslin',
    'edge':'M_ep3_real_worn_hems', 'bamboo':'M_ep3_bamboo',
}.items()}
for body in [o for o in collection.objects if o.type == 'MESH' and o.name.endswith('_body')]:
    for obj in list(body.children):
        if obj.name.startswith('ep3_finish_') or obj.name.endswith('_shorts'):
            bpy.data.objects.remove(obj, do_unlink=True)
    restore_topology(body)
    print('EP3 restored garment regions:',body.name,flush=True)
clothe_people(craft, collection, reuse_materials=True)
finish_people(craft, collection)
compact_source()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, compress=True)
print('EP3 anatomical garment regions refitted', flush=True)
