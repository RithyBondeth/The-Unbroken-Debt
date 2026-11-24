"""Episode 1's jump scares' props (the user approved J1-J5 from Cycles previews, Nov 24,
2026; the previews are the scratchpad's jumpscare_preview.py):

- J2, the washing room: the sheet on the washing board has sat up over the Preay reaching.
  Her posed body (preay.blend's `reach` clip at 1 s, leant forward 0.18 rad) is baked to a
  still mesh and a cotton sheet is dropped on it by a cloth simulation, as in the preview.
  Feet at the origin, facing -Y (the rig's forward), like the Preay herself.
- J3, the nailed back door: the four planks and the diagonal of stilt_house.locks(), and
  the door's leaf (from the rebuilt village), at their places in the house, smashed through
  where her face comes (a boolean hole), with splinters bent toward the corridor. The game
  swaps these for the whole door.

blender -b --factory-startup --python-exit-code 1 -P tools/characters/build-scares.py
Then: npm run assets -- ep1/scares
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/areas"))
from kit import box, library_material, plain  # noqa: E402
from shrine_craft import Batch  # noqa: E402
import stilt_house as SH  # noqa: E402

PREAY = ROOT / "art-source/characters/preay/preay.blend"
OUT = ROOT / "art-export/ep1/scares.glb"
BLEND = ROOT / "art-source/characters/scares/scares.blend"
# The rebuilt village (tools/areas/rebuild-farmstead.py): the back door's leaf comes from it.
VILLAGE = ROOT / "art-source/blender/ep1/ep1_area_village.blend"

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
coll = bpy.data.collections.new("scares")
sc.collection.children.link(coll)
work = bpy.data.collections.new("_work")
sc.collection.children.link(work)


def evaluated_copy(obj, name, into):
    """A still mesh of what `obj` looks like now (modifiers and pose applied)."""
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
    me.name = name
    out = bpy.data.objects.new(name, me)
    into.objects.link(out)
    out.matrix_world = obj.matrix_world.copy()
    return out


# ------------------------------------------------------------------ J2: the sheet sitting up
with bpy.data.libraries.load(str(PREAY), link=False) as (src, dst):
    dst.objects = ["preay_body", "preay_rig"]
    dst.actions = list(src.actions)
body = next(o for o in dst.objects if o.name.startswith("preay_body"))
rig = next(o for o in dst.objects if o.name.startswith("preay_rig"))
for o in (body, rig):
    work.objects.link(o)
act = next(a for a in bpy.data.actions if a.name == "reach")
rig.animation_data_create()
rig.animation_data.action = act
if hasattr(rig.animation_data, "action_slot") and len(getattr(act, "slots", [])):
    rig.animation_data.action_slot = act.slots[0]
sc.render.fps = 30
# Leant forward as she sits up (the preview's place_facing tilt), feet at the origin.
rig.matrix_world = Matrix.Rotation(0.18, 4, "X")
sc.frame_set(int(act.frame_range[0] + 1.0 * 30))
bpy.context.view_layer.update()
posed = evaluated_copy(body, "scare_sheet_body", coll)
posed.matrix_world = Matrix.Identity(4)
deps = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(deps)
# new_from_object keeps the object-space mesh; bake the rig's tilt into the vertices.
posed.data.transform(ev.matrix_world)
bpy.data.objects.remove(body, do_unlink=True)
bpy.data.objects.remove(rig, do_unlink=True)
sc.frame_set(1)

top = max(v.co.z for v in posed.data.vertices)
me = bpy.data.meshes.new("scare_sheet_cloth")
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=64, y_segments=64, size=1.05)
bm.to_mesh(me)
bm.free()
sheet = bpy.data.objects.new("scare_sheet_cloth_sim", me)
work.objects.link(sheet)
sheet.location = (0, 0, top + 0.03)
posed.modifiers.new("collision", "COLLISION")
posed.collision.thickness_outer = 0.025
posed.collision.cloth_friction = 3
cl = sheet.modifiers.new("cloth", "CLOTH")
cl.settings.quality = 10
cl.settings.mass = 0.25
cl.settings.tension_stiffness = 12
cl.settings.compression_stiffness = 12
cl.settings.bending_stiffness = 0.2
cl.collision_settings.use_self_collision = False
cl.collision_settings.distance_min = 0.015
cl.collision_settings.collision_quality = 3
cl.point_cache.frame_start = 1
cl.point_cache.frame_end = 45
for f in range(1, 46):
    sc.frame_set(f)
sub = sheet.modifiers.new("subd", "SUBSURF")
sub.levels = sub.render_levels = 1
cloth = evaluated_copy(sheet, "scare_sheet_cloth", coll)
bpy.data.objects.remove(sheet, do_unlink=True)
posed.modifiers.clear()
cotton = library_material("rough_linen", "M_scare_sheet_cotton", tint=(0.86, 0.84, 0.79), tile=0.5)
cotton.use_backface_culling = False
cloth.data.materials.clear()
cloth.data.materials.append(cotton)
for p in cloth.data.polygons:
    p.use_smooth = True
uv = cloth.data.uv_layers.active or cloth.data.uv_layers.new(name="UVMap")
for loop in cloth.data.loops:
    co = cloth.data.vertices[loop.vertex_index].co
    uv.data[loop.index].uv = (co.x / 0.5, co.y / 0.5)
fig = bpy.data.objects.new("scare_sheet", None)
coll.objects.link(fig)
for o in (posed, cloth):
    o.parent = fig
print("[scares] sheet", len(cloth.data.vertices), "verts over", len(posed.data.polygons), "faces", flush=True)

# ------------------------------------------------------------------ J3: the planks smashed through
FLOOR, T = SH.FLOOR, SH.T
y = SH.B["y1"] - T - 0.03
planks_mat = library_material("weathered_planks", "M_sh_nailed_planks", tint=(0.55, 0.5, 0.45), tile=1.2)
iron = plain("M_scare_nail_iron", (0.05, 0.045, 0.04), rough=0.55, metal=0.8)
door = bpy.data.objects.new("scare_door_broken", None)
coll.objects.link(door)
planks, nails = [], []
for k, (z, tilt) in enumerate(((FLOOR + 0.45, 0.0), (FLOOR + 1.05, 0.12), (FLOOR + 1.6, -0.06), (FLOOR + 1.9, 0.0))):
    p = box(f"scare_door_broken_plank_{k}", coll, -0.68, 0.68, y - 0.026, y, z - 0.085, z + 0.085, planks_mat)
    p.rotation_euler.y = tilt
    planks.append(p)
    for xn in (-0.6, 0.6):
        nails.append(box(f"scare_door_broken_nail_{k}", coll, xn - 0.008, xn + 0.008, y - 0.03, y - 0.026, z - 0.008, z + 0.008, iron))
p = box("scare_door_broken_plank_diag", coll, -0.75, 0.75, y - 0.05, y - 0.026, FLOOR + 1.2 - 0.09, FLOOR + 1.2 + 0.09, planks_mat)
p.rotation_euler.y = math.radians(52)
planks.append(p)
# The door's own leaf behind them (the village's door_back_leaf, built by stilt_house): the
# hole goes through it too, or her face would have nothing to show through.
with bpy.data.libraries.load(str(VILLAGE), link=False) as (src, dst):
    dst.objects = ["door_back_leaf"]
leaf = dst.objects[0]
coll.objects.link(leaf)
leaf.name = "scare_door_broken_leaf"
leaf.parent = None
planks.append(leaf)
# The hole her face and arms came through (the preview's cutter), the boards' edges ragged.
me = bpy.data.meshes.new("scare_cutter")
bm = bmesh.new()
bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.2)
for v in bm.verts:
    v.co.x *= 1.25
    v.co.z *= 0.8
    v.co += Vector((math.sin(v.co.z * 31) * 0.04, 0, math.sin(v.co.x * 27) * 0.04))
bm.to_mesh(me)
bm.free()
cutter = bpy.data.objects.new("scare_cutter", me)
work.objects.link(cutter)
cutter.location = (0.0, SH.B["y1"] - 0.05, FLOOR + 1.32)
cutter.scale = (1.0, 3.0, 1.0)
bpy.context.view_layer.update()
for p in planks:
    mod = p.modifiers.new("hole", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    cut = evaluated_copy(p, p.name + "_cut", coll)
    cut.matrix_world = p.matrix_world.copy()
    name = p.name
    bpy.data.objects.remove(p, do_unlink=True)
    cut.name = name
    cut.parent = door
    cut.matrix_parent_inverse = Matrix.Identity(4)
for n in nails:
    n.parent = door
    n.matrix_parent_inverse = Matrix.Identity(4)
b = Batch("scare_door_broken_splinters")
rng = np.random.default_rng(5)
for k in range(14):
    a = rng.uniform(0, math.tau)
    p0 = Vector((0.24 * math.cos(a), y - 0.03, FLOOR + 1.32 + 0.18 * math.sin(a)))
    p1 = p0 + Vector((rng.normal(0, 0.06), -rng.uniform(0.1, 0.3), rng.normal(0, 0.06)))
    b.tube(planks_mat, [tuple(p0), tuple(p1)], [0.012, 0.002], sides=4, cap_end=True)
b.build(coll)
for o in list(coll.objects):
    if o.name.startswith("scare_door_broken_splinters"):
        o.parent = door
        o.matrix_parent_inverse = Matrix.Identity(4)
print("[scares] door", [o.name for o in door.children], flush=True)

# ------------------------------------------------------------------ save and export
for o in list(work.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.data.collections.remove(work)
BLEND.parent.mkdir(parents=True, exist_ok=True)
for img in bpy.data.images:
    if img.source == "FILE":
        img.pack()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
bpy.ops.object.select_all(action="DESELECT")
for o in coll.all_objects:
    o.select_set(True)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", use_selection=True, export_yup=True,
                          export_apply=True, export_animations=False, export_extras=False,
                          export_cameras=False, export_lights=False)
print("[scares] exported", OUT, flush=True)
