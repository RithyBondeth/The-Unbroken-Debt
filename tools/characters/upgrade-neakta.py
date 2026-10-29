"""Focused upgrade; preserves the seated figures and their material maps.
blender -b art-source/characters/ancestors/ancestor-forms.blend -P tools/characters/upgrade-neakta.py
"""
import bpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/characters'))
from ancestor_motion import prepare_standing, standing_surface

parts = list(bpy.data.collections['ancestor_shadow'].objects)
prepare_standing(parts)
standing_surface(parts)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'art-source/characters/ancestors/ancestor-forms.blend'))
bpy.ops.object.select_all(action='DESELECT')
for obj in parts:
    obj.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=str(ROOT / 'art-export/ep1/neakta_shadow.glb'),
    export_format='GLB', use_selection=True, export_yup=True,
    export_extras=True, export_morph=True, export_morph_normal=True,
    export_cameras=False, export_lights=False,
)
