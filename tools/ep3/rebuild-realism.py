"""Rebuild the realism layer without touching story roots or collision geometry.
blender -b art-source/blender/ep3/ep3_area_village.blend -P tools/ep3/rebuild-realism.py
"""
import bpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/areas'));sys.path.insert(0,str(ROOT/'tools/ep3'))
from realism_scene import apply_realism
area=bpy.data.collections['ep3_area_village']
apply_realism(area,bpy.data.objects['village_axes'])
from compact_source import compact_source
compact_source()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
print('EP3 realism scene:',len(area.all_objects),'objects',flush=True)
