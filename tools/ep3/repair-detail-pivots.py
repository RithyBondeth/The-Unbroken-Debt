"""Repair rotated detail boxes in an older source without rebuilding its art.
Also writes parent-space GLTF offsets for the matching already-optimized asset.
blender -b art-source/blender/ep3/ep3_area_village.blend -P tools/ep3/repair-detail-pivots.py
"""
import bpy,json
from mathutils import Vector
from pathlib import Path

prefixes=('stove_charcoal_piece','real_waterlogged_patient_record',
          'real_flood_debris','ep3_finish_market_louver')
offsets={}
for obj in bpy.data.collections['ep3_area_village'].objects:
    if obj.type!='MESH' or not obj.name.startswith(prefixes) or obj.get('ep3_detail_pivot_centered'):continue
    centre=sum((Vector(corner) for corner in obj.bound_box),Vector())/8
    delta=centre-obj.rotation_euler.to_matrix()@centre
    offsets[obj.name]=[delta.x,delta.z,-delta.y]
    for vertex in obj.data.vertices:vertex.co-=centre
    obj.location+=centre
    obj['ep3_detail_pivot_centered']=True
Path('/tmp/ep3-detail-pivot-offsets.json').write_text(json.dumps(offsets))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
print('Episode 3 detail pivots repaired:',len(offsets),flush=True)
