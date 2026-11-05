"""Finalize contact constraints after an incremental character/environment rebuild."""
import bpy
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/areas'),str(ROOT/'tools/ep3')]
from realism_scene import Craft
from human_finish import finish_faces
from dread_scene import anchor_boats, mature_forest

collection=bpy.data.collections['ep3_area_village']
craft=Craft.__new__(Craft)
craft.coll=collection
craft.root=bpy.data.objects['ep3_realism']
craft.m={'bamboo':bpy.data.materials['M_ep3_bamboo']}
finish_faces(craft,collection)
mature_forest(collection)
anchor_boats(collection)
oar=bpy.data.objects.get('borrowed_oar')
if oar and not oar.get('ep3_contact_fixed'):
    matrix=oar.matrix_world.copy()
    matrix.translation.z-=.13
    oar.matrix_world=matrix
    oar['ep3_contact_fixed']=True
from compact_source import compact_source
compact_source()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
print('EP3 dread source finalized',flush=True)
