"""Rigs the red dancer ghost (art-source/library/scans/dancer_ghost.glb, made by
tools/characters/import-dancer-ghost.py) and gives her a slow robam to move to, for the
Episode 1 studio (src/episodes/ep1/prologue/DancerGhost.ts).

    blender -b --factory-startup --python-exit-code 1 -P tools/characters/rig-dancer-ghost.py
    npm run assets -- ep1/dancer_ghost

The figure is one static mesh standing in the dance's pose: her head lolling to her
right under the crown, her left arm out with the clawed hand turned up, her right hand
at her waist. A skeleton is built inside her from where her joints are on the mesh
(measured on the user's model, November 19), and skinned with bone-heat weights
computed on a watertight copy of her (a generated mesh is not clean enough for bone
heat) and carried over; the crown goes with the head.

Her rest pose is the dance pose, so every key below is a small turn away from it, each
given about her own axes (lean to the side, bend forward, twist) rather than a bone's:

- "robam", 4.8 s, looping (longer than the 4 s she is seen, so the loop never shows):
  her weight passes from one foot to the other and back, the hips sliding out and
  dropping as the knees give, the chest leaning the other way and turning toward the
  standing side (her feet held to the floor by IK, baked out); the lifted arm floats up
  and sweeps back, the hand bending back at the wrist as a dancer's does, a beat behind
  the body; the low hand curls and opens at her waist; her head rolls slowly further over
  and back, out of step with the rest. Every key eases in and out.

Writes art-export/ep1/dancer_ghost.glb.
"""
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "art-source/library/scans/dancer_ghost.glb"
OUT = ROOT / "art-export/ep1/dancer_ghost.glb"
FPS = 30
LOOP = 4.8
# The scan is the source scaled from 0.98 to 1.85 m: joints are measured in source units.
K = 1.85 / 0.98


def load():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    bpy.ops.import_scene.gltf(filepath=str(SRC))
    body = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    bpy.context.view_layer.update()
    body.data.transform(body.matrix_world)
    body.parent = None
    body.matrix_world.identity()
    for o in [o for o in bpy.context.scene.objects if o != body]:
        bpy.data.objects.remove(o)
    # glTF splits vertices along UV seams; weld them, so the only holes are real ones.
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(body.data)
    bm.free()
    for poly in body.data.polygons:
        poly.use_smooth = True
    return body


def joints(body):
    """Joint positions (metres) from the mesh itself; she faces -Y, her left is +X."""
    co = np.array([v.co[:] for v in body.data.vertices]) / K
    x, y, z = co[:, 0], co[:, 1], co[:, 2]

    def centre(mask):
        pts = co[mask]
        if not len(pts):
            raise RuntimeError("no vertices for a joint")
        return pts.mean(0)

    def V(p):
        return Vector(np.array(p) * K)

    j = {
        "root": V((-0.07, 0.035, 0.45)),
        "spine": V((-0.075, 0.025, 0.535)),
        "chest": V((-0.085, 0.02, 0.6)),
        "neck": V((-0.095, 0.025, 0.69)),
        "head": V((-0.125, 0.035, 0.735)),
        "head_top": V((-0.175, 0.06, 0.84)),
        "shoulder.R": V((-0.15, 0.025, 0.655)),
        "shoulder.L": V((-0.02, 0.015, 0.66)),
        "hip.R": V((-0.11, 0.04, 0.43)),
        "hip.L": V((-0.03, 0.04, 0.43)),
        "knee.R": V((-0.11, 0.025, 0.23)),
        "knee.L": V((-0.035, 0.025, 0.23)),
    }
    # The arms, from where they are on the mesh.
    j["elbow.L"] = V(centre((x > 0.1) & (x < 0.13) & (z > 0.55) & (z < 0.63)))
    j["wrist.L"] = V(centre((x > 0.225) & (x < 0.25) & (z > 0.62) & (z < 0.69)))
    j["hand.L"] = V(co[x.argmax()])
    j["elbow.R"] = V(centre((x < -0.19) & (z > 0.46) & (z < 0.53)))
    low_hand = (z > 0.4) & (z < 0.53) & (y < -0.06) & (x > -0.18)
    j["wrist.R"] = V(centre(low_hand & (x < -0.12)))
    j["hand.R"] = V(co[np.where(low_hand)[0][y[low_hand].argmin()]])
    # The feet: either side of her middle, under the hem.
    for side, s in (("R", -1), ("L", 1)):
        foot = (s * (x + 0.07) > 0) & (z < 0.07) & (np.abs(x + 0.07) < 0.1)
        j[f"ankle.{side}"] = V(centre(foot & (z > 0.03)))
        toe = co[foot & (z < 0.025)]
        j[f"toe.{side}"] = V(toe[toe[:, 1].argmin()])
    for k, v in j.items():
        print(f"JOINT {k:12s} {v.x:+.3f} {v.y:+.3f} {v.z:+.3f}", flush=True)
    return j


def skeleton(j):
    data = bpy.data.armatures.new("dancer_ghost_rig")
    rig = bpy.data.objects.new("dancer_ghost_rig", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = data.edit_bones

    def bone(name, head, tail, parent=None, deform=True, connect=False):
        b = eb.new(name)
        b.head, b.tail = head, tail
        if (b.tail - b.head).length < 1e-3:
            b.tail = b.head + Vector((0, 0, 0.05))
        b.use_deform = deform
        if parent:
            b.parent = eb[parent]
            b.use_connect = connect
        return b

    bone("root", j["root"], j["spine"])
    bone("spine", j["spine"], j["chest"], "root", connect=True)
    bone("chest", j["chest"], j["neck"], "spine", connect=True)
    bone("neck", j["neck"], j["head"], "chest", connect=True)
    bone("head", j["head"], j["head_top"], "neck", connect=True)
    for s in ("L", "R"):
        bone(f"upperarm.{s}", j[f"shoulder.{s}"], j[f"elbow.{s}"], "chest")
        bone(f"forearm.{s}", j[f"elbow.{s}"], j[f"wrist.{s}"], f"upperarm.{s}", connect=True)
        bone(f"hand.{s}", j[f"wrist.{s}"], j[f"hand.{s}"], f"forearm.{s}", connect=True)
        bone(f"thigh.{s}", j[f"hip.{s}"], j[f"knee.{s}"], "root")
        bone(f"shin.{s}", j[f"knee.{s}"], j[f"ankle.{s}"], f"thigh.{s}", connect=True)
        bone(f"foot.{s}", j[f"ankle.{s}"], j[f"toe.{s}"], f"shin.{s}", connect=True)
        # Where each foot stays on the floor (an IK goal; not exported as a deformer).
        bone(f"ik.{s}", j[f"ankle.{s}"], j[f"ankle.{s}"] + Vector((0, 0.08, 0)), None, deform=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def skin(body, rig):
    """Bone-heat weights on a watertight remesh of her, carried onto the real mesh."""
    proxy = body.copy()
    proxy.data = body.data.copy()
    bpy.context.scene.collection.objects.link(proxy)
    remesh = proxy.modifiers.new("watertight", "REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = 0.01
    bpy.context.view_layer.objects.active = proxy
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    bpy.ops.object.select_all(action="DESELECT")
    proxy.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    print("proxy", len(proxy.data.vertices), "verts, groups", [g.name for g in proxy.vertex_groups], flush=True)
    for g in proxy.vertex_groups:
        body.vertex_groups.new(name=g.name)
    bpy.context.view_layer.objects.active = body
    transfer = body.modifiers.new("weights", "DATA_TRANSFER")
    transfer.object = proxy
    transfer.use_vert_data = True
    transfer.data_types_verts = {"VGROUP_WEIGHTS"}
    transfer.vert_mapping = "POLYINTERP_NEAREST"
    transfer.layers_vgroup_select_src = "ALL"
    transfer.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.modifier_apply(modifier=transfer.name)
    bpy.data.objects.remove(proxy)
    for g in [g for g in body.vertex_groups if g.name.startswith("ik.")]:
        body.vertex_groups.remove(g)
    deform = body.modifiers.new("Armature", "ARMATURE")
    deform.object = rig
    body.parent = rig


def channels(action):
    """(collection, fcurve) pairs of an action: Blender 5 keeps them in layered channel bags."""
    if hasattr(action, "fcurves"):
        return [(action.fcurves, fc) for fc in action.fcurves]
    return [(bag.fcurves, fc) for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for fc in bag.fcurves]


def ease_all(action):
    for _, fc in channels(action):
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER"
            k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"
        fc.modifiers.new("CYCLES")


# Her own axes, in the armature's space: +X her left, -Y her front, +Z up.
SIDE = Vector((0, 1, 0))     # about the front-back axis: + leans the top toward her left
BEND = Vector((1, 0, 0))     # about the left-right axis: + bends the top forward
TWIST = Vector((0, 0, 1))    # about the vertical: + turns her front toward her left


def animate(rig):
    """The robam: keys in seconds; each turn is given about her own axes (degrees) and
    turned into the bone's own space."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    pb = rig.pose.bones
    for b in pb:
        b.rotation_mode = "QUATERNION"
    for s in ("L", "R"):
        ik = pb[f"shin.{s}"].constraints.new("IK")
        ik.target = rig
        ik.subtarget = f"ik.{s}"
        ik.chain_count = 2
        ik.use_tail = True
        pb[f"thigh.{s}"].ik_stiffness_y = 0.6
    rig.animation_data_create()
    action = bpy.data.actions.new("robam")
    rig.animation_data.action = action

    def key(t, name, turns=(), slide=None):
        b = pb[name]
        rest = b.bone.matrix_local.to_3x3()
        q = Quaternion()
        for axis, deg in turns:
            q = Quaternion(axis, math.radians(deg)) @ q
        # A turn about her axes, as the bone's own rotation from its rest.
        local = rest.inverted() @ q.to_matrix() @ rest
        b.rotation_quaternion = local.to_quaternion()
        b.keyframe_insert("rotation_quaternion", frame=1 + t * FPS)
        if slide is not None:
            b.location = rest.inverted() @ Vector(slide)
            b.keyframe_insert("location", frame=1 + t * FPS)

    # The body: a pass to her left, back through the middle, a pass to her right.
    T = (0.0, 1.2, 2.4, 3.6, LOOP)
    sway = (0, 1, 0, -1, 0)
    sink = (0.35, 1, 0.35, 1, 0.35)
    for t, w, d in zip(T, sway, sink):
        key(t, "root", ((SIDE, -3 * w), (BEND, 1.5 * d)), slide=(0.032 * w, 0, -0.03 * d))
        key(t, "spine", ((SIDE, 2.5 * w), (BEND, 1.5 * d), (TWIST, 2 * w)))
        key(t, "chest", ((SIDE, 3 * w), (TWIST, 4 * w), (BEND, -1 + 1.5 * d)))
        key(t, "neck", ((SIDE, -2 * w),))
    # Her head, slower and out of step: rolling further over to her right and back.
    for t, h in zip((0.0, 1.6, 3.0, 4.0, LOOP), (0, 0.8, 1, 0.4, 0)):
        key(t, "head", ((SIDE, -7 * h), (BEND, -5 * h), (TWIST, 3 * h)))
    # The lifted arm, a beat behind the body: it floats up and sweeps back, the hand
    # bending back at the wrist.
    for t, a in zip((0.0, 1.5, 2.7, 3.9, LOOP), (0, 1, 0.35, -0.7, 0)):
        key(t, "upperarm.L", ((SIDE, -9 * a), (TWIST, 7 * a)))
        key(t, "forearm.L", ((SIDE, -9 * a), (BEND, 4 * a)))
        key(t, "hand.L", ((SIDE, -16 * a), (TWIST, -6 * a)))
    # The low hand curls and opens at her waist.
    for t, b_ in zip((0.0, 1.1, 2.3, 3.5, LOOP), (0, -0.6, 1, 0.2, 0)):
        key(t, "upperarm.R", ((BEND, 3 * b_), (SIDE, 2 * b_)))
        key(t, "forearm.R", ((TWIST, 6 * b_),))
        key(t, "hand.R", ((TWIST, 12 * b_), (SIDE, -6 * b_)))
    for s in ("L", "R"):
        pb[f"ik.{s}"].keyframe_insert("location", frame=1)
    ease_all(action)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = int(LOOP * FPS)
    # Bake the IK out (glTF keeps no constraints), then drop the goals' keys.
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.nla.bake(frame_start=1, frame_end=int(LOOP * FPS) + 1, only_selected=False, visual_keying=True,
                     clear_constraints=True, use_current_action=True, bake_types={"POSE"})
    action = rig.animation_data.action
    action.name = "robam"
    for coll, fc in [c for c in channels(action) if '"ik.' in c[1].data_path]:
        coll.remove(fc)
    bpy.ops.object.mode_set(mode="OBJECT")
    return action


def export(body, rig):
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    rig.select_set(True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=False, export_animations=True, export_skins=True,
                              export_def_bones=True, export_image_format="AUTO",
                              export_cameras=False, export_lights=False)
    print("Wrote", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB", flush=True)


body = load()
j = joints(body)
rig = skeleton(j)
skin(body, rig)
animate(rig)
export(body, rig)
