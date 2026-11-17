"""Points images whose files have moved back at this checkout. Patch scripts run
from git worktrees (../The-Unbroken-Debt-ep1, .claude/worktrees/...) saved
relative paths into those worktrees; once a worktree is removed the export
silently drops the texture. Any missing file whose path contains
`art-source/` is looked up under this checkout's art-source/ instead.

    blender -b --factory-startup art-source/blender/ep1/ep1_area_village.blend \\
        -P tools/areas/repair_image_paths.py
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
from kit import ROOT  # noqa: E402


def repair_image_paths():
    fixed, missing = [], []
    for img in bpy.data.images:
        if img.source != "FILE" or not img.filepath or img.packed_file:
            continue
        path = os.path.normpath(bpy.path.abspath(img.filepath))
        if os.path.exists(path):
            continue
        at = path.find("art-source" + os.sep)
        candidate = os.path.join(ROOT, path[at:]) if at >= 0 else None
        if candidate and os.path.exists(candidate):
            img.filepath = candidate
            img.reload()
            fixed.append(img.name)
        else:
            missing.append((img.name, path))
    if bpy.data.filepath:
        bpy.ops.file.make_paths_relative()
    print(f"[paths] repaired {len(fixed)}: {fixed}")
    for name, path in missing:
        print(f"[paths] STILL MISSING {name}: {path}")
    return fixed, missing


if __name__ == "__main__":
    repair_image_paths()
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
