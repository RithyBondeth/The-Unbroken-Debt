"""Moves Episode 1's funeral from the yard tent into the house's central hall
(funeral_indoors.py) in the village file, checks nothing else moved, and saves.

    blender -b art-source/blender/ep1/ep1_area_village.blend --python-exit-code 1 \\
        -P tools/areas/rebuild-funeral-indoors.py
    (then rebuild-village-nature.py, npm run export -- ep1/ep1_area_village, npm run assets)

Re-runnable: once the coffin is in the hall it does nothing. FUNERAL_PREVIEW=1 runs it
without saving.
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
import funeral_indoors as F  # noqa: E402


def main():
    before = {o.name: o.matrix_world.copy() for o in bpy.data.objects
              if o.users_collection and o.users_collection[0].name not in ("_protos", "nature_templates")
              and not (F.in_tent(F.centre(o)) or F.MOVE.match(o.name) or F.GONE.match(o.name)
                       or F.SANDALS.match(o.name) or o.name in ("interact_thread", "thread_mesh")
                       or (o.parent and (F.MOVE.match(o.parent.name) or F.GONE.match(o.parent.name))))}
    result = F.move_indoors()
    print("Funeral indoors:", result, flush=True)
    if result is None:
        return
    bpy.context.view_layer.update()
    changed = [n for n, m in before.items() if not bpy.data.objects.get(n) or bpy.data.objects[n].matrix_world != m]
    assert not changed, f"unrelated objects changed: {changed[:20]}"
    left = sorted({o.name for o in bpy.data.objects if o.users_collection
                   and o.users_collection[0].name not in ("_protos", "nature_templates") and o.parent is None
                   and F.in_tent(F.centre(o))})
    print("Left in the yard where the tent stood:", left, flush=True)
    for name in ("coffin_body", "portrait_sok", "marker_main_burner", "interact_incense_0", "interact_thread",
                 "light_flame_coffin", "marker_flies_tent", "interact_oil_tent"):
        o = bpy.data.objects.get(name)
        assert o is not None, f"Missing {name}"
        print(" ", name, tuple(round(v, 2) for v in o.matrix_world.translation), flush=True)
    if os.environ.get("FUNERAL_PREVIEW"):
        print("Preview: not saved", flush=True)
        return
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print("Saved", bpy.data.filepath, flush=True)


main()
