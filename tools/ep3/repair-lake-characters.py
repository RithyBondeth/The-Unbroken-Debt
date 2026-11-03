"""Repair only the two lake characters in the editable production area."""
import bpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/areas'));sys.path.insert(0,str(ROOT/'tools/ep3'))
from lake_characters import finish_lake_characters
collection=bpy.data.collections['ep3_area_village']
for obj in list(collection.objects):
    if obj.name.startswith(('kanha_hair_strand','kanha_wet_scalp','kanha_milky_eye','pich_cotton_shirt','pich_wrapped_sampot')):bpy.data.objects.remove(obj,do_unlink=True)
m={key:bpy.data.materials['M_ep3_'+key] for key in ['ivory','blue']}
finish_lake_characters(collection,bpy.data.objects['kanha'],bpy.data.objects['kanha_body'],bpy.data.objects['pich_body'],m)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
