"""Rigs the headless dancer (art-source/library/scans/dancer_ghost.glb, made by
tools/characters/import-dancer-ghost.py) and gives her a slow robam to move to, for the
Episode 1 studio (src/episodes/ep1/prologue/DancerGhost.ts).

    blender -b --factory-startup --python-exit-code 1 -P tools/characters/rig-dancer-ghost.py
    npm run assets -- ep1/dancer_ghost

The figure is one static mesh standing in the dance's pose. A skeleton is built inside
her from where her joints are on the mesh, and skinned with weights computed on a
watertight copy of her (a generated mesh is not clean enough for bone heat) and
carried over. Then both hands are taken off at the wrist (the user's call, November
2026), along the line where the hand bones' weights give way to the forearms': each
stump closed and sunk into a raw wound, the sleeve's end round it soaked dark, and
blood run in streaks down the raised forearm toward the elbow, dried along the low one
(vertex colour, multiplied over her texture).

Her rest pose is the dance pose, so every key below is a small turn away from it,
which is what keeps her moving like a person rather than a puppet:

- "robam", 3.2 s, looping: her weight passes from one foot to the other and back, the
  hips swaying out and the chest leaning the other way, the knees sinking on each pass
  (her feet held to the floor by IK, baked out); the raised forearm sweeps outward and
  back and the low arm lifts, the stumps of the wrists turning as hands would; the stump
  of her neck turns a little toward whoever is watching. Every key eases in and out.

Writes art-export/ep1/dancer_ghost.glb.
"""
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Vector

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "art-source/library/scans/dancer_ghost.glb"
OUT = ROOT / "art-export/ep1/dancer_ghost.glb"
FPS = 30
LOOP = 3.2


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
    """Joint positions from the mesh itself (she faces -Y; her left is +X)."""
    co = np.array([v.co[:] for v in body.data.vertices])

    def centre(mask):
        pts = co[mask]
        if not len(pts):
            raise RuntimeError("no vertices for a joint")
        return Vector(pts.mean(0))

    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    def trunk_y(z0, z1):
        # Midway between front and back (an average leans toward the sash and folds).
        ys = co[(z > z0) & (z < z1) & (np.abs(x) < 0.12)][:, 1]
        return float(np.percentile(ys, 5) + np.percentile(ys, 95)) / 2
    j = {}
    j["root"] = Vector((0, trunk_y(0.72, 0.8), 0.78))
    j["spine"] = Vector((0, trunk_y(0.95, 1.05), 1.0))
    j["chest"] = Vector((0, trunk_y(1.15, 1.22), 1.18))
    j["neck"] = Vector((0, trunk_y(1.32, 1.38), 1.33))
    j["neck_top"] = Vector(co[z.argmax()])
    for side, s in (("R", -1), ("L", 1)):
        j[f"shoulder.{side}"] = Vector((s * 0.15, trunk_y(1.24, 1.3), 1.27))
        foot = (s * x > 0.0) & (z < 0.14) & (s * x < 0.16)
        j[f"ankle.{side}"] = centre(foot & (z > 0.06))
        toe = co[foot & (z < 0.04)]
        j[f"toe.{side}"] = Vector(toe[toe[:, 1].argmin()])
        j[f"hip.{side}"] = Vector((s * 0.085, j["root"].y, 0.74))
        j[f"knee.{side}"] = Vector((s * 0.08, j["root"].y - 0.02, 0.42))
    # The low right arm: elbow and wrist from where it leaves the trunk, the fingertips.
    j["elbow.R"] = centre((x < -0.22) & (z > 1.08) & (z < 1.13))
    j["wrist.R"] = centre((x > -0.37) & (x < -0.3) & (z > 0.92) & (z < 0.98))
    j["hand.R"] = Vector(co[x.argmin()])
    # The raised left arm: the elbow hangs below the shoulder, the hand points up.
    j["elbow.L"] = centre((x > 0.25) & (x < 0.34) & (z > 1.12) & (z < 1.16))
    j["wrist.L"] = centre((x > 0.33) & (x < 0.4) & (z > 1.26) & (z < 1.3))
    raised = co[(x > 0.42)]
    j["hand.L"] = Vector(raised[raised[:, 2].argmax()])
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
    bone("neck", j["neck"], j["neck_top"], "chest", connect=True)
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
    remesh.voxel_size = 0.012
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
    # The sampot hangs from the hips: below the knee its weight stays with the shins,
    # above it with the thighs and hips, never with the arms.
    for g in [g for g in body.vertex_groups if g.name.startswith("ik.")]:
        body.vertex_groups.remove(g)
    deform = body.modifiers.new("Armature", "ARMATURE")
    deform.object = rig
    body.parent = rig


ARMS = ("hand.",)


def amputate(body, rig, j):
    """Both hands off at the wrist, the stumps capped as recessed wounds, blood round
    them and run down the forearms."""
    import bmesh
    from mathutils.kdtree import KDTree
    rng = np.random.default_rng(1932)
    arm_groups = {g.index for g in body.vertex_groups if g.name.startswith(ARMS)}
    bm = bmesh.new()
    bm.from_mesh(body.data)
    deform = bm.verts.layers.deform.active
    doomed = [v for v in bm.verts if sum(w for gi, w in v[deform].items() if gi in arm_groups) > 0.5]
    # The generated mesh has small gaps of its own; only the new edges are the wrists.
    gaps = {e for e in bm.edges if e.is_boundary}
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    # Close each stump: fill the hole, put a point in its middle and sink it in.
    rim = [e for e in bm.edges if e.is_boundary and e not in gaps]
    rim_pts = [v.co.copy() for v in {v for e in rim for v in e.verts}]
    # Each wrist's rim as its own loop (a wrist that shares a vertex with an old gap is
    # not a clean hole for holes_fill): triangulated across, then gathered to one face.
    loops, left = [], set(rim)
    while left:
        stack, loop = [left.pop()], set()
        while stack:
            e = stack.pop()
            loop.add(e)
            for v in e.verts:
                for n in v.link_edges:
                    if n in left:
                        left.discard(n)
                        stack.append(n)
        loops.append(loop)
    print("rim loops", sorted(len(loop) for loop in loops), flush=True)
    caps = []
    for loop in loops:
        if len(loop) < 8:
            continue
        made = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=list(loop))["geom"]
        tris = [f for f in made if isinstance(f, bmesh.types.BMFace)]
        if tris:
            merged = bmesh.ops.dissolve_faces(bm, faces=tris)["region"]
            caps += [f for f in merged if isinstance(f, bmesh.types.BMFace)] or tris
    wound = len(body.data.materials)
    body.data.materials.append(wound_material())
    centres = []
    for face in caps:
        face.material_index = wound
        centre = face.calc_center_median()
        normal = face.normal.copy()
        poked = bmesh.ops.poke(bm, faces=[face])
        for f in poked["faces"]:
            f.material_index = wound
            f.smooth = True
        for v in poked["verts"]:
            # Sunk into the body, ragged.
            v.co = v.co - normal * 0.01 + Vector(rng.normal(0, 0.002, 3))
        centres.append(centre)
    bm.normal_update()
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    # Blood: the sleeve soaked round each stump, and runs from the rim along the forearm
    # toward the elbow, fresh down the raised one, dried and shorter on the low one.
    co = np.array([v.co[:] for v in body.data.vertices])
    tree = KDTree(len(rim_pts))
    for i, p in enumerate(rim_pts):
        tree.insert(p, i)
    tree.balance()
    blood = np.zeros(len(co))
    for i, c in enumerate(co):
        _, _, d = tree.find(c)
        blood[i] = np.clip((0.045 - d) / 0.033, 0, 1)
    streaks = 0
    for side, longest, strength in (("L", 0.2, 0.9), ("R", 0.09, 0.6)):
        down = (j[f"elbow.{side}"] - j[f"wrist.{side}"]).normalized()
        sign = 1 if side == "L" else -1
        mine = [p for p in rim_pts if sign * p.x > 0]
        for p in mine[:: max(1, len(mine) // 9)]:
            if rng.random() > 0.75:
                continue
            length, width = rng.uniform(0.03, longest), rng.uniform(0.004, 0.011)
            rel = co - np.array(p[:])
            along = rel @ np.array(down[:])
            across = np.linalg.norm(rel - np.outer(along, np.array(down[:])), axis=1)
            t = np.clip(along / length, 0, 1)
            # Hugging the arm: only points close to the surface line from the rim point.
            hit = (along > -0.004) & (along < length) & (across < width * np.sqrt(1 - t) + 0.006)
            blood = np.maximum(blood, np.where(hit, strength * (1 - 0.45 * t), 0))
            streaks += 1
    colour = np.ones((len(co), 4), np.float32)
    dark = np.array((0.3, 0.03, 0.022))
    colour[:, :3] = 1 - blood[:, None] * (1 - dark)
    attr = body.data.color_attributes.new(name="blood", type="FLOAT_COLOR", domain="POINT")
    attr.data.foreach_set("color", colour.ravel())
    body.data.color_attributes.active_color = attr
    # The texture is multiplied by it in the material, so the exporter keeps it as COLOR_0.
    mat = body.data.materials[0]
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    src = bsdf.inputs["Base Color"].links[0].from_socket
    tint = nodes.new("ShaderNodeVertexColor")
    tint.layer_name = "blood"
    mult = nodes.new("ShaderNodeMix")
    mult.data_type = "RGBA"
    mult.blend_type = "MULTIPLY"
    mult.inputs["Factor"].default_value = 1.0
    links.new(src, mult.inputs[6])
    links.new(tint.outputs["Color"], mult.inputs[7])
    links.new(mult.outputs[2], bsdf.inputs["Base Color"])
    # The arms' bones and weights go with them.
    for g in [g for g in body.vertex_groups if g.name.startswith(ARMS)]:
        body.vertex_groups.remove(g)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for b in [b for b in rig.data.edit_bones if b.name.startswith(ARMS)]:
        rig.data.edit_bones.remove(b)
    bpy.ops.object.mode_set(mode="OBJECT")
    print("amputated", len(doomed), "verts;", len(caps), "stumps;", streaks, "streaks;",
          int((blood > 0.3).sum()), "bloodied verts", flush=True)


def wound_material():
    m = bpy.data.materials.new("M_dancer_ghost_wound")
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.11, 0.008, 0.006, 1)
    p.inputs["Roughness"].default_value = 0.28
    return m


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


def animate(rig):
    """The robam: keys in seconds, rotations in degrees about each bone's own axes
    (Blender's bone space: Y runs along the bone)."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    pb = rig.pose.bones
    for b in pb:
        b.rotation_mode = "XYZ"
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

    def key(t, name, rot=(0, 0, 0), loc=None):
        b = pb[name]
        b.rotation_euler = Euler([math.radians(a) for a in rot])
        b.keyframe_insert("rotation_euler", frame=1 + t * FPS)
        if loc is not None:
            b.location = loc
            b.keyframe_insert("location", frame=1 + t * FPS)

    # Times: 0 rest, then a pass to her left, back through the middle, a pass to her right.
    T = (0.0, 0.8, 1.6, 2.4, LOOP)
    sway = (0, 1, 0, -1, 0)          # weight over the left foot (+1) or the right (-1)
    sink = (0, 1, 0.35, 1, 0)        # how far the knees give
    for t, w, d in zip(T, sway, sink):
        # Root (bone space: Y up the spine, X to her left, Z backward): the hips slide
        # over the standing foot and drop as the knees bend.
        key(t, "root", (2 * d, 0, -4 * w), loc=(0.028 * w, -0.035 * d, 0.0))
        key(t, "spine", (-1.5 * d, 2 * w, 3 * w))
        key(t, "chest", (-1 - 1.5 * d, 3 * w, 4 * w))
        key(t, "neck", (6 + 4 * d, -8 * w, -5 * w))
    # The arms on a phrase of their own, a quarter-beat behind the hips.
    A = (0.0, 0.6, 1.25, 2.0, 2.7, LOOP)
    for t, a in zip(A, (0, 1, 0.4, -0.4, -1, 0)):
        key(t, "upperarm.L", (6 * a, 0, -10 * a))
        key(t, "forearm.L", (-12 * a, 22 * a, 0))
        key(t, "upperarm.R", (-8 + 8 * a, 0, -14 - 12 * a))
        key(t, "forearm.R", (6 * a, -16 * a, -10))
    for s in ("L", "R"):
        key(0, f"ik.{s}")
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
                              export_def_bones=True, export_vertex_color="ACTIVE",
                              export_image_format="JPEG", export_image_quality=90,
                              export_cameras=False, export_lights=False)
    print("Wrote", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB", flush=True)


body = load()
j = joints(body)
rig = skeleton(j)
skin(body, rig)
amputate(body, rig, j)
animate(rig)
export(body, rig)
