"""Bring an existing editable scene into parity with finish-village.mjs, without rebuilding.
blender -b art-source/blender/ep3/ep3_area_village.blend -P tools/ep3/repair-lettering.py
"""
import bpy,re
pattern=re.compile(r'^(clinic_facade|ward_sign|attic_sign|pump_label|safe_numerals|debt_name|tin_cross(?:\.\d+)?)$')
for obj in bpy.data.objects:
    if pattern.match(obj.name) and not obj.get('ep3_lettering_corrected'):
        obj.scale.x*=-1;obj['ep3_lettering_corrected']=True
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
