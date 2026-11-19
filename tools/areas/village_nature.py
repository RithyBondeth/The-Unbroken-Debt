"""Episode 1 village nature pass (November 19, 2026): every tree, palm, bamboo clump and
banana plant of the village becomes one of the user's scanned plants (prep-village-flora.py),
the Neak Ta shrine's banyan becomes the scanned banyan, the forest floor gets a scanned
litter of decaying leaves, bark and roots, the drowned paddies are planted with rice at
grain filling and a ripe golden field, and their bunds are rebuilt as earth dikes.

Plain functions, run inside Blender on the village .blend by rebuild-village-nature.py
(which saves) and by the Cycles preview (which never saves). Blender space: x east, y
north; Babylon x = -x, z = -y.

One palette for everything (the user, Nov 19: "make sure everything match and fit with
each other"): every foliage material is pulled toward the same cold, deep jungle green,
dry leaves toward the same brown, so scans from five sources read as one forest.
"""
import math
import os
import re

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LIB = os.path.join(ROOT, "art-source", "library")
SCANS = os.path.join(LIB, "scans")

# No bamboo (the user, Nov 19: "remove all the bamboo ... replace it with" bananas and
# palms): its scan stays in the library but nothing in the village uses it.
FLORA = ("forest_tree_gn", "forest_banyan", "sugar_palm", "banana_clump")
WATER_Z = -0.1          # the flood's surface over the paddies (flood_water)
PADDY_FLOOR = -0.32     # the drowned fields' mud (terrain(), ep1_area_village.py)
BUND_X = (-34, -20, -6, 8, 22, 36)   # the dikes between the paddies (terrain())
BUND_Y = (-74.0, -84.0)
PADDY_Y = (-86.5, -66.1)            # far bank .. road bank foot
PADDY_X = 53.5                      # the walls' bunds close the fields (forestBorder.ts BUND_X)
BANYAN = (-7.0, -35.5)
SHRINE = (-3.9, -34.9)


def protos_collection():
    hidden = bpy.data.collections.get("_protos")
    if hidden is None:
        hidden = bpy.data.collections.new("_protos")
        bpy.context.scene.collection.children.link(hidden)
    return hidden


def import_scan(key, path=None):
    """Imports a scan file once into _protos; returns its mesh objects by name."""
    hidden = protos_collection()
    path = path or os.path.join(SCANS, f"{key}.glb")
    stamp = os.path.getmtime(path)
    have = {o.name: o for o in hidden.objects if o.get("flora") == key}
    if have and all(abs(o.get("src_mtime", 0) - stamp) < 1 for o in have.values()):
        return have
    for o in have.values():         # the scan was prepared again: import it afresh
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data is not None and data.users == 0:
            bpy.data.meshes.remove(data)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    out = {}
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        hidden.objects.link(o)
        o["flora"] = key
        o["src_mtime"] = stamp
        if o.type == "MESH":
            o.parent = None
            for slot in o.material_slots:
                m = slot.material
                if m and not m.name.startswith("M_flora_"):
                    m.name = f"M_flora_{key}_{m.name.split('.')[0]}"
            out[o.name] = o
        o.hide_render = False
    return out


def flora():
    """The five plants, LOD0 and LOD1, plus a dead tree made from the giant's bare wood."""
    out = {}
    for key in FLORA:
        objs = import_scan(key)
        out[key] = (objs[key], objs[f"{key}_lod1"], objs.get(f"{key}_lod2", objs[f"{key}_lod1"]))
    stale = bpy.data.objects.get("forest_tree_gn_dead")
    if stale and stale.get("src_mtime") != out["forest_tree_gn"][0].get("src_mtime"):
        bpy.data.objects.remove(stale, do_unlink=True)
    if "forest_tree_gn_dead" not in bpy.data.objects:
        gn = out["forest_tree_gn"][0]
        dead = gn.copy()
        dead.data = gn.data.copy()
        dead.name = dead.data.name = "forest_tree_gn_dead"
        protos_collection().objects.link(dead)
        bm = bmesh.new()
        bm.from_mesh(dead.data)
        leafy = [i for i, m in enumerate(dead.data.materials) if m and re.search("Cluster|Vines", m.name)]
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in leafy], context="FACES")
        bm.to_mesh(dead.data)
        bm.free()
        dead["flora"] = "forest_tree_gn_dead"
        dead["src_mtime"] = gn.get("src_mtime")
    out["dead"] = (bpy.data.objects["forest_tree_gn_dead"],) * 3
    unify_palette()
    return out


# One forest: what each material family is pulled toward (linear albedo multipliers).
PALETTE = {
    "leaf": (0.66, 0.78, 0.62),     # living foliage: cold, deep green
    "dry": (0.86, 0.8, 0.72),       # dead leaves and fronds: toward a damp brown
    "bark": (0.78, 0.76, 0.74),     # wet bark, a shade darker than the scans' dry wood
}


def unify_palette():
    """Multiplies each Poly Haven plant's and scan's base colour toward PALETTE, once."""
    for mat in bpy.data.materials:
        if mat.get("palette") or not mat.node_tree:
            continue
        name = mat.name.lower()
        if re.search(r"(fern_02|shrub_0|pachira|calathea|anthurium|grass_medium|grass_bermuda|nettle|weed_plant|periwinkle|sorrel)", name):
            family = "leaf"
        elif re.search(r"(bark_debris|dead_tree|dry_branches|root_cluster|single_root|tree_stump)", name):
            family = "bark"
        else:
            continue
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bsdf or not bsdf.inputs["Base Color"].is_linked:
            continue
        nt = mat.node_tree
        link = bsdf.inputs["Base Color"].links[0]
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs["B"].default_value = (*PALETTE[family], 1)
        nt.links.new(link.from_socket, mix.inputs["A"])
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
        mat["palette"] = family


def use_2k_maps():
    """Points every Poly Haven plant texture at its 2K file where one was fetched (the
    library keeps the 1K set other scenes were built with)."""
    swapped = 0
    for image in bpy.data.images:
        path = bpy.path.abspath(image.filepath)
        if "_1k." not in path or "library/models" not in path.replace("\\", "/"):
            continue
        hi = path.replace("_1k.", "_2k.")
        if os.path.exists(hi):
            image.filepath = bpy.path.relpath(hi) if bpy.data.filepath else hi
            image.reload()
            swapped += 1
    return swapped


def place(coll, src, name, x, y, z, yaw=0.0, scale=1.0, tilt=(0.0, 0.0)):
    """A linked copy (shared mesh) of a plant, its foot at (x, y, z)."""
    obj = bpy.data.objects.new(name, src.data)
    coll.objects.link(obj)
    # The game picks its forest templates by this (ForestBorder.ts), and sets them down
    # by their origin, the trunk's foot, not by their lowest point (roots run below it).
    obj["flora"] = src.get("flora", src.name)
    obj["foot_origin"] = 1
    # The foot in the game's space (Babylon x = -x, y = z, z = -y): the asset pipeline's
    # quantisation moves node origins to mesh centres, so the origin can't be trusted.
    obj["foot"] = [-x, z, -y]
    obj.matrix_world = (Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, "Z")
                        @ Matrix.Rotation(tilt[0], 4, "X") @ Matrix.Rotation(tilt[1], 4, "Y")
                        @ Matrix.Scale(scale, 4))
    return obj


def foot_of(obj):
    """A procedural plant's foot: the centre of its lowest vertices (origins sit at 0,0,0)."""
    co = np.array([(obj.matrix_world @ v.co)[:] for v in obj.data.vertices])
    low = co[:, 2].min()
    base = co[co[:, 2] < low + 0.3]
    return float(base[:, 0].mean()), float(base[:, 1].mean())


def ground_under(ground, x, y, r):
    """The lowest ground within r: a trunk set there never floats on a slope."""
    return min(ground(x + dx * r, y + dy * r) for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)))


def lod(f, src, x, y, path_distance, in_yard):
    """The LOD0 source where Sora walks, its LOD1 elsewhere."""
    hot = path_distance(x, y) < 10 or in_yard(x, y, 6) or -66.5 < y < -58.5
    for key, (lod0, lod1, _lod2) in f.items():
        if src is lod0:
            if key == "forest_banyan" or not hot:
                return lod1
            return lod0
    return src


def swap_plants(coll, ground, rng, path_distance, in_yard):
    """Replaces the procedural trees, palms, bamboo, dead trees and bananas with the scans.
    Names stay (tree_N, palm_N, ...) and so do the foot colliders, so the game's
    templates, colliders and omens still find them."""
    f = flora()
    made = {}
    old = [o for o in coll.objects if re.fullmatch(r"(tree|palm|coco|bamboo|dead)_\d+", o.name)]
    for o in old:
        kind, k = o.name.rsplit("_", 1)
        col = bpy.data.objects.get(f"col_{o.name}")
        x, y = (col.location.x, col.location.y) if col else foot_of(o)
        name = o.name
        bpy.data.objects.remove(o, do_unlink=True)
        yaw = rng.uniform(0, math.tau)
        if PADDY_Y[0] < y < PADDY_Y[1] + 5.5 and abs(x) < PADDY_X:
            # Standing in the fields or on the road bank: only a sugar palm stands there.
            src, s, r = f["sugar_palm"][0], rng.uniform(0.9, 1.2), 0.3
        elif y < -52 and kind in ("tree", "dead") and rng.random() < 0.75:
            # The paddies' banks are open country: sugar palms, bamboo and bananas, a
            # big shade tree here and there, never a wall of forest over the fields.
            u = rng.random()
            if u < 0.6:
                src, s, r = f["sugar_palm"][0], rng.uniform(0.9, 1.2), 0.3
            else:
                src, s, r = f["banana_clump"][0], rng.uniform(0.6, 0.8), 1.0
        elif kind == "tree":
            # Strangler figs only well away from the path and yard: their aerial roots
            # hang 8 m out and would brush Sora's face.
            fig = path_distance(x, y) > 10 and not in_yard(x, y, 8) and rng.random() < 0.3
            src = f["forest_banyan"][0] if fig else f["forest_tree_gn"][0]
            s = rng.uniform(0.78, 0.98) if fig else rng.uniform(0.8, 1.12)
            r = 0.9 * s
        elif kind == "palm" and int(k) >= 9000:
            # A sugar palm that took a bamboo clump's place stays a sugar palm.
            src, s, r = f["sugar_palm"][0], rng.uniform(0.9, 1.2), 0.3
        elif kind in ("palm", "coco") and not in_yard(x, y, 10) and y > -52:
            # Sugar palms stand in open fields, not under the forest (the user, Nov 19:
            # "the palm tree should be with the ricefield"): a banana grove takes its place.
            src, s, r = f["banana_clump"][0], rng.uniform(0.6, 0.85), 1.0
        elif kind in ("palm", "coco"):
            src, s, r = f["sugar_palm"][0], rng.uniform(0.82, 1.15), 0.3
        elif kind == "bamboo":
            # No bamboo any more: a banana clump or a sugar palm, named for what it is now
            # (the game hears a plant by its name). Its old collider goes; a palm gets a
            # trunk's.
            if col:
                bpy.data.objects.remove(col, do_unlink=True)
                col = None
            if rng.random() < 0.6:
                src, s, r = f["banana_clump"][0], rng.uniform(0.62, 0.85), 1.0
                name = f"banana_{9000 + int(k)}"
            else:
                src, s, r = f["sugar_palm"][0], rng.uniform(0.9, 1.2), 0.3
                name = f"palm_{9000 + int(k)}"
                trunk = bpy.data.meshes.new(f"col_{name}")
                bm = bmesh.new()
                bmesh.ops.create_cube(bm, size=1)
                bm.to_mesh(trunk)
                bm.free()
                tc = bpy.data.objects.new(trunk.name, trunk)
                coll.objects.link(tc)
                tc.location = (x, y, ground(x, y) + 1.6)
                tc.scale = (0.56, 0.56, 3.2)
                tc.display_type = "WIRE"
                tc.hide_render = True
                tc["surface"] = "leaves"
        else:
            # The old dead trees come back leafy: no leafless trees anywhere (the user,
            # Nov 19: "remove all no leaf tree").
            src, s, r = f["forest_tree_gn"][0], rng.uniform(0.62, 0.86), 0.6
        tilt = (rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05)) if src is f["sugar_palm"][0] else (0, 0)
        # Full detail where Sora walks (the path, the compound, the road bank); the
        # lighter LOD elsewhere; the forest's figs always light (111k at full detail).
        src = lod(f, src, x, y, path_distance, in_yard)
        obj = place(coll, src, name, x, y, ground_under(ground, x, y, r) - 0.04, yaw, s, tilt)
        obj["forest_height"] = float(s)
        made[name] = obj
    # Bananas: the old single plants stood in groups by the houses; one scanned clump
    # (several plants, suckers and dead leaves) takes each group.
    bananas = [o for o in coll.objects if re.fullmatch(r"banana_\d+", o.name)]
    feet = [(o.name, *foot_of(o)) for o in bananas]
    for o in bananas:
        bpy.data.objects.remove(o, do_unlink=True)
    groups = []
    for name, x, y in feet:
        for g in groups:
            if math.hypot(g["x"] - x, g["y"] - y) < 6.5:
                g["pts"].append((x, y))
                g["x"] = sum(p[0] for p in g["pts"]) / len(g["pts"])
                g["y"] = sum(p[1] for p in g["pts"]) / len(g["pts"])
                break
        else:
            groups.append({"name": name, "x": x, "y": y, "pts": [(x, y)]})
    for g in groups:
        s = rng.uniform(0.62, 0.82) * (1.0 if len(g["pts"]) > 1 else 0.85)
        obj = place(coll, lod(f, f["banana_clump"][0], g["x"], g["y"], path_distance, in_yard), g["name"], g["x"], g["y"],
                    ground_under(ground, g["x"], g["y"], 1.2) - 0.03, rng.uniform(0, math.tau), s)
        made[g["name"]] = obj
    return made


def spirit_banyan(coll, ground, path_distance):
    """The Neak Ta shrine's banyan: the scanned fig, its own copy, with the aerial roots
    that would hang through the path, the shrine roof or the spirit house cut away, and
    the villagers' cloth bands refitted round its real trunk."""
    src = flora()["forest_banyan"][0]
    old = bpy.data.objects.get("banyan")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    me = src.data.copy()
    obj = bpy.data.objects.new("banyan", me)
    coll.objects.link(obj)
    x, y = BANYAN
    s = 1.0
    # Turned so its heaviest limbs reach west, away from the path.
    obj.matrix_world = Matrix.Translation((x, y, ground_under(ground, x, y, 1.2) - 0.06)) \
        @ Matrix.Rotation(math.radians(200), 4, "Z") @ Matrix.Scale(s, 4)
    me.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    # The shrine's own procedural roots go: the scanned banyan's roots come down round it.
    stick = bpy.data.objects.get("neakta_shrine_wet_bark")
    if stick:
        bpy.data.objects.remove(stick, do_unlink=True)
    keep_out = [((SHRINE[0], SHRINE[1]), (1.12, 1.4)), ((-4.1, -36.5), (0.75, 0.65))]
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    seen = set()
    doomed = []
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        stack, island = [f0], []
        seen.add(f0.index)
        while stack:
            g = stack.pop()
            island.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        co = [v.co for g in island for v in g.verts]
        zmin = min(c.z for c in co)
        if zmin > 3.2 or len(island) > 20000:
            continue        # crown pieces and the trunk itself
        low = [c for c in co if c.z < 3.2]
        hit = any(path_distance(c.x, c.y) < 2.4 for c in low[::3]) or any(
            abs(c.x - cx) < hx and abs(c.y - cy) < hy for (cx, cy), (hx, hy) in keep_out for c in low[::3])
        if hit:
            doomed.extend(island)
    bmesh.ops.delete(bm, geom=list(set(doomed)), context="FACES")
    bm.to_mesh(me)
    bm.free()
    refit_cloth(obj, *trunk_axis(obj, x, y))
    return obj


def trunk_axis(tree, x, y):
    """Where the trunk actually stands at the bands' height: the centroid of the bark
    within 2 m of the planting point, 0.9-1.7 m up."""
    ring = [v.co for v in tree.data.vertices if 0.9 < v.co.z < 1.7 and math.hypot(v.co.x - x, v.co.y - y) < 2.0]
    if len(ring) < 20:
        return x, y
    return sum(p.x for p in ring) / len(ring), sum(p.y for p in ring) / len(ring)


def refit_cloth(tree, x, y):
    """Moves the cloth bands' vertices radially onto the new trunk (a ray from outside
    at each vertex's height and bearing), 2 cm proud of the bark."""
    cloth = bpy.data.objects.get("banyan_cloth")
    if not cloth:
        return
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mw = cloth.matrix_world
    inv = mw.inverted()
    radii = {}
    for v in cloth.data.vertices:
        p = mw @ v.co
        a = math.atan2(p.y - y, p.x - x)
        key = (round(a, 2), round(p.z, 2))
        if key not in radii:
            # Outward from the trunk's heart: the first bark met is the trunk's own skin,
            # never one of the aerial roots hanging a few metres off.
            origin = Vector((x, y, p.z))
            d = Vector((math.cos(a), math.sin(a), 0))
            ok, hit, *_ = tree.ray_cast(origin, d, distance=2.2, depsgraph=depsgraph)
            radii[key] = min(1.8, math.hypot(hit.x - x, hit.y - y)) if ok else None
        r = radii[key]
        if r is None:
            continue
        q = Vector((x + (r + 0.02) * math.cos(a), y + (r + 0.02) * math.sin(a), p.z))
        v.co = inv @ q
    cloth.data.update()


def litter_ground():
    """The forest floor material becomes the scanned decaying-leaf litter (2K)."""
    mat = bpy.data.materials["M_wet_forest_floor"]
    swaps = {"brown_mud_leaves_01": "dry_decay_leaves"}
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            for a, b in swaps.items():
                if a in n.image.filepath:
                    path = os.path.join(LIB, "materials", b, os.path.basename(n.image.filepath).replace(a, b))
                    img = bpy.data.images.load(path, check_existing=True)
                    img.colorspace_settings.name = n.image.colorspace_settings.name
                    n.image = img
    # The scans' leaves are crisp and dry: wet them a shade darker, as the paths are.
    mix = next((n for n in mat.node_tree.nodes if n.type == "MIX" and n.data_type == "RGBA"), None)
    if mix is not None and not mat.get("litter_wet"):
        mix.inputs[7].default_value = tuple(c * 0.82 for c in mix.inputs[7].default_value[:3]) + (1,)
        mat["litter_wet"] = True
    return mat


def library_material(key, name, tile=2.0, tint=None):
    """A Poly Haven ground material (BC, N, ORM) for world-mapped meshes."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    d = os.path.join(LIB, "materials", key)
    bc = nt.nodes.new("ShaderNodeTexImage")
    bc.image = bpy.data.images.load(os.path.join(d, f"{key}_BC.jpg"), check_existing=True)
    if tint:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1
        mix.inputs["B"].default_value = (*tint, 1)
        nt.links.new(bc.outputs["Color"], mix.inputs["A"])
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    else:
        nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    nm = nt.nodes.new("ShaderNodeTexImage")
    nm.image = bpy.data.images.load(os.path.join(d, f"{key}_N.jpg"), check_existing=True)
    nm.image.colorspace_settings.name = "Non-Color"
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nm.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    orm = nt.nodes.new("ShaderNodeTexImage")
    orm.image = bpy.data.images.load(os.path.join(d, f"{key}_ORM.jpg"), check_existing=True)
    orm.image.colorspace_settings.name = "Non-Color"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    mat["tile"] = tile
    return mat


# ------------------------------------------------------------------ paddies


def paddy_plots():
    """The fields between the dikes: (x0, x1, y0, y1, kind). Green rice at grain filling
    in most; the far row and two plots by the old field hut ripe and golden (the farm
    field); the plot the flooded road runs into is drowned, the rice lodged under water."""
    xs = [-PADDY_X] + list(BUND_X) + [PADDY_X]
    ys = [PADDY_Y[0]] + sorted(BUND_Y) + [PADDY_Y[1]]
    plots = []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            x0, x1, y0, y1 = xs[i] + 0.45, xs[i + 1] - 0.45, ys[j] + 0.45, ys[j + 1] - 0.45
            cx = (x0 + x1) / 2
            if j == 0 or (j == 1 and cx > 20):
                kind = "ripe"
            elif j == 2 and -20 < cx < -6:
                kind = "drowned"
            else:
                kind = "green"
            plots.append((x0, x1, y0, y1, kind))
    return plots


def rice_material(name, image_path):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path, check_existing=True)
    tex.image.alpha_mode = "STRAIGHT"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    less = nt.nodes.new("ShaderNodeMath")
    less.operation = "LESS_THAN"
    less.inputs[1].default_value = 0.5
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs["Alpha"], less.inputs[0])
    nt.links.new(less.outputs["Value"], sub.inputs[1])
    nt.links.new(sub.outputs["Value"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.7
    bsdf.inputs["Specular IOR Level"].default_value = 0.35
    mat.surface_render_method = "DITHERED"
    mat.use_backface_culling = False
    return mat


def rice_cards(coll, rng, textures, row=0.5, strip=(2.0, 1.25)):
    """Stands the rendered rice strips up as cards along the rows of every planted plot,
    in 12 m cells (one mesh per cell and kind): rows run east-west, every `row` m, each
    card a strip `strip[0]` m wide; every few metres a short card across the rows, so
    the field has body seen along the rows too. Cards stand in the water, their roots
    under its surface; normals lean up and out so the field shades like a crop."""
    w, h = strip
    cells = {}
    for x0, x1, y0, y1, kind in paddy_plots():
        tex = "ripe" if kind == "ripe" else "green"
        top = {"ripe": 1.0, "green": 1.0, "drowned": 0.55}[kind]
        y = y0 + rng.uniform(0, row)
        while y < y1:
            # Rows start and end a hill or two short of the dike at random, so a plot's
            # edge is ragged, never a wall of card ends.
            x = x0 - rng.uniform(0, w * 0.5)
            end = x1 - rng.uniform(0, 0.7)
            start = x0 + rng.uniform(0, 0.7)
            while x < end:
                k = rng.uniform(0.8, 1.12) * top
                a = rng.uniform(-0.08, 0.08)
                ax = Vector((math.cos(a), math.sin(a), 0))
                p0 = Vector((max(x, start), y + rng.uniform(-0.05, 0.05), WATER_Z - 0.12))
                length = min(w, end - p0.x, x + w - p0.x)
                if length > 0.3:
                    u0 = rng.choice([0.0, 0.5]) if length < w else 0.0
                    u1 = u0 + length / w
                    key = (int(p0.x // 12), int(p0.y // 12), tex)
                    cells.setdefault(key, []).append((p0, ax * length, h * k, u0, min(1.0, u1),
                                                     kind == "drowned"))
                x += w * rng.uniform(0.92, 1.0)
            y += row * rng.uniform(0.9, 1.1)
        # Short cards across the rows.
        for _ in range(int((x1 - x0) * (y1 - y0) / 7)):
            cx, cy = rng.uniform(x0, x1), rng.uniform(y0, y1 - 0.8)
            ax = Vector((0, 1, 0))
            key = (int(cx // 12), int(cy // 12), tex)
            cells.setdefault(key, []).append((Vector((cx, cy, WATER_Z - 0.12)), ax * 0.8, h * rng.uniform(0.85, 1.05) * top,
                                              rng.uniform(0, 0.55), 0, kind == "drowned"))
    out = []
    for (i, j, tex), cards in cells.items():
        verts, faces, uvs, normals = [], [], [], []
        for p0, along, height, u0, u1, lodged in cards:
            if u1 <= u0:
                u1 = u0 + along.length / w
            # Each card leans a little forward or back: the field's top undulates.
            side0 = along.normalized().cross(Vector((0, 0, 1)))
            up = Vector((0, 0, height)) + side0 * rng.uniform(-0.14, 0.14)
            if lodged:
                up = Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.6, -0.3), height * 0.7))
            b = len(verts)
            verts += [p0, p0 + along, p0 + along + up, p0 + up]
            faces.append((b, b + 1, b + 2, b + 3))
            uvs += [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]
            side = along.normalized().cross(Vector((0, 0, 1)))
            for t in (0, 0, 1, 1):
                n = (Vector((0, 0, 0.55 + 0.45 * t)) + side * 0.6).normalized()
                normals.append(n)
        me = bpy.data.meshes.new(f"paddy_rice_{tex}_{i}_{j}")
        me.from_pydata([v[:] for v in verts], [], faces)
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
        me.materials.append(textures[tex])
        loop_normals = [normals[me.loops[li].vertex_index] for li in range(len(me.loops))]
        me.normals_split_custom_set([n[:] for n in loop_normals])
        obj = bpy.data.objects.new(me.name, me)
        coll.objects.link(obj)
        out.append(obj)
    return out


def bunds(coll, ground, rng, mud):
    """The dikes between the paddies: low earth banks a little above the water, crowned,
    their sides slumped, worn hollow where people walk."""
    out = []
    lines = [((x, PADDY_Y[0]), (x, PADDY_Y[1])) for x in BUND_X] + \
            [((-PADDY_X, y), (PADDY_X, y)) for y in BUND_Y]
    for k, (a, b) in enumerate(lines):
        a, b = Vector((*a, 0)), Vector((*b, 0))
        length = (b - a).length
        along = (b - a).normalized()
        side = Vector((-along.y, along.x, 0))
        n = int(length / 0.5)
        verts, faces, uvs = [], [], []
        profile = [(-0.75, PADDY_FLOOR - 0.02), (-0.42, WATER_Z + 0.02), (-0.22, WATER_Z + 0.13),
                   (0.0, WATER_Z + 0.16), (0.22, WATER_Z + 0.13), (0.42, WATER_Z + 0.02), (0.75, PADDY_FLOOR - 0.02)]
        for i in range(n + 1):
            t = i / n
            p = a + along * (t * length)
            wob = 0.08 * math.sin(t * length * 0.7 + k) + 0.04 * math.sin(t * length * 2.3)
            sag = 0.03 * math.sin(t * length * 0.31 + k * 2)
            for s, z in profile:
                q = p + side * (s * (1 + 0.15 * math.sin(t * 9 + s)) + wob)
                verts.append((q.x, q.y, z - sag * (1 if abs(s) < 0.3 else 0)))
                uvs.append((q.x / 2.0, q.y / 2.0))
        m = len(profile)
        for i in range(n):
            for j in range(m - 1):
                c = i * m + j
                faces.append((c, c + 1, c + m + 1, c + m))
        me = bpy.data.meshes.new(f"paddy_bund_{k}")
        me.from_pydata(verts, [], faces)
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
        me.materials.append(mud)
        for poly in me.polygons:
            poly.use_smooth = True
        obj = bpy.data.objects.new(me.name, me)
        coll.objects.link(obj)
        out.append(obj)
    return out


# ------------------------------------------------------------------ forest floor


# Triangles a piece of floor cover may have in the game (the scans run to 225k).
BUDGET = {
    "bark_debris_01": 900, "dry_branches_medium_01": 1200, "root_cluster_01": 2500, "root_cluster_02": 2500,
    "single_root": 1800, "tree_stump_01": 3000, "tree_stump_02": 3000, "dead_tree_trunk": 4000,
    "dead_tree_trunk_02": 4000, "anthurium_botany_01": 1800, "periwinkle_plant": 1400, "nettle_plant": 1400,
    "shrub_02": 2400, "shrub_03": 1800, "shrub_04": 3000, "calathea_orbifolia_01": 1600, "weed_plant_02": 1400,
    "fern_02": 1200, "grass_medium_01": 900, "grass_medium_02": 900,
}


def poly_haven(model, res="2k"):
    """A Poly Haven model's meshes (its 2K set where fetched), imported once into _protos
    and decimated to its BUDGET, so the copies the village places stay affordable."""
    path = os.path.join(LIB, "models", model, f"{model}_{res}.gltf")
    if not os.path.exists(path):
        path = os.path.join(LIB, "models", model, f"{model}.gltf")
    objs = import_scan(model, path)
    meshes = [o for o in objs.values() if o.type == "MESH" and len(o.data.polygons) > 0]
    budget = BUDGET.get(model)
    for o in meshes:
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        if budget and tris > budget * 1.15 and not o.get("budgeted"):
            decimate(o, budget / tris)
            o["budgeted"] = budget
    return meshes


def decimate(obj, ratio):
    mod = obj.modifiers.new("decimate", "DECIMATE")
    mod.ratio = max(0.002, ratio)
    mod.use_collapse_triangulate = True
    depsgraph = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    obj.modifiers.remove(mod)
    old = obj.data
    obj.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)


def _low_point(src):
    co = [v.co for v in src.data.vertices]
    return Vector((sum(v.x for v in co) / len(co), sum(v.y for v in co) / len(co), min(v.z for v in co)))


_feet = {}


def put(coll, src, x, y, ground, yaw, s, sink=0.02, z=None):
    """A linked copy of a small scan, its lowest point `sink` m into the ground."""
    if src.name not in _feet:
        _feet[src.name] = _low_point(src)
    obj = bpy.data.objects.new(f"{src.name.split('.')[0]}_n", src.data)
    coll.objects.link(obj)
    # On the lowest ground under its whole footprint: a log's ends never hang over a dip.
    reach = 0.7 * s * max(src.dimensions.x, src.dimensions.y) / 2
    zz = (ground_under(ground, x, y, reach) if z is None else z) - sink
    obj.matrix_world = (Matrix.Translation((x, y, zz)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Scale(s, 4)
                        @ Matrix.Translation(-_feet[src.name]))
    return obj


def obstacles():
    out = []
    for o in bpy.data.objects:
        if o.name.startswith("col_") and o.type == "MESH" and o.name != "col_ground":
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            out.append((min(p.x for p in bb), max(p.x for p in bb), min(p.y for p in bb), max(p.y for p in bb)))
    return out


def floor_cover(coll, ground, rng, path_distance, in_yard):
    """Scanned understory and litter over the forest floor beside the walk and round the
    compound (the game grows the rest of the forest's floor at runtime): denser within
    8 m of the path, never on it, in the yard, the paddies or a building's footprint;
    logs, stumps and stones kept back from the trodden line."""
    under = {
        "anthurium": poly_haven("anthurium_botany_01"), "calathea": poly_haven("calathea_orbifolia_01"),
        "fern": poly_haven("fern_02"), "shrub": poly_haven("shrub_02") + poly_haven("shrub_03") + poly_haven("shrub_04"),
        "nettle": poly_haven("nettle_plant"), "weed": poly_haven("weed_plant_02"), "periwinkle": poly_haven("periwinkle_plant"),
    }
    litter = {
        "bark": poly_haven("bark_debris_01"), "branch": poly_haven("dry_branches_medium_01"),
        "root": poly_haven("single_root"),
        "stump": poly_haven("tree_stump_01") + poly_haven("tree_stump_02"),
        "log": poly_haven("dead_tree_trunk") + poly_haven("dead_tree_trunk_02"),
    }
    unify_palette()
    boxes = obstacles()

    def clear(x, y, r):
        return not any(a - r < x < b + r and c - r < y < d + r for a, b, c, d in boxes)

    def floor(x, y):
        return (-64 < x < 64 and -91 < y < 60 and not (-86.5 < y < -60.2) and not in_yard(x, y, 1.5)
                and path_distance(x, y) > 1.6)

    counts = {"understory": 0, "litter": 0}
    # Where Sora walks: beside the path and round the compound's fence. The game's
    # forest past it carries its own undergrowth (ForestBorder.ts).
    def near(x, y, d):
        return d < 11 or (in_yard(x, y, 7) and not in_yard(x, y, 1.5))

    for _ in range(9000):
        # Half the earlier cover (the road and its fields are open country now, and it
        # cost the frame rate: about 1.4 M triangles in view from the road, Nov 19).
        if counts["understory"] >= 600:
            break
        x, y = rng.uniform(-40, 40), rng.uniform(-60, 40)
        d = path_distance(x, y)
        if not floor(x, y) or not near(x, y, d) or not clear(x, y, 0.4) or d < 2.6 \
                or rng.random() > (0.9 if d < 6 else 0.5):
            continue
        kind = rng.choice(["anthurium", "calathea", "fern", "fern", "shrub", "nettle", "weed", "periwinkle", "fern"])
        src = under[kind][int(rng.integers(len(under[kind])))]
        put(coll, src, x, y, ground, rng.uniform(0, math.tau), rng.uniform(0.8, 1.5) * (0.7 if kind == "periwinkle" else 1))
        counts["understory"] += 1
    for _ in range(9000):
        if counts["litter"] >= 450:
            break
        x, y = rng.uniform(-40, 40), rng.uniform(-60, 40)
        d = path_distance(x, y)
        if not floor(x, y) or not near(x, y, d) or not clear(x, y, 0.3) or d < 2.4:
            continue
        # No stones: the village stands on the flat alluvial plain (the user, Nov 19:
        # "remove some unnecessary big rock").
        # No root clusters: they read as brown blobs by the path (the user, Nov 19).
        kind = rng.choice(["bark", "bark", "bark", "branch", "branch", "root", "stump", "log"],
                          p=[.24, .18, .18, .18, .1, .07, .03, .02])
        if kind in ("log", "stump") and d < 6.5:
            kind = "bark"
        src = litter[kind][int(rng.integers(len(litter[kind])))]
        put(coll, src, x, y, ground, rng.uniform(0, math.tau), rng.uniform(0.8, 1.3),
            sink=0.08 if kind in ("log", "stump") else 0.03)
        counts["litter"] += 1
    return counts


def bund_grass(coll, dikes, rng):
    """Short Bermuda grass along the dikes' crowns, out of the water."""
    bermuda = poly_haven("grass_bermuda_01")
    n = 0
    for b in dikes:
        vs = b.data.vertices
        for i in range(0, len(vs), 7):
            v = vs[i].co
            if v.z > WATER_Z + 0.1 and rng.random() < 0.8:
                put(coll, bermuda[int(rng.integers(len(bermuda)))], v.x + rng.normal(0, .12), v.y + rng.normal(0, .12),
                    None, rng.uniform(0, math.tau), rng.uniform(1.2, 2.2), sink=0.01, z=v.z)
                n += 1
    return n


def rice_canopy(coll, rng, textures, tile=2.0):
    """The crop's top seen from the road bank: near-level cards of the canopy rendered
    from above (rice_field.render_top) at panicle height over every planted plot, each
    turned a quarter at random and tipped a little, so the field reads as a crop and not
    as rows of boards when looked down on."""
    cells = {}
    for x0, x1, y0, y1, kind in paddy_plots():
        tex = "ripe" if kind == "ripe" else "green"
        top = 0.86 if kind != "drowned" else 0.45
        y = y0 + 0.1
        while y < y1 - 0.4:
            x = x0 + 0.1
            while x < x1 - 0.4:
                s = min(tile, x1 - x, y1 - y)
                z = WATER_Z - 0.12 + top * rng.uniform(0.9, 1.06)
                key = (int(x // 12), int(y // 12), tex)
                cells.setdefault(key, []).append((x, y, s, z, int(rng.integers(4)),
                                                  rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08)))
                x += tile * rng.uniform(0.82, 0.95)
            y += tile * rng.uniform(0.82, 0.95)
    out = []
    corners = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for (i, j, tex), tiles in cells.items():
        verts, faces, uvs = [], [], []
        for x, y, s, z, turn, tx, ty in tiles:
            b = len(verts)
            for cx, cy in corners:
                verts.append((x + cx * s, y + cy * s, z + (cx - 0.5) * tx * s + (cy - 0.5) * ty * s))
                u, v = corners[(corners.index((cx, cy)) + turn) % 4]
                uvs.append((u * s / tile, v * s / tile))
            faces.append((b, b + 1, b + 2, b + 3))
        me = bpy.data.meshes.new(f"paddy_canopy_{tex}_{i}_{j}")
        me.from_pydata(verts, [], faces)
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
        me.materials.append(textures[tex])
        obj = bpy.data.objects.new(me.name, me)
        coll.objects.link(obj)
        out.append(obj)
    return out


def field_palms(coll, ground, rng):
    """Sugar palms (thnot) over the paddies, the Khmer countryside's own skyline (the
    user, Nov 19: "suitable for khmer country side view", "the palm tree should be with
    the ricefield"): singly and in twos and threes along the dikes, a group where dikes
    meet, a line of them along the far bank above its bamboo, all of their own height
    and lean. Palms near the road bank are full detail; the far ones the lighter LOD.
    Each gets a trunk collider, as the village's palms have."""
    lod0, lod1, _ = flora()["sugar_palm"]
    spots = []

    def group(x, y, z, n):
        for i in range(n):
            a, d = rng.uniform(0, math.tau), (0 if i == 0 else rng.uniform(2.6, 4.0))
            spots.append((x + math.cos(a) * d * (0.3 if z is not None else 1),
                          y + math.sin(a) * d * (1.0 if z is not None else 0.4), z))

    for x in BUND_X:                      # along the north-south dikes, set back from the road
        for _ in range(int(rng.integers(1, 3))):
            group(x + rng.normal(0, 0.1), rng.uniform(PADDY_Y[0] + 1.5, PADDY_Y[1] - 5.0), WATER_Z + 0.12,
                  int(rng.choice([1, 1, 1, 2])))
    for y in BUND_Y:                      # along the east-west dikes
        for _ in range(int(rng.integers(3, 5))):
            group(rng.uniform(-PADDY_X + 2, PADDY_X - 2), y + rng.normal(0, 0.1), WATER_Z + 0.12,
                  int(rng.choice([1, 1, 2])))
    for x in BUND_X[1::3]:                # a pair where two dikes meet
        group(x, BUND_Y[int(rng.integers(2))], WATER_Z + 0.12, 2)
    for _ in range(12):                   # the far bank, where the tree line begins
        group(rng.uniform(-62, 62), rng.uniform(-91.0, -87.2), None, int(rng.choice([1, 1, 2])))
    out = []
    taken = []
    for k, (x, y, z) in enumerate(spots):
        on_dike = z is not None
        # Sparse, as palms stand over Khmer paddies: a pair at most, otherwise well apart.
        near = [math.hypot(x - a, y - b) for a, b in taken]
        if abs(x) > 64 or any(d < 2.4 for d in near) or sum(d < 7 for d in near) > 1:
            continue
        if on_dike and min(min(abs(x - bx) for bx in BUND_X), min(abs(y - by) for by in BUND_Y)) > 0.3:
            continue                     # a group spilled off its dike into the water
        taken.append((x, y))
        zz = ground_under(ground, x, y, 0.3) if z is None else z
        src = lod0 if y > -72 else lod1
        s = rng.uniform(0.95, 1.38)
        obj = place(coll, src, f"palm_field_{k}", x, y, zz - 0.05, rng.uniform(0, math.tau), s,
                    (rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06)))
        col = bpy.data.objects.get(f"col_palm_field_{k}")
        if col is None:
            me = bpy.data.meshes.new(f"col_palm_field_{k}")
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1)
            bm.to_mesh(me)
            bm.free()
            col = bpy.data.objects.new(f"col_palm_field_{k}", me)
            coll.objects.link(col)
            col.display_type = "WIRE"
            col.hide_render = True
        col.location = (x, y, zz + 1.5)
        col.scale = (0.5, 0.5, 3.0)
        col["surface"] = "mud"
        out.append(obj)
    return out


BOULDER = re.compile(r"^rock_moss_set_01_rock\d+\.\d+$")


def remove_boulders():
    """The mossy granite boulders go: the Khmer plain has none (the user, Nov 19)."""
    gone = [o for o in bpy.data.objects if BOULDER.match(o.name) and o.users_collection
            and o.users_collection[0].name != "_protos"]
    for o in gone:
        bpy.data.objects.remove(o, do_unlink=True)
    return len(gone)


def rice_hills(coll, rng, atlases, spacing=0.3, cells=4, width=0.62, height=1.24):
    """The paddies planted hill by hill, as transplanted rice stands: a hill every
    `spacing` m in rough rows (a little off-line, a few missing), each two crossed cards
    of one rendered hill (rice_field.render_hills) at its own turn and height. Merged per
    12 m cell and crop; normals rounded up and out so each tuft shades as a tuft."""
    meshes = {}
    for x0, x1, y0, y1, kind in paddy_plots():
        crop = "ripe" if kind == "ripe" else "green"
        top = 0.55 if kind == "drowned" else 1.0
        y = y0 + rng.uniform(0.05, spacing)
        while y < y1:
            x = x0 + rng.uniform(0.05, spacing)
            while x < x1:
                if rng.random() > 0.04:
                    hx, hy = x + rng.normal(0, 0.03), y + rng.normal(0, 0.03)
                    k = rng.uniform(0.86, 1.1) * top
                    cell = int(rng.integers(cells))
                    yaw = rng.uniform(0, math.pi)
                    lean = (rng.normal(0, 0.06), rng.normal(0, 0.06))
                    if kind == "drowned":
                        lean = (rng.uniform(-0.5, 0.5), rng.uniform(-0.9, -0.4))   # lodged by the flood
                    key = (int(hx // 12), int(hy // 12), crop)
                    meshes.setdefault(key, []).append((hx, hy, k, cell, yaw, lean))
                x += spacing
            y += spacing
    out = []
    for (i, j, crop), hills in meshes.items():
        verts, faces, uvs, normals = [], [], [], []
        for hx, hy, k, cell, yaw, lean in hills:
            u0, u1 = cell / cells, (cell + 1) / cells
            for turn in (0.0, math.pi / 2):
                a = yaw + turn
                ax = Vector((math.cos(a), math.sin(a), 0)) * (width * k / 2)
                up = Vector((lean[0], lean[1], 1)).normalized() * (height * k)
                base = Vector((hx, hy, WATER_Z - 0.12))
                b = len(verts)
                verts += [base - ax, base + ax, base + ax + up, base - ax + up]
                faces.append((b, b + 1, b + 2, b + 3))
                uvs += [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]
                side = Vector((-math.sin(a), math.cos(a), 0))
                for t, sx in ((0, -1), (0, 1), (1, 1), (1, -1)):
                    normals.append((Vector((0, 0, 0.45 + 0.5 * t)) + ax.normalized() * 0.45 * sx).normalized())
        me = bpy.data.meshes.new(f"paddy_rice_{crop}_{i}_{j}")
        me.from_pydata([v[:] for v in verts], [], faces)
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
        me.materials.append(atlases[crop])
        me.normals_split_custom_set([normals[me.loops[li].vertex_index][:] for li in range(len(me.loops))])
        obj = bpy.data.objects.new(me.name, me)
        coll.objects.link(obj)
        out.append(obj)
    return out


CLUTTER = re.compile(r"^(col_)?(ragtree_\d+|old_flag_\d+|termite_\d+)$")


def remove_clutter():
    """What the user asked gone (Nov 19): the rag trees (dead stubs hung with cloth,
    rope and coconut-shell pots), the old crocodile flags on bare poles along the path
    and the termite mounds. The funeral's own flag at the house stays."""
    gone = [o for o in bpy.data.objects if CLUTTER.match(o.name)]
    names = sorted(o.name for o in gone)
    for o in gone:
        bpy.data.objects.remove(o, do_unlink=True)
    return names


def scarecrows():
    """The Ting Mong become the user's scarecrow (Smartinius Scarecrow, CC BY 4.0): the
    same objects, so names, foot pivots, `front` extras and colliders stay and the
    watchers still turn (Apparitions.ts). Its front is local -Y, as the old figures';
    the stake goes 0.3 m into the ground as theirs did."""
    src = import_scan("scarecrow")["scarecrow"]
    done = []
    for o in bpy.data.objects:
        if not re.fullmatch(r"tingmong_\d+", o.name) or o.type != "MESH":
            continue
        facing = float(o.get("front", -math.pi / 2)) + math.pi / 2
        me = src.data.copy()
        me.name = f"{o.name}_scarecrow"
        me.transform(Matrix.Translation((0, 0, -0.3)) @ Matrix.Rotation(facing, 4, "Z"))
        old = o.data
        o.data = me
        if old.users == 0:
            bpy.data.meshes.remove(old)
        o["flora"] = "scarecrow"
        done.append(o.name)
    return done


def more_bananas(coll, ground, rng, path_distance, in_yard, n=34):
    """Banana groves where a Khmer household keeps them: round the compound's fence,
    beside the path as it nears the house, along the road bank and by the wells; never
    on a path or lane, never in a building's footprint, 5 m apart at least."""
    src = flora()["banana_clump"][0]
    for o in [o for o in coll.objects if re.fullmatch(r"banana_g\d+(\.\d+)?", o.name)]:
        bpy.data.objects.remove(o, do_unlink=True)
    boxes = obstacles()
    have = [(o.location.x, o.location.y) for o in coll.objects if re.match(r"banana_", o.name)]

    def ok(x, y):
        if path_distance(x, y) < 3.6 or in_yard(x, y, 0.5):
            return False
        if any(a - 2 < x < b + 2 and c - 2 < y < d + 2 for a, b, c, d in boxes):
            return False
        return all(math.hypot(x - a, y - b) > 5 for a, b in have)

    zones = [
        lambda: (rng.uniform(-22, 22), rng.uniform(-11, 40), lambda x, y: in_yard(x, y, 9) and not in_yard(x, y, 1.5)),
        lambda: (rng.uniform(-9, 9), rng.uniform(-22, -4), lambda x, y: 3.6 < path_distance(x, y) < 9),
        lambda: (rng.uniform(-40, 40), rng.uniform(-60.2, -55), lambda x, y: True),
    ]
    out = []
    for _ in range(4000):
        if len(out) >= n:
            break
        x, y, test = zones[int(rng.integers(len(zones)))]()
        if not test(x, y) or not ok(x, y):
            continue
        obj = place(coll, lod(flora(), src, x, y, path_distance, in_yard), f"banana_g{len(out)}", x, y,
                    ground_under(ground, x, y, 1.0) - 0.03, rng.uniform(0, math.tau), rng.uniform(0.55, 0.85))
        have.append((x, y))
        out.append(obj)
    return out


TEMPLATE_KEYS = ("forest_tree_gn", "forest_tree_gn_lod1", "forest_tree_gn_lod2",
                 "forest_banyan_lod2", "sugar_palm_lod1", "sugar_palm_lod2",
                 "banana_clump_lod1", "banana_clump_lod2")


def templates(far_atlas):
    """One of each scan for the game's runtime forest (ForestBorder.ts copies them past
    the walls and never draws these), a card carrying the far-forest atlas rendered from
    the scans, and a clump of scanned grass for the tall grass (TallGrass.ts). They live
    in the exported collection `nature_templates`, 60 m under the village."""
    coll = bpy.data.collections.get("nature_templates")
    if coll is None:
        coll = bpy.data.collections.new("nature_templates")
        bpy.context.scene.collection.children.link(coll)
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    f = flora()
    by_name = {**{k: f[k][0] for k in FLORA}, **{f"{k}_lod1": f[k][1] for k in FLORA},
               **{f"{k}_lod2": f[k][2] for k in FLORA}, "forest_tree_gn_dead": f["dead"][0]}
    for i, key in enumerate(TEMPLATE_KEYS):
        place(coll, by_name[key], f"tpl_{key}", 30.0 * i, 0, -60)
    # The far-forest atlas on a plain card.
    mat = bpy.data.materials.get("M_forest_far_cards_scan") or rice_material("M_forest_far_cards_scan", far_atlas)
    me = bpy.data.meshes.new("tpl_far_cards")
    me.from_pydata([(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for li, (u, v) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[li].uv = (u, v)
    me.materials.append(mat)
    card = bpy.data.objects.new("tpl_far_cards", me)
    coll.objects.link(card)
    card.location = (-30, 0, -60)
    # A clump of tall grass (smau) from the scanned grass, about a metre high.
    pieces = sorted(poly_haven("grass_medium_01"), key=lambda o: -max(o.dimensions))[:4]
    bm = bmesh.new()
    rng = np.random.default_rng(6242071)
    for k, src in enumerate(pieces):
        tmp = bmesh.new()
        tmp.from_mesh(src.data)
        co = [v.co for v in tmp.verts]
        low = Vector((sum(c.x for c in co) / len(co), sum(c.y for c in co) / len(co), min(c.z for c in co)))
        h = max(c.z for c in co) - low.z
        a = k * math.tau / len(pieces) + rng.uniform(-0.4, 0.4)
        off = Vector((math.cos(a), math.sin(a), 0)) * (0.06 if k else 0.0)
        bmesh.ops.transform(tmp, verts=tmp.verts, matrix=Matrix.Translation(off) @ Matrix.Rotation(a, 4, "Z")
                            @ Matrix.Scale(0.95 / max(h, 0.05), 4) @ Matrix.Translation(-low))
        me2 = bpy.data.meshes.new("tmp_grass")
        tmp.to_mesh(me2)
        tmp.free()
        bm.from_mesh(me2)
        bpy.data.meshes.remove(me2)
    me = bpy.data.meshes.new("tpl_grass_clump")
    bm.to_mesh(me)
    bm.free()
    for m in pieces[0].data.materials:
        me.materials.append(m)
    grass = bpy.data.objects.new("tpl_grass_clump", me)
    coll.objects.link(grass)
    grass.location = (-60, 0, -60)
    grass["foot_origin"] = 1
    grass["foot"] = [60.0, -60.0, 0.0]
    return coll


ROOT_BLOBS = ("root_cluster_01.001", "root_cluster_01.002")


def settle(names, tol=0.012):
    """Sets each loose part of the named objects down onto whatever is under it (the
    ground, a tray, a mat), if it floats more than `tol`: the old offerings' rice grains,
    firewood, a cart's stains, puddles (the audit, Nov 19). Root-cluster scans that float
    by the path go (the user: no brown blobs)."""
    for name in ROOT_BLOBS:
        o = bpy.data.objects.get(name)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    moved = 0
    for name in names:
        obj = bpy.data.objects.get(name)
        if not obj or obj.type != "MESH":
            continue
        me = obj.data
        if me.users > 1:
            obj.data = me = me.copy()
        mw, inv = obj.matrix_world, obj.matrix_world.inverted()
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        seen = set()
        hidden = obj.hide_get()
        obj.hide_set(True)          # never land on itself
        for v0 in bm.verts:
            if v0.index in seen:
                continue
            stack, part = [v0], []
            seen.add(v0.index)
            while stack:
                v = stack.pop()
                part.append(v)
                for e in v.link_edges:
                    w = e.other_vert(v)
                    if w.index not in seen:
                        seen.add(w.index)
                        stack.append(w)
            low = min(part, key=lambda v: (mw @ v.co).z)
            p = mw @ low.co
            ok, hit, *_ = scene.ray_cast(depsgraph, p + Vector((0, 0, 0.002)), Vector((0, 0, -1)), distance=2.0)
            if ok and p.z - hit.z > tol:
                drop = inv.to_3x3() @ Vector((0, 0, -(p.z - hit.z - 0.002)))
                for v in part:
                    v.co += drop
                moved += 1
        obj.hide_set(hidden)
        bm.to_mesh(me)
        bm.free()
    return moved
