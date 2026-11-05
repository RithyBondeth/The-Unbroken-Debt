"""Update only roof joints in the editable production area; retain all other scenery."""
import bpy,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/areas'));sys.path.insert(0,str(ROOT/'tools/ep3'))
from roof_joint import roof_joint
collection=bpy.data.collections['ep3_area_village'];world=bpy.data.objects['village_axes']
for obj in list(collection.objects):
    if obj.name.startswith(('escape_turn','col_escape_turn')):bpy.data.objects.remove(obj,do_unlink=True)
layout=json.loads((ROOT/'src/episodes/ep3/data/village-layout.json').read_text())
for i,point in enumerate(layout['escape']):roof_joint(collection,bpy.data.materials['M_ep3_wood'],'escape_turn_'+str(i),point,world)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
