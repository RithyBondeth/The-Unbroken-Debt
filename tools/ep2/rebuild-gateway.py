"""Focused gateway rebuild; the full area builder uses the same build_gateway function."""
import os,sys
import bpy
sys.path.insert(0,os.path.abspath('tools/areas'))
from pagoda_gateway import build_gateway
path=os.path.abspath('art-source/blender/ep2/ep2_area_pagoda.blend')
bpy.ops.wm.open_mainfile(filepath=path)
coll=bpy.data.collections['ep2_area_pagoda'];world=bpy.data.objects['pagoda_axes']
for o in list(coll.objects):
    if o.name.startswith(('gateway_','col_gateway_','gate_wall','col_gate_wall','gate_pier','col_gate_pier','gate_spire','gate_lintel','gate_lotus_relief','pier_floral_relief','gate_roof','gate_gable','gate_bargeboard','gate_finial','gate_ridge','gate_rafter','gate_purlin','gate_eave')):
        bpy.data.objects.remove(o,do_unlink=True)
m={k:bpy.data.materials['M_ep2_'+k] for k in ['stone','bronze']}
before=set(coll.objects);build_gateway(coll,m)
for o in coll.objects:
    if o not in before:o.parent=world
bpy.ops.wm.save_as_mainfile(filepath=path)
print('GATEWAY_REBUILT',flush=True)
