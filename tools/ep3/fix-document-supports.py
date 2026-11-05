"""Seat story documents and retain their interaction ownership and ink."""
import bpy
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/areas'),str(ROOT/'tools/ep3')]
from realism_scene import Craft
from dread_scene import support_documents
from compact_source import compact_source
collection=bpy.data.collections['ep3_area_village']
craft=Craft.__new__(Craft)
craft.coll=collection
craft.root=bpy.data.objects['ep3_realism']
craft.m={'wood':bpy.data.materials['M_ep3_wood'],'dark':bpy.data.materials['M_ep3_dark']}
support_documents(craft,collection)
compact_source()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
print('EP3 story documents have physical supports',flush=True)
