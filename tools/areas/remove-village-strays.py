"""Remove strays from the village blend: library prototypes that leaked into the
exported collection (they stood at the origin, in front of the funeral pavilion)
and the oil-bottle pickup on the floor of Sok's room (2026-11-07, at the user's request).

blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/remove-village-strays.py -- names.json

Writes the removed node names, so a focused merge can drop them from the GLB too.
"""
import json
import sys

import bpy

coll = bpy.data.collections['ep1_area_village']
strays = {o for o in coll.objects if (o.name.startswith('proto_') and o.parent is None)
          or o.name.removeprefix('col_') in ('interact_oil_sok', 'oil_sok')}
for obj in list(strays):
    strays.update(obj.children_recursive)
names = sorted(o.name for o in strays)
protos = bpy.data.collections.get('_protos')
for obj in strays:
    if obj.name.startswith('proto_') or (obj.parent and obj.parent.name.startswith('proto_')):
        # Keep prototypes as copy sources, just out of the exported collection.
        if protos and obj.name not in protos.objects:
            protos.objects.link(obj)
        coll.objects.unlink(obj)
    else:
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Removed strays:', names, flush=True)
if '--' in sys.argv:
    with open(sys.argv[sys.argv.index('--') + 1], 'w') as stream:
        json.dump(names, stream, indent=2)
