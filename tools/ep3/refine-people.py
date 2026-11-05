"""Refresh actor garments and measured lamp supports without regenerating scenery."""
import bpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools/areas'), str(ROOT/'tools/ep3')]
from realism_scene import Craft
from realism_materials import make_materials
from human_anatomy import replace_existing
from cinematic_scene import clothe_people
from human_finish import finish_people
from dread_scene import ground_props
from compact_source import compact_source

collection = bpy.data.collections['ep3_area_village']
craft = Craft.__new__(Craft)
craft.coll = collection
craft.root = bpy.data.objects['ep3_realism']
craft.m = make_materials()
replace_existing(collection)
clothe_people(craft, collection)
finish_people(craft, collection)
ground_props(collection)
compact_source()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, compress=True)
print('EP3 clothing and lamp supports refined', flush=True)
