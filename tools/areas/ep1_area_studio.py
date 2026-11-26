"""Builds Sora's floor of a Phnom Penh shophouse (Episode 1 prologue), 8 PM, 1932.

The top floor of a Sino-Khmer shophouse: long and narrow between masonry party walls.
- Front studio (south, 4.6 x 6 m): two tall French doors onto the street balcony,
  the drafting table under the east door, the writing desk with its drawer on the
  west wall, a plan chest and bookcase, a tea corner, and the period prints on the
  walls (real public-domain posters, postcards and photographs, 1906-1921).
- Airwell (3 m): open to the sky, the rain falling into a sunken basin with water
  jars and plants; covered walkways round it; the stairs down (the way out, behind
  a child gate), the wall telephone and the hurricane lamp on its hook.
- Back room (north, 4.6 x 4.8 m): the bed under its mosquito net, a wardrobe, the
  washstand and mirror, the family altar shelf.
Clean, swept and old: cement tiles, limewash over a painted dado, worn teak.

The writing desk, its drawer and the drafting table stand where the prologue's code
expects them (Blender (x, y, z) is runtime (-x, z, -y)).

Library models and materials: art-source/library/ (CC0, Poly Haven; `npm run
fetch-library`), decimated to a polygon budget each. Prints: tools/drawings/studio.mjs
(`npm run drawings -- ep1`), laid out by tools/areas/studio_prints.json. Run:
    blender -b --factory-startup -P tools/areas/ep1_area_studio.py
    blender -b art-source/blender/ep1/ep1_area_studio.blend -P tools/areas/bake_studio_lightmap.py
    npm run export -- ep1 && npm run assets -- ep1
Blender axes: X east, Y north, Z up; metres. Names follow the TDD, section 7.1.
"""

import json
import math
import os
import sys

import bpy
import mathutils
import mathutils.bvhtree
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from kit import *  # noqa: E402,F403  (shared materials and geometry)
from studio_bathroom import BATH_DOOR, BATH_Y1, build_bathroom, vintage_wall_switch  # noqa: E402

BLEND = os.path.join(ROOT, "art-source", "blender", "ep1", "ep1_area_studio.blend")
PRINTS = json.load(open(os.path.join(os.path.dirname(__file__), "studio_prints.json")))
BOOKS = json.load(open(os.path.join(os.path.dirname(__file__), "studio_books.json")))

W = 4.6                      # inside width between the party walls
PARTY = 0.3                  # party wall thickness
H = 3.4                      # ceiling height in the rooms
FRONT = 6.0                  # front studio depth (y 0..6)
P1 = (6.0, 6.12)             # timber partition between studio and airwell
AIR = (6.12, 9.12)           # airwell zone
P2 = (9.12, 9.27)            # masonry wall between airwell and back room
BACK = 14.0                  # back room's north wall (inside face)
FACADE = 0.3                 # street facade thickness (y -0.3..0)
DOORS = [(0.75, 1.65), (2.95, 3.85)]   # French doors onto the balcony
DOOR_TOP = 2.72
FAN_TOP = 3.18               # fanlight above each door
P1_DOOR = (0.15, 1.15)       # studio -> airwell walkway
P2_DOOR = (0.15, 1.05)       # walkway -> back room
WALK = 0.8                   # covered walkway width along the airwell's south side
COURT = (1.15, 3.35)         # open basin, x
STAIR = (3.45, 4.5, 7.0, 9.05)  # stair opening x0, x1, y0, y1 (going down northwards)
DADO = 1.05

rng = np.random.default_rng(1932)
area = None
m = {}
# The altar's offerings as they are made in back_room(), for scare_props().
ALTAR = {}


# =============================================================== helpers


def lib(model_id, location, rot_deg=0.0, name=None, collide=True, scale=1.0, budget=6000, **props):
    """A library model, decimated to about `budget` faces (Poly Haven scans arrive with
    up to 200k faces; at room scale 6k is plenty)."""
    parent = import_model(area, model_id, location, rot_deg, name=name, collide=collide, scale=scale, **props)
    return fit_budget(parent, budget)


PROPS = []   # every imported model, for shrink_prop_textures()


def fit_budget(parent, budget):
    PROPS.append(parent)
    meshes = [o for o in parent.children_recursive if o.type == "MESH"]
    # Library glass (lamp chimneys) arrives alpha-blended; Blender 5's exporter only keeps
    # that if the material renders blended, otherwise the chimney comes out black.
    for o in meshes:
        for slot in o.material_slots:
            mat = slot.material
            if mat and any(k in mat.name.lower() for k in ("glass", "flame")) and hasattr(mat, "surface_render_method"):
                mat.surface_render_method = "BLENDED"
    faces = sum(len(o.data.polygons) for o in meshes)
    if faces > budget:
        ratio = budget / faces
        for o in meshes:
            if o.data.users > 1:
                o.data = o.data.copy()
            mod = o.modifiers.new("budget", "DECIMATE")
            mod.ratio = max(ratio, 0.02)
            mod.use_collapse_triangulate = True
    return parent


def shrink_prop_textures():
    """Texture size to suit each model's size in the room: a lime or a spoon does not need
    the 1K maps a table has (each 1K normal map is about 1.3 MB in the game's download).
    A texture shared by several models keeps the size its largest user needs."""
    bpy.context.view_layer.update()
    need = {}
    for parent in PROPS:
        pts = [o.matrix_world @ mathutils.Vector(c) for o in parent.children_recursive if o.type == "MESH" for c in o.bound_box]
        if not pts:
            continue
        size = max(max(p[k] for p in pts) - min(p[k] for p in pts) for k in range(3))
        cap = 256 if size < 0.2 else 512 if size < 0.55 else 1024
        if parent.name.startswith("interact_"):
            cap = 1024   # picked up and seen close
        for o in parent.children_recursive:
            for slot in getattr(o, "material_slots", []):
                if not slot.material or not slot.material.node_tree:
                    continue
                for nd in slot.material.node_tree.nodes:
                    if nd.type == "TEX_IMAGE" and nd.image:
                        need[nd.image] = max(need.get(nd.image, 0), cap)
    shrunk = 0
    for img, cap in need.items():
        w, h = img.size
        if max(w, h) > cap:
            k = cap / max(w, h)
            img.scale(max(1, round(w * k)), max(1, round(h * k)))
            img.pack()
            shrunk += 1
    print(f"shrank {shrunk} prop textures")


def scan(key, location, rot_deg=0.0, name=None, collide=True, scale=1.0, budget=None):
    """A Sketchfab scan from art-source/library/scans (CC BY; downloads need an account,
    so they are kept in LFS rather than fetched). tools/areas/studio_scans.py has already
    stood each one on its base centre at the origin, at life size in metres, and reduced it.
    It is not decimated again here: a photo scan's fragmented texture layout tears apart
    when it is (the glazed jar came out like crumpled foil). Returns None when the scan is
    not there, so the build still runs without it."""
    path = os.path.join(LIB, "scans", f"{key}.glb")
    if not os.path.exists(path):
        print(f"scan {key} is not in art-source/library/scans; left out")
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    parent = empty(name or f"prop_{key}", area, location, (0, 0, math.radians(rot_deg)))
    parent.scale = (scale, scale, scale)
    for obj in new:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        area.objects.link(obj)
        if obj.parent is None:
            obj.parent = parent
    bpy.context.view_layer.update()
    if collide:
        pts = [o.matrix_world @ v.co for o in new if o.type == "MESH" for v in o.data.vertices]
        xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
        collider(name or key, area, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
    return fit_budget(parent, budget or 10**9)


def surface_z(x, y, z_from=H - 0.25):
    """Height of the first surface below (x, y, z_from), ignoring collision boxes: props
    are set down on whatever shelf board or table top the scanned furniture really has.
    Each mesh is cast against on its own. (A scene-wide cast that stepped past each
    collider it met went wrong wherever a collider's top lay flush with the furniture's:
    the collider won the tie, the ray carried on from inside the board and found its
    underside, and everything set on the hall table, the rice chest and the washstand sat
    2-3 cm down inside them. November 2026.)"""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    origin = mathutils.Vector((x, y, z_from))
    down = mathutils.Vector((0, 0, -1))
    best = None
    for obj in area.all_objects:
        if obj.type != "MESH" or obj.name.startswith("col_"):
            continue
        bb = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        if not (min(p.x for p in bb) <= x <= max(p.x for p in bb) and min(p.y for p in bb) <= y <= max(p.y for p in bb)
                and min(p.z for p in bb) <= z_from):
            continue
        inv = obj.matrix_world.inverted()
        hit, loc, _n, _i = obj.ray_cast(inv @ origin, (inv.to_3x3() @ down).normalized(), depsgraph=depsgraph)
        if hit:
            z = (obj.matrix_world @ loc).z
            if z <= z_from + 1e-6 and (best is None or z > best):
                best = z
    return best if best is not None else 0.0


def set_down(model_id, x, y, rot=0.0, z_from=H - 0.25, scale=1.0, budget=1500, name=None, lift=0.0):
    """A small library prop stood on the surface below (x, y, z_from)."""
    z = surface_z(x, y, z_from)
    return lib(model_id, (x, y, z + lift), rot, name=name, collide=False, scale=scale, budget=budget)


def plain_paint(name, colour, rough=0.75):
    return plain(name, colour, rough=rough)


def atlas_material(key):
    spec = PRINTS["atlases"][key]
    return image_material(f"M_studio_print_{key}", os.path.join(TEXTURES, f"{spec['file']}.png"), rough=0.92)


def print_sheet(name, key, item, centre, right, up, width, thickness=0.0012, tilt=0.0, mat=None):
    """A printed sheet (or card) on a wall: `right`/`up` are world directions across its
    face as seen by someone looking at it; its face shows `item`'s rect in atlas `key`.
    The height follows the rect's aspect. Returns the sheet."""
    spec = PRINTS["atlases"][key]
    S = spec["size"][0]
    x, y, w, h = spec["items"][item]["rect"]
    height = width * h / w
    r = np.array(right, float); r /= np.linalg.norm(r)
    u = np.array(up, float); u /= np.linalg.norm(u)
    if tilt:
        c, s = math.cos(tilt), math.sin(tilt)
        r, u = r * c + u * s, u * c - r * s
    n = np.cross(r, u)
    cx = np.array(centre, float)
    corners = []
    for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        p = cx + r * du * width / 2 + u * dv * height / 2
        corners.append(p)
    verts = [tuple(p) for p in corners] + [tuple(p - n * thickness) for p in corners]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    # Face: the rect; back and edges: a sliver of the rect's border (paper colour).
    u0, u1 = x / S, (x + w) / S
    v0, v1 = 1 - (y + h) / S, 1 - y / S
    edge = (u0 + 0.002, v1 - 0.002)
    uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)] + [edge] * 20
    return mesh_object(name, area, verts, faces, mat or m[f"print_{key}"], uvs=uvs)


def frame_print(name, key, item, centre, right, up, width, moulding=0.035, depth=0.025, mat=None):
    """A mounted print in a plain moulded frame (walls are axis-aligned, so the four
    mouldings are boxes)."""
    sheet = print_sheet(name, key, item, centre, right, up, width)
    spec = PRINTS["atlases"][key]
    _, _, w, h = spec["items"][item]["rect"]
    height = width * h / w
    r = np.array(right, float); r /= np.linalg.norm(r)
    u = np.array(up, float); u /= np.linalg.norm(u)
    n = np.cross(r, u)
    c = np.array(centre, float)
    hw, hh = width / 2, height / 2
    bars = {"bottom": ((-hw - moulding, -hh - moulding), (hw + moulding, -hh)), "top": ((-hw - moulding, hh), (hw + moulding, hh + moulding)),
            "left": ((-hw - moulding, -hh), (-hw, hh)), "right": ((hw, -hh), (hw + moulding, hh))}
    for k, ((a0, b0), (a1, b1)) in bars.items():
        pts = [c + r * a + u * b + n * d for a in (a0, a1) for b in (b0, b1) for d in (-0.002, depth)]
        lo, hi = np.min(pts, axis=0), np.max(pts, axis=0)
        box(f"{name}_frame_{k}", area, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], mat or m["frame"], edge=0.004)
    # A card mount bevel just inside the frame.
    return sheet


def pinned_poster(k, item, centre, right, width, tilt=0.0):
    """One of the user's portrait posters (atlas nineties_p) tacked flat to a wall with a
    brass pin through each corner. Slot meshes are named poster90_p_<k> (the game keeps
    them apart and shuffles their pictures)."""
    sheet = print_sheet(f"poster90_p_{k}", "nineties_p", item, centre, right, (0, 0, 1), width, tilt=tilt)
    _, _, w, h = PRINTS["atlases"]["nineties_p"]["items"][item]["rect"]
    height = width * h / w
    r = np.array(right, float); r /= np.linalg.norm(r)
    u = np.array((0.0, 0.0, 1.0))
    c_, s_ = math.cos(tilt), math.sin(tilt)
    r, u = r * c_ + u * s_, u * c_ - r * s_
    n = np.cross(r, u)
    for du in (-1, 1):
        for dv in (-1, 1):
            p = np.array(centre, float) + r * du * (width / 2 - 0.018) + u * dv * (height / 2 - 0.018) + n * 0.0005
            pin(f"poster90_p_{k}_pin_{du}_{dv}", tuple(p), tuple(n))
    return sheet


def framed_picture(k, item, centre, right, width):
    """One of the user's landscape pictures (atlas nineties_l) in a plain moulded frame;
    the slot's sheet is poster90_l_<k>. Returns the height of the frame's top."""
    frame_print(f"poster90_l_{k}", "nineties_l", item, centre, right, (0, 0, 1), width)
    _, _, w, h = PRINTS["atlases"]["nineties_l"]["items"][item]["rect"]
    return centre[2] + width * h / w / 2 + 0.035


def attach(child, parent):
    """Parents `child` to `parent` keeping its world placement."""
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    return child


def pin(name, at, normal, mat=None):
    """A brass drawing pin pushed into plaster or board at `at`, its head facing `normal`."""
    nx, ny, nz = normal
    head = cylinder(name, area, 0, 0, 0, 0.0025, 0.0055, mat or m["brass"], verts=10)
    head.location = (at[0] + nx * 0.0013, at[1] + ny * 0.0013, at[2] + nz * 0.0013)
    head.rotation_euler = (math.atan2(-ny, nz) if abs(nx) < 0.5 else 0, math.pi / 2 if abs(nx) > 0.5 else 0, 0)
    return head


def outline_slab(name, outline, z0, z1, mat, edge=0.0):
    """A slab extruded vertically from a 2D outline (x, y) points, counter-clockwise."""
    n = len(outline)
    verts = [(x, y, z0) for x, y in outline] + [(x, y, z1) for x, y in outline]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    obj = mesh_object(name, area, verts, faces, mat)
    if edge:
        bevel(obj, edge)
    return obj


def boards(name, x0, x1, y0, y1, z0, z1, mat, width=0.12, axis="x", gap=0.004, edge=0.002):
    """Tongue-and-groove boards: a run of narrow boxes with a hairline between them."""
    out = []
    if axis == "x":
        n = max(1, round((x1 - x0) / width))
        w = (x1 - x0) / n
        for i in range(n):
            out.append(box(f"{name}_{i}", area, x0 + i * w + gap / 2, x0 + (i + 1) * w - gap / 2, y0, y1, z0, z1, mat, edge=edge))
    elif axis == "y":
        n = max(1, round((y1 - y0) / width))
        w = (y1 - y0) / n
        for i in range(n):
            out.append(box(f"{name}_{i}", area, x0, x1, y0 + i * w + gap / 2, y0 + (i + 1) * w - gap / 2, z0, z1, mat, edge=edge))
    else:
        n = max(1, round((z1 - z0) / width))
        w = (z1 - z0) / n
        for i in range(n):
            out.append(box(f"{name}_{i}", area, x0, x1, y0, y1, z0 + i * w + gap / 2, z0 + (i + 1) * w - gap / 2, mat, edge=edge))
    return out


def turned(name, profile, x, y, z, mat, segments=16):
    return lathe(name, area, profile, x, y, z, mat, segments=segments)


BALUSTER = [(0.0, 0.0), (0.028, 0.0), (0.028, 0.06), (0.018, 0.08), (0.024, 0.16), (0.014, 0.3), (0.02, 0.42),
            (0.026, 0.5), (0.016, 0.58), (0.016, 0.66), (0.024, 0.68), (0.024, 0.74), (0.0, 0.74)]


# =============================================================== materials


def cement_tile_textures():
    """Encaustic cement tiles of the kind laid in Phnom Penh shophouses in the 1920s-30s:
    20 cm tiles with a corner-ring and four-petal motif in ochre, oxblood and charcoal on
    cream; worn by forty years of bare feet, swept clean. 4 x 4 tiles per map (0.8 m)."""
    N, T = 2048, 4
    px = N // T
    yy, xx = np.mgrid[:N, :N].astype(np.float32)
    u = (xx % px) / px
    v = (yy % px) / px
    tx, ty = (xx // px).astype(int), (yy // px).astype(int)
    cream = np.array((0.80, 0.74, 0.60)); ochre = np.array((0.66, 0.46, 0.20))
    oxblood = np.array((0.42, 0.15, 0.11)); charcoal = np.array((0.13, 0.12, 0.11)); sage = np.array((0.42, 0.46, 0.38))
    col = np.empty((N, N, 3), np.float32); col[:] = cream
    def paint(mask, c):
        col[mask] = c
    # Corner rings: quarter circles that join into full rings across four tiles.
    for cu in (0, 1):
        for cv in (0, 1):
            d = np.hypot(u - cu, v - cv)
            paint((d > 0.255) & (d < 0.315), ochre)
            paint((d > 0.315) & (d < 0.33), charcoal)
            paint(d < 0.12, sage)
    # Diamond line and the central four-petal flower.
    dd = np.abs(u - 0.5) + np.abs(v - 0.5)
    paint((dd > 0.395) & (dd < 0.415), charcoal)
    a = np.arctan2(v - 0.5, u - 0.5)
    rr = np.hypot(u - 0.5, v - 0.5)
    petal = rr < 0.2 * (0.35 + 0.65 * np.abs(np.cos(2 * a)) ** 1.5)
    paint(petal, oxblood)
    paint((rr < 0.2 * (0.35 + 0.65 * np.abs(np.cos(2 * a)) ** 1.5) - 0.025) & petal, np.array((0.52, 0.22, 0.15)))
    paint(rr < 0.045, charcoal)
    # Edge line round each tile (makes the grid of the floor read from standing height).
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    paint((edge > 0.012) & (edge < 0.022), sage * 0.9)
    # Per-tile shade (each tile pressed separately), wear and cement speckle.
    tile_shade = rng.uniform(0.94, 1.05, (T, T))
    col *= tile_shade[ty, tx][..., None]
    def smooth_noise(cell, seed):
        r = np.random.default_rng(seed)
        g = r.random((N // cell + 2, N // cell + 2)).astype(np.float32)
        gx, gy = xx / cell, yy / cell
        ix, iy = gx.astype(int), gy.astype(int)
        fx, fy = gx - ix, gy - iy
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a0 = g[iy, ix] * (1 - fx) + g[iy, ix + 1] * fx
        a1 = g[iy + 1, ix] * (1 - fx) + g[iy + 1, ix + 1] * fx
        return a0 * (1 - fy) + a1 * fy
    wear = 0.6 * smooth_noise(256, 3) + 0.4 * smooth_noise(64, 4)
    col = col * (0.9 + 0.12 * wear[..., None])
    # Worn paths: the pigment layer fades towards grey cement where feet go.
    fadew = np.clip((wear - 0.55) * 2.5, 0, 1)[..., None] * 0.35
    col = col * (1 - fadew) + np.array((0.62, 0.60, 0.55)) * fadew
    speck = np.random.default_rng(5).random((N, N)).astype(np.float32)
    col *= (1 + (speck[..., None] - 0.5) * 0.08)
    col[(speck > 0.9985)] *= 0.55
    grout = edge < 0.004
    col[grout] = np.array((0.28, 0.27, 0.25))
    col = np.clip(col, 0, 1)
    # Normal: grout recessed, each tile slightly out of level, fine pitting.
    height = np.where(grout, -1.0, 0.0) + (tile_shade[ty, tx] - 1) * 4 * u + (speck - 0.5) * 0.15
    gy_, gx_ = np.gradient(height)
    nrm = np.stack([-gx_ * 0.6, gy_ * 0.6, np.ones_like(gx_)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    nrm = nrm * 0.5 + 0.5
    rough = np.clip(0.5 - 0.12 * fadew[..., 0] / 0.35 + 0.1 * (wear - 0.5) + np.where(grout, 0.4, 0), 0.25, 0.95)
    orm = np.stack([np.where(grout, 0.65, 1.0), rough, np.zeros_like(rough)], -1)
    paths = {}
    for suffix, arr, non_color in (("BC", col, False), ("N", nrm, True), ("ORM", orm, True)):
        img = bpy.data.images.new(f"T_studio_cement_tiles_{suffix}", N, N, alpha=False)
        rgba = np.ones((N, N, 4), np.float32)
        rgba[..., :3] = arr[::-1]
        if non_color:
            img.colorspace_settings.name = "Non-Color"
        img.pixels.foreach_set(rgba.ravel())
        path = os.path.join(TEXTURES, f"T_studio_cement_tiles_{suffix}.png")
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        paths[suffix] = path
    return paths


def textured_material(name, paths, tile, tint=None):
    """Principled material from BC/N/ORM image paths, like kit.library_material."""
    mat = bpy.data.materials.new(name)
    mat.use_backface_culling = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bc = nodes.new("ShaderNodeTexImage"); bc.image = image(paths["BC"], False)
    if tint:
        mix = nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0; mix.inputs[7].default_value = (*tint, 1)
        links.new(bc.outputs["Color"], mix.inputs[6]); links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    else:
        links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    nrm = nodes.new("ShaderNodeTexImage"); nrm.image = image(paths["N"], True)
    nmap = nodes.new("ShaderNodeNormalMap")
    links.new(nrm.outputs["Color"], nmap.inputs["Color"]); links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    orm = nodes.new("ShaderNodeTexImage"); orm.image = image(paths["ORM"], True)
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(orm.outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    out = nodes.new("ShaderNodeGroup"); out.node_tree = gltf_output_group()
    links.new(split.outputs["Red"], out.inputs["Occlusion"])
    mat["tile"] = tile
    return mat


def materials():
    tiles = cement_tile_textures()
    lm = library_material
    m.update({
        "floor": textured_material("M_studio_cement_tiles", tiles, 0.8),
        "floor_border": textured_material("M_studio_cement_border", tiles, 0.8, tint=(0.36, 0.3, 0.26)),
        "limewash": lm("painted_plaster_wall", "M_studio_limewash", tint=(0.96, 0.86, 0.66), tile=2.0),
        "dado": lm("painted_plaster_wall", "M_studio_dado_paint", colour=(0.36, 0.40, 0.33), tile=2.0),
        "dado_line": plain("M_studio_dado_line", (0.22, 0.09, 0.06), rough=0.6),
        "outside": lm("white_plaster_rough_01", "M_studio_outside_plaster", tint=(0.85, 0.78, 0.62), tile=2.5),
        "ceiling": lm("dark_wooden_planks", "M_studio_ceiling", tile=2.0),
        "joist": lm("dark_wood", "M_studio_joist"),
        "wood": lm("dark_wood", "M_dark_wood"),
        "teak": lm("teak_veneer", "M_teak_veneer"),
        "rosewood": lm("rosewood_veneer1", "M_studio_rosewood", tile=1.0),
        "worn": lm("wood_table_worn", "M_wood_worn"),
        "planks": lm("weathered_planks", "M_studio_old_planks", tint=(0.78, 0.7, 0.6), tile=1.2),
        "bark": lm("bark_brown_02", "M_studio_firewood_bark", tile=0.4),
        "boards": lm("stair_planks", "M_studio_partition_boards", tint=(0.8, 0.7, 0.58), tile=1.5),
        "stair": lm("stair_planks", "M_studio_stair_treads", tile=1.5),
        "shutter": lm("wood_shutter", "M_studio_shutter", tint=(0.55, 0.62, 0.5), tile=1.0),
        "cement": lm("concrete_floor_worn_001", "M_studio_cement", tint=(0.8, 0.76, 0.7), tile=2.0),
        "wet_cement": lm("concrete_floor_worn_001", "M_studio_wet_cement", tint=(0.45, 0.43, 0.4), tile=2.0),
        "roof": lm("clay_roof_tiles_02", "M_studio_roof_tiles"),
        "rust": lm("rusty_metal", "M_studio_rusted_iron", tint=(0.5, 0.45, 0.42), tile=1.0),
        "linen": lm("rough_linen", "M_linen", colour=(0.78, 0.72, 0.6)),
        "krama": lm("fabric_pattern_07", "M_krama", tile=0.12),
        "rug": lm("quatrefoil_jacquard_fabric", "M_rug", tint=(0.72, 0.55, 0.45)),
        "brick": lm("red_brick", "M_studio_old_brick", tint=(0.8, 0.7, 0.62), tile=1.2),
        "sampot": lm("fabric_pattern_07", "M_studio_sampot", tint=(0.35, 0.42, 0.75), tile=0.22),
        "bamboo": plain("M_studio_bamboo", (0.55, 0.45, 0.25), rough=0.55),
        "enamel": plain("M_studio_enamel", (0.78, 0.8, 0.76), rough=0.25),
        "incense": plain("M_studio_incense", (0.32, 0.16, 0.08), rough=0.92),
        "incense_red": plain("M_studio_incense_red", (0.48, 0.07, 0.06), rough=0.78),
        "incense_ash": plain("M_studio_incense_ash", (0.58, 0.56, 0.52), rough=0.98),
        "incense_ember": plain("M_studio_incense_ember", (1.0, 0.28, 0.04), rough=0.6, emission=(1.0, 0.32, 0.05), strength=8.5),
        "mat": lm("bamboo_wall", "M_studio_reed_mat", tint=(0.8, 0.7, 0.5), tile=0.5),
        "mesh_cover": plain("M_studio_wire_mesh", (0.05, 0.05, 0.045), rough=0.55, metal=0.5, alpha=0.32),
        "enamel_green": plain("M_studio_green_enamel", (0.12, 0.25, 0.18), rough=0.3),
        "brass": plain("M_brass", (0.62, 0.45, 0.2), rough=0.35, metal=1.0),
        "nickel": plain("M_studio_nickel", (0.72, 0.7, 0.66), rough=0.28, metal=1.0),
        "iron": plain("M_black_iron", (0.03, 0.03, 0.03), rough=0.5, metal=0.8),
        "japan": plain("M_studio_japanned_iron", (0.025, 0.022, 0.02), rough=0.25, metal=0.3),
        "ebonite": plain("M_studio_ebonite", (0.035, 0.033, 0.03), rough=0.3),
        "porcelain": plain("M_studio_porcelain", (0.86, 0.84, 0.78), rough=0.2),
        "paper": plain("M_paper", (0.86, 0.82, 0.72), rough=0.95),
        "newsprint": plain("M_newsprint", (0.62, 0.6, 0.55), rough=0.95),
        "leather": plain("M_leather", (0.24, 0.12, 0.06), rough=0.55),
        "satchel_leather": lm("brown_leather", "M_studio_satchel_leather", tint=(0.85, 0.72, 0.6), tile=0.5),
        "book": plain("M_book_cover", (0.08, 0.06, 0.05), rough=0.6),
        "frame": plain("M_studio_frame", (0.09, 0.055, 0.035), rough=0.45),
        "glass": plain("M_window_glass", (0.015, 0.017, 0.02), rough=0.06, alpha=0.86),
        "green_glass": plain("M_lamp_green_glass", (0.03, 0.26, 0.11), rough=0.12, emission=(0.1, 0.55, 0.22), strength=0.35),
        "opal": plain("M_lamp_opal_glass", (0.9, 0.88, 0.8), rough=0.3, emission=(1, 0.85, 0.6), strength=0.8),
        "bulb": plain("M_lamp_bulb", (1, 0.9, 0.7), rough=0.3, emission=(1, 0.85, 0.6), strength=6.0),
        "ink": plain("M_ink", (0.02, 0.02, 0.025), rough=0.1),
        "candle": plain("M_candle_wax", (0.9, 0.86, 0.75), rough=0.5),
        "string": plain("M_string", (0.55, 0.5, 0.42), rough=0.9),
        "cord": plain("M_studio_braided_cord", (0.12, 0.09, 0.06), rough=0.85),
        "water": plain("M_studio_water", (0.02, 0.025, 0.03), rough=0.04),
        "glaze": plain("M_studio_jar_glaze", (0.2, 0.13, 0.06), rough=0.18),
        "terracotta": lm("clay_plaster", "M_studio_terracotta", tint=(0.62, 0.36, 0.24), tile=0.6),
        "neighbour": plain("M_neighbour_window", (0.1, 0.07, 0.04), emission=(1, 0.62, 0.3), strength=0.6),
        "dark": plain("M_studio_dark_room", (0.01, 0.01, 0.01), rough=1.0),
        "net": plain("M_mosquito_net", (0.9, 0.9, 0.88), rough=0.9, alpha=0.22),
        "mirror": plain("M_studio_mirror", (0.55, 0.55, 0.5), rough=0.08, metal=1.0),
        "flame": plain("M_studio_oil_flame", (1, 0.6, 0.25), emission=(1, 0.55, 0.2), strength=8.0),
    })
    m["illustration"] = drawing("M_studio_illustration", "T_studio_illustration_BC")
    m["print_posters"] = atlas_material("posters")
    m["print_cards"] = atlas_material("cards")
    m["print_colour"] = atlas_material("colour")
    # The user's posters (90s Posters/, November 2026): portrait sheets and framed
    # landscape pictures, shuffled between their slots each time the room loads
    # (src/episodes/ep1/prologue/posterShuffle.ts).
    m["print_nineties_p"] = atlas_material("nineties_p")
    m["print_nineties_l"] = atlas_material("nineties_l")
    # Real vintage book cover & spine atlases (tools/drawings/books.mjs, tools/areas/studio_books.json),
    # paired with Poly Haven linen normal & roughness micro-weave so every book catches lamplight realistically!
    for bk_key, bk_spec in BOOKS["atlases"].items():
        mat = image_material(f"M_studio_book_{bk_key}", os.path.join(TEXTURES, f"{bk_spec['file']}.png"), rough=0.72)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = nodes["Principled BSDF"]
        linen_base = os.path.join(LIB, "materials", "rough_linen", "rough_linen")
        if os.path.exists(f"{linen_base}_N.jpg"):
            tc = nodes.new("ShaderNodeTexCoord")
            mp = nodes.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (18.0, 18.0, 18.0)
            links.new(tc.outputs["UV"], mp.inputs["Vector"])
            nrm = nodes.new("ShaderNodeTexImage"); nrm.image = image(f"{linen_base}_N.jpg", True)
            links.new(mp.outputs["Vector"], nrm.inputs["Vector"])
            nmap = nodes.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = 0.25
            links.new(nrm.outputs["Color"], nmap.inputs["Color"])
            links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
        mat["tile"] = 0.0
        m[f"book_atlas_{bk_key}"] = mat
    m["cobweb"] = cobweb_material()
    m["cracks"] = crack_material()


# =============================================================== shell


def wall(name, x0, x1, y0, y1, z0, z1, mat, solid=True):
    obj = box(name, area, x0, x1, y0, y1, z0, z1, mat)
    if solid:
        collider(name, area, x0, x1, y0, y1, z0, z1)
    return obj


def room_walls(name, x0, x1, y0, y1, faces, gaps=()):
    """Lining for one room: a painted dado to 1.05 m with a red-brown line, limewash
    above, a cement skirting. `faces` lists which inside faces get lining
    ('w', 'e', 's', 'n'); `gaps` are (face, a, b, top) openings (doorways)."""
    t = 0.012
    spans = {"w": ((x0, x0 + t), (y0, y1), "y"), "e": ((x1 - t, x1), (y0, y1), "y"),
             "s": ((x0, x1), (y0, y0 + t), "x"), "n": ((x0, x1), (y1 - t, y1), "x")}
    for f in faces:
        (ax0, ax1), (ay0, ay1), along = spans[f]
        cuts = sorted((a, b, top) for g, a, b, top in gaps if g == f)
        lo = ay0 if along == "y" else ax0
        hi = ay1 if along == "y" else ax1
        segs, at = [], lo
        for a, b, top in cuts:
            if a > at:
                segs.append((at, a, None))
            segs.append((a, b, top))
            at = b
        if at < hi:
            segs.append((at, hi, None))
        for k, (a, b, top) in enumerate(segs):
            def span(z0, z1, mat, nm, inset=0.0):
                if along == "y":
                    xa, xb = (ax0 + (inset if f == "e" else 0), ax1 - (inset if f == "w" else 0)) if inset else (ax0, ax1)
                    if f == "w":
                        xa, xb = ax0, ax1 + inset
                    if f == "e":
                        xa, xb = ax0 - inset, ax1
                    return box(f"{name}_{nm}_{f}{k}", area, xa, xb, a, b, z0, z1, mat)
                ya, yb = ay0, ay1
                if f == "s":
                    ya, yb = ay0, ay1 + inset
                if f == "n":
                    ya, yb = ay0 - inset, ay1
                return box(f"{name}_{nm}_{f}{k}", area, a, b, ya, yb, z0, z1, mat)
            if top is None:
                span(0, 0.14, m["cement"], "skirting", 0.012)
                span(0.14, DADO, m["dado"], "dado")
                span(DADO, DADO + 0.025, m["dado_line"], "dado_line", 0.004)
                span(DADO + 0.025, H, m["limewash"], "limewash")
            else:
                span(top, H, m["limewash"], "head")


def shell():
    # Party walls (brick, plastered): west extends past the rear bathroom (BATH_Y1); east stops at BACK.
    wall("party_wall_west", -PARTY, 0, -FACADE, BATH_Y1 + 0.3, -0.3, H + 0.05, m["limewash"])
    wall("party_wall_east", W, W + PARTY, -FACADE, BACK + 0.3, -0.3, H + 0.05, m["limewash"])
    # Floors: tiles with a plain border band in each room; cement in the walkways.
    collider("floor", area, -PARTY, W + PARTY, -1.3, BACK + 0.15, -0.3, 0, surface="stone")
    for name, (y0, y1) in (("front", (0, FRONT)), ("back", (P2[1], BACK))):
        box(f"floor_{name}_border", area, 0, W, y0, y1, -0.05, -0.001, m["floor_border"])
        box(f"floor_{name}_tiles", area, 0.3, W - 0.3, y0 + 0.3, y1 - 0.3, -0.05, 0.0, m["floor"])
    # The hall: tiles round the stair opening (x 3.45-4.5, y 7.0-9.05).
    box("floor_hall_border_w", area, 0, STAIR[0], P1[0], AIR[1], -0.05, -0.001, m["floor_border"])
    box("floor_hall_border_landing", area, STAIR[0], W, P1[0], STAIR[2], -0.05, -0.001, m["floor_border"])
    box("floor_hall_border_e", area, STAIR[1], W, STAIR[2], AIR[1], -0.05, -0.001, m["floor_border"])
    box("floor_hall_tiles", area, 0.3, STAIR[0] - 0.3, P1[1] + 0.3, AIR[1] - 0.3, -0.05, 0.0, m["floor"])
    box("floor_threshold_p2", area, P2_DOOR[0], P2_DOOR[1], P2[0], P2[1], -0.05, 0.01, m["cement"], edge=0.004)

    # Ceilings: planks on exposed joists in both rooms.
    for name, (y0, y1) in (("front", (0, P1[0])), ("hall", (P1[1], P2[0])), ("back", (P2[1], BACK))):
        box(f"ceiling_{name}", area, 0, W, y0, y1, H, H + 0.04, m["ceiling"])
        n = int((y1 - y0) / 0.55)
        for i in range(1, n + 1):
            y = y0 + (y1 - y0) * i / (n + 1)
            box(f"ceiling_{name}_joist_{i}", area, 0, W, y - 0.045, y + 0.045, H - 0.17, H, m["joist"], edge=0.006)

    # Street facade (south) with the two French doors and their fanlights.
    xs = [0] + [v for d in DOORS for v in d] + [W]
    for k in range(0, len(xs), 2):
        a, b = xs[k], xs[k + 1]
        wall(f"facade_pier_{k}", a, b, -FACADE, 0, 0, H, m["limewash"])
        box(f"facade_pier_{k}_outside", area, a, b, -FACADE - 0.01, -FACADE, -0.3, H + 0.3, m["outside"])
    for k, (a, b) in enumerate(DOORS):
        wall(f"facade_head_{k}", a, b, -FACADE, 0, FAN_TOP + 0.06, H, m["limewash"], solid=False)
        box(f"facade_head_{k}_outside", area, a, b, -FACADE - 0.01, -FACADE, FAN_TOP + 0.06, H + 0.3, m["outside"])
        collider(f"french_door_{k}", area, a, b, -FACADE, -0.02, 0, FAN_TOP)
        french_door(k, a, b)
    # Inside linings of the front room (dado etc.), with gaps for the doors.
    room_walls("front", 0, W, 0, P1[0], "wes",
               gaps=[("s", a - 0.05, b + 0.05, FAN_TOP + 0.06) for a, b in DOORS])
    # Door reveals and architraves round each opening.
    for k, (a, b) in enumerate(DOORS):
        for s, (u0, u1) in (("w", (a - 0.09, a)), ("e", (b, b + 0.09))):
            box(f"door_architrave_{k}_{s}", area, u0, u1, -0.004, 0.018, 0, FAN_TOP + 0.09, m["wood"], edge=0.004)
        box(f"door_architrave_{k}_top", area, a - 0.09, b + 0.09, -0.004, 0.022, FAN_TOP + 0.06, FAN_TOP + 0.16, m["wood"], edge=0.005)

    balcony_and_street()
    partition_p1()
    hall()
    wall_p2()
    back_room_shell()


def french_door(k, a, b):
    """A pair of glazed casement doors (closed: it is raining), panelled below, six panes
    each above, and a fanlight with radiating glazing bars over the transom."""
    y0, y1 = -0.16, -0.11
    wood = m["teak"]
    box(f"french_door_{k}_frame_w", area, a, a + 0.06, y0 - 0.01, y1 + 0.01, 0, FAN_TOP, wood, edge=0.004)
    box(f"french_door_{k}_frame_e", area, b - 0.06, b, y0 - 0.01, y1 + 0.01, 0, FAN_TOP, wood, edge=0.004)
    box(f"french_door_{k}_transom", area, a, b, y0 - 0.01, y1 + 0.01, DOOR_TOP, DOOR_TOP + 0.07, wood, edge=0.004)
    box(f"french_door_{k}_sill", area, a - 0.03, b + 0.03, y0 - 0.06, y1 + 0.03, 0, 0.035, m["cement"], edge=0.006)
    leaf_w = (b - a - 0.12) / 2
    panes = []
    for s in range(2):
        lx0 = a + 0.06 + s * leaf_w
        lx1 = lx0 + leaf_w
        # West balcony door's east leaf (k==0, s==1) is hinged to unlatch and swing inward!
        dynamic_leaf = (k == 0 and s == 1)
        pivot = None
        if dynamic_leaf:
            pivot = empty("haunt_balcony_door", area, (lx1, y1, 0.035), (0, 0, 0), action="use")
            bpy.context.view_layer.update()
        leaf_objs = []
        for nm, (u0, u1, z0, z1) in {"stile_a": (lx0, lx0 + 0.055, 0.035, DOOR_TOP), "stile_b": (lx1 - 0.055, lx1, 0.035, DOOR_TOP),
                                     "bottom": (lx0, lx1, 0.035, 0.2), "lock": (lx0, lx1, 0.82, 0.92), "top": (lx0, lx1, DOOR_TOP - 0.06, DOOR_TOP)}.items():
            leaf_objs.append(box(f"french_door_{k}_{s}_{nm}", area, u0, u1, y0, y1, z0, z1, wood, edge=0.004))
        # Raised lower panel.
        leaf_objs.append(box(f"french_door_{k}_{s}_panel", area, lx0 + 0.055, lx1 - 0.055, y0 + 0.012, y1 - 0.012, 0.2, 0.82, wood))
        leaf_objs.append(box(f"french_door_{k}_{s}_panel_raise", area, lx0 + 0.085, lx1 - 0.085, y0 + 0.006, y1 - 0.006, 0.24, 0.78, wood, edge=0.012))
        # Glazing bars: two columns, three rows.
        gx0, gx1, gz0, gz1 = lx0 + 0.055, lx1 - 0.055, 0.92, DOOR_TOP - 0.06
        leaf_objs.append(box(f"french_door_{k}_{s}_bar_v", area, (gx0 + gx1) / 2 - 0.012, (gx0 + gx1) / 2 + 0.012, y0 + 0.01, y1 - 0.01, gz0, gz1, wood))
        for j in (1, 2):
            z = gz0 + (gz1 - gz0) * j / 3
            leaf_objs.append(box(f"french_door_{k}_{s}_bar_h{j}", area, gx0, gx1, y0 + 0.01, y1 - 0.01, z - 0.012, z + 0.012, wood))
        # Three brass butt hinges on each jamb edge
        hx = lx0 if s == 0 else lx1
        for hi, hz in enumerate((0.28, 1.35, DOOR_TOP - 0.24)):
            leaf_objs.append(cylinder(f"french_door_{k}_{s}_hinge_{hi}", area, hx, y1 + 0.004, hz - 0.038, hz + 0.038, 0.006, m["brass"], verts=8))
        # Espagnolette rod, guide brackets & sculpted French curved brass lever handle on the meeting stile.
        if (k == 1 and s == 0) or (k == 0 and s == 1):
            rx = (lx1 - 0.028) if s == 0 else (lx0 + 0.028)
            leaf_objs.append(cylinder(f"french_door_{k}_espagnolette", area, rx, y1 + 0.008, 0.05, DOOR_TOP - 0.02, 0.0055, m["brass"], verts=8))
            for gz_ in (0.18, 1.07, 1.92, DOOR_TOP - 0.14):
                leaf_objs.append(box(f"french_door_{k}_guide_{gz_:.2f}", area, rx - 0.012, rx + 0.012, y1, y1 + 0.016, gz_ - 0.012, gz_ + 0.012, m["brass"], edge=0.002))
            leaf_objs.append(box(f"french_door_{k}_lockcase", area, rx - 0.018, rx + 0.018, y1, y1 + 0.018, 1.00, 1.14, m["brass"], edge=0.003))
            lever_dir = -1 if s == 0 else 1
            lever_pts = [(rx, y1 + 0.018, 1.07), (rx, y1 + 0.044, 1.07), (rx + lever_dir * 0.025, y1 + 0.048, 1.055), (rx + lever_dir * 0.058, y1 + 0.042, 1.005)]
            leaf_objs.append(tube(f"french_door_{k}_handle", area, smooth_path(lever_pts, 4), 0.0065, m["brass"], sides=8))
        if dynamic_leaf:
            yg = (y0 + y1) / 2
            leaf_objs.append(mesh_object("balcony_door_glass", area, [(gx0, yg, gz0), (gx1, yg, gz0), (gx1, yg, gz1), (gx0, yg, gz1)], [(0, 1, 2, 3)], m["glass"]))
            for obj_ in leaf_objs:
                attach(obj_, pivot)
        else:
            panes.append((gx0, gx1, gz0, gz1))
    # One glass sheet per door (the rain on the glass is fitted to it at runtime).
    verts, faces = [], []
    for gx0, gx1, gz0, gz1 in panes:
        i = len(verts)
        yg = (y0 + y1) / 2
        verts += [(gx0, yg, gz0), (gx1, yg, gz0), (gx1, yg, gz1), (gx0, yg, gz1)]
        faces.append((i, i + 1, i + 2, i + 3))
    mesh_object("window_glass" if k == 1 else "window_glass_west", area, verts, faces, m["glass"])
    # Transom light over the doors: one rectangular pane with sunburst glazing bars.
    fz0, fz1 = DOOR_TOP + 0.07, FAN_TOP
    box(f"fanlight_{k}_head", area, a, b, y0 - 0.01, y1 + 0.01, FAN_TOP, FAN_TOP + 0.06, wood, edge=0.004)
    mesh_object(f"fanlight_glass_{k}", area, [(a + 0.06, -0.135, fz0), (b - 0.06, -0.135, fz0), (b - 0.06, -0.135, fz1), (a + 0.06, -0.135, fz1)], [(0, 1, 2, 3)], m["glass"])
    cx, r = (a + b) / 2, min((b - a) / 2 - 0.06, fz1 - fz0 - 0.01)
    tube(f"fanlight_{k}_arch", area, [(cx + math.cos(t) * r, -0.135, fz0 + math.sin(t) * r) for t in np.linspace(0, math.pi, 17)], 0.012, wood, sides=6)
    for t in np.linspace(0.0, math.pi, 7):
        far = min((b - a) / 2 - 0.06, (fz1 - fz0) / max(math.sin(t), 1e-3)) if 0.05 < t < math.pi - 0.05 else (b - a) / 2 - 0.06
        tube(f"fanlight_{k}_ray_{t:.2f}", area, [(cx, -0.135, fz0), (cx + math.cos(t) * far, -0.135, fz0 + math.sin(t) * far)], 0.008, wood, sides=5)
    # Louvred shutters folded back against the outside wall.
    for side, (s0, s1) in {"w": (a - 0.5, a - 0.04), "e": (b + 0.04, b + 0.5)}.items():
        if s0 < -0.1 or s1 > W + 0.1:
            continue
        box(f"shutter_{k}_{side}_frame_l", area, s0, s0 + 0.045, -FACADE - 0.07, -FACADE - 0.03, 0.04, DOOR_TOP, m["shutter"], edge=0.004)
        box(f"shutter_{k}_{side}_frame_r", area, s1 - 0.045, s1, -FACADE - 0.07, -FACADE - 0.03, 0.04, DOOR_TOP, m["shutter"], edge=0.004)
        for j in range(26):
            z = 0.1 + j * (DOOR_TOP - 0.2) / 26
            box(f"shutter_{k}_{side}_slat_{j}", area, s0 + 0.045, s1 - 0.045, -FACADE - 0.075, -FACADE - 0.035, z, z + 0.05, m["shutter"], tilt=(0.55, 0, 0))


def balcony_and_street():
    # The balcony: a cement slab on iron brackets with a cast-iron railing.
    box("balcony_slab", area, -0.1, W + 0.1, -1.25, -FACADE, -0.12, -0.02, m["cement"], edge=0.01)
    collider("balcony_edge", area, -0.1, W + 0.1, -1.25, -1.15, 0, 1.0)
    collider("balcony_slab", area, -0.1, W + 0.1, -1.25, -FACADE, -0.3, -0.02, surface="stone")
    box("balcony_rail_top", area, -0.05, W + 0.05, -1.2, -1.15, 0.95, 0.99, m["rust"], edge=0.008)
    box("balcony_rail_bottom", area, -0.05, W + 0.05, -1.2, -1.16, 0.06, 0.09, m["rust"])
    for i in range(int(W / 0.11) + 1):
        x = 0.02 + i * 0.11
        cylinder(f"balcony_baluster_{i}", area, x, -1.18, 0.09, 0.95, 0.008, m["rust"], verts=6)
        if i % 4 == 2:
            for dz in (0.35, 0.65):
                tube(f"balcony_scroll_{i}_{dz}", area, [(x + 0.055 * math.sin(t), -1.18, dz + 0.1 * (1 - math.cos(t)) * 0.5) for t in np.linspace(0, math.tau, 13)], 0.005, m["rust"], sides=5)
    for x in (0.2, W / 2, W - 0.2):
        box(f"balcony_bracket_{x:.1f}", area, x - 0.03, x + 0.03, -1.15, -FACADE, -0.45, -0.12, m["rust"], tilt=(0, 0, 0))
    # The eave of the roof over the balcony (tiles above, rafters beneath).
    box("street_eave_tiles", area, -0.3, W + 0.3, -1.45, -FACADE, H + 0.35, H + 0.42, m["roof"], tilt=(-0.18, 0, 0))
    for i in range(9):
        x = i * W / 8
        box(f"street_eave_rafter_{i}", area, x - 0.03, x + 0.03, -1.45, -FACADE, H + 0.22, H + 0.32, m["wood"], tilt=(-0.18, 0, 0))
    # The shophouse opposite, eight metres across the street: three floors of shutters,
    # one window lit, a balcony in the dark.
    box("facade_opposite", area, -6, 11, -9.6, -9.4, -9, 7, m["outside"])
    for fl, z in enumerate((-3.8, -0.3, 3.0)):
        for k, x in enumerate((-3.2, -1.1, 1.2, 3.4, 5.6, 7.8)):
            lit = (fl, k) == (1, 2)
            box(f"opposite_window_{fl}_{k}", area, x, x + 0.9, -9.39, -9.38, z, z + 2.3, m["neighbour"] if lit else m["dark"])
            box(f"opposite_shutter_{fl}_{k}", area, x - 0.04, x + 0.94, -9.37, -9.33, z - 0.04, z + 2.34, m["shutter"]) if not lit else None
        box(f"opposite_balcony_{fl}", area, -6, 11, -9.4, -8.6, z - 0.15, z - 0.05, m["cement"])
    empty("marker_lightning", area, (2.6, -4.0, H + 0.4))


def partition_p1():
    """Timber partition between the studio and the airwell: vertical boards, a doorway
    at the west end with a lattice transom."""
    y0, y1 = P1
    d0, d1 = P1_DOOR
    for name, (x0, x1) in (("west", (0, d0)), ("east", (d1, W))):
        boards(f"partition_boards_{name}", x0, x1, y0, y1, 0, H, m["boards"], width=0.14)
        collider(f"partition_{name}", area, x0, x1, y0, y1, 0, H)
    boards("partition_boards_head", d0, d1, y0, y1, 2.65, H, m["boards"], width=0.14)
    for x in (d0, d1):
        box(f"partition_door_post_{x:.2f}", area, x - 0.05, x + 0.05, y0 - 0.02, y1 + 0.02, 0, 2.65, m["wood"], edge=0.006)
    box("partition_door_head", area, d0 - 0.05, d1 + 0.05, y0 - 0.02, y1 + 0.02, 2.2, 2.28, m["wood"], edge=0.006)
    # Lattice transom (fretwork) between the door head and the boards.
    for i in range(1, 9):
        x = d0 + (d1 - d0) * i / 9
        box(f"partition_lattice_v_{i}", area, x - 0.008, x + 0.008, y0 + 0.03, y1 - 0.03, 2.28, 2.65, m["wood"])
    for z in (2.4, 2.53):
        box(f"partition_lattice_h_{z}", area, d0, d1, y0 + 0.03, y1 - 0.03, z - 0.008, z + 0.008, m["wood"])
    # Skirting and dado rail on the studio side.
    box("partition_skirting_east", area, d1, W, y0 - 0.015, y0, 0, 0.12, m["wood"], edge=0.003)
    box("partition_skirting_west", area, 0, d0, y0 - 0.015, y0, 0, 0.12, m["wood"], edge=0.003)
    box("partition_rail", area, d1, W, y0 - 0.025, y0, DADO, DADO + 0.04, m["wood"], edge=0.004)
    # Detailed 1932 colonial 4-panel solid teak studio partition door (openable/closable + haunted!)
    leaf = (d1 - d0) - 0.03
    pdoor = empty("haunt_partition_door", area, (d0 + 0.015, y1 - 0.005, 0.004), (0, 0, math.radians(88)), action="use")
    bpy.context.view_layer.update()
    pparts = [
        box("part_door_stile_l", area, 0.0, 0.085, 0.0, 0.042, 0.0, 2.18, m["teak"], edge=0.004),
        box("part_door_stile_r", area, leaf - 0.085, leaf, 0.0, 0.042, 0.0, 2.18, m["teak"], edge=0.004),
        box("part_door_mullion", area, leaf / 2 - 0.032, leaf / 2 + 0.032, 0.002, 0.040, 0.18, 2.06, m["teak"], edge=0.003),
        box("part_door_rail_bot", area, 0.0, leaf, 0.0, 0.042, 0.0, 0.19, m["teak"], edge=0.004),
        box("part_door_rail_mid", area, 0.0, leaf, 0.0, 0.042, 0.90, 1.04, m["teak"], edge=0.004),
        box("part_door_rail_top", area, 0.0, leaf, 0.0, 0.042, 2.05, 2.18, m["teak"], edge=0.004),
        box("part_door_kick_s", area, 0.01, leaf - 0.01, -0.003, 0.001, 0.01, 0.12, m["brass"], edge=0.001),
    ]
    # Four bevelled raised colonial panels (2 tall upper, 2 square lower)
    for px_tag, (px0, px1) in (("w", (0.085, leaf / 2 - 0.032)), ("e", (leaf / 2 + 0.032, leaf - 0.085))):
        for pz_tag, (pz0, pz1) in (("lo", (0.19, 0.90)), ("hi", (1.04, 2.05))):
            pparts.append(box(f"part_door_panel_{px_tag}_{pz_tag}", area, px0, px1, 0.010, 0.032, pz0, pz1, m["wood"]))
            pparts.append(box(f"part_door_raise_{px_tag}_{pz_tag}", area, px0 + 0.024, px1 - 0.024, 0.005, 0.037, pz0 + 0.028, pz1 - 0.028, m["rosewood"], edge=0.009))
    # Brass mortise lockplates, keyhole escutcheons & turned brass knobs on BOTH faces
    for side, yy, rot in (("s", -0.002, math.pi / 2), ("n", 0.044, -math.pi / 2)):
        pparts.append(box(f"part_door_lockplate_{side}", area, leaf - 0.095, leaf - 0.045, yy - 0.003, yy + 0.003, 0.87, 1.09, m["brass"], edge=0.002))
        pparts.append(box(f"part_door_keyhole_{side}", area, leaf - 0.074, leaf - 0.066, yy - 0.004, yy + 0.004, 0.90, 0.925, m["dark"]))
        kb = turned(f"part_door_knob_{side}", [(0.0, 0.0), (0.017, 0.0), (0.010, 0.028), (0.024, 0.048), (0.0, 0.060)], 0, 0, 0, m["brass"], segments=16)
        kb.location = (leaf - 0.070, yy, 0.99)
        kb.rotation_euler = (rot, 0, 0)
        pparts.append(kb)
    for k, hz in enumerate((0.26, 1.09, 1.92)):
        pparts.append(box(f"part_door_hinge_{k}", area, -0.006, 0.048, 0.038, 0.048, hz - 0.038, hz + 0.038, m["iron"], edge=0.002))
        pparts.append(cylinder(f"part_door_hinge_pin_{k}", area, -0.004, 0.046, hz - 0.044, hz + 0.044, 0.006, m["iron"], verts=8))
    for p in pparts:
        p.parent = pdoor


def draped(name, xa, xb, y, z, drop, mat, segments=(28, 22)):
    """Cloth hung over a pole: a front and a back fall, soft vertical folds, a sagging
    uneven hem, and the fold over the pole itself."""
    nx, nz = segments
    verts, faces, uvs = [], [], []
    rows = []
    for side in (-1, 1):
        length = drop * (1.0 if side < 0 else 0.82)
        for j in range(nz + 1):
            t = j / nz
            row = []
            for i in range(nx + 1):
                u = i / nx
                x = xa + (xb - xa) * u
                fold = math.sin(u * math.tau * 3.2 + side) * 0.018 * t + math.sin(u * math.tau * 7.1) * 0.006 * t
                hem = (0.05 * math.sin(u * 5.3 + side) + 0.04 * math.cos(u * 9.1)) * t * t
                zz = z - length * t + hem
                yy = y + side * (0.026 + 0.03 * t) + fold
                row.append(len(verts))
                verts.append((x, yy, zz))
                uvs_ = (u * (xb - xa) / 0.4, (t * length) / 0.4)
            rows.append(row)
        base = len(rows) - (nz + 1)
        for j in range(nz):
            for i in range(nx):
                a, b = rows[base + j][i], rows[base + j][i + 1]
                c, d = rows[base + j + 1][i + 1], rows[base + j + 1][i]
                faces.append((a, b, c, d) if side > 0 else (d, c, b, a))
    # The fold over the pole joins the two tops.
    front_top, back_top = rows[0], rows[nz + 1]
    for i in range(nx):
        faces.append((front_top[i], front_top[i + 1], back_top[i + 1], back_top[i]))
    obj = mesh_object(name, area, verts, faces, mat, smooth=True)
    mat.use_backface_culling = False
    return obj


def peg_cloth(name, tip, width, drop, mat, seed=0, segments=(14, 18)):
    """A cloth hung by its middle from a peg: both layers pinched together at the peg,
    spreading into soft folds below, the back layer a little shorter and nearer the wall."""
    r = np.random.default_rng(seed)
    nx, nz = segments
    tx, ty, tz = tip
    ph = r.uniform(0, math.tau, 3)
    verts, faces = [], []
    for side, length in ((1, drop), (-1, drop * 0.86)):
        base = len(verts)
        for j in range(nz + 1):
            t = j / nz
            half = 0.012 + (width / 2 - 0.012) * (1 - (1 - t) ** 2.2)
            for i in range(nx + 1):
                u = 2 * i / nx - 1
                fold = (math.sin(u * math.pi * 2.5 + ph[0] + side) * 0.022 + math.sin(u * math.pi * 5.3 + ph[1]) * 0.007) * min(1.0, t * 3) * (1 - 0.35 * t)
                hem = (0.03 * math.sin(u * 4.1 + ph[2]) + 0.02 * u * u) * t ** 3
                verts.append((tx + u * half, ty + side * (0.008 + 0.022 * math.sqrt(t)) + fold * (1.0 if side > 0 else 0.6), tz - length * t + hem))
        for j in range(nz):
            for i in range(nx):
                a = base + j * (nx + 1) + i
                q = (a, a + 1, a + nx + 2, a + nx + 1)
                faces.append(q if side > 0 else tuple(reversed(q)))
    obj = mesh_object(name, area, verts, faces, mat, smooth=True)
    mat.use_backface_culling = False
    return obj


def pegged_sheet(name, top, along, normal, size, front, back, seed=0, n=8):
    """A sheet of paper pegged to a line by its top edge: `front` shows on the side facing
    `normal` (the image upright for someone looking at it), `back` on the other; the lower
    corners curl a little towards the room as it dries."""
    r = np.random.default_rng(seed)
    a = np.array(along, float); a /= np.linalg.norm(a)
    nv = np.array(normal, float); nv /= np.linalg.norm(nv)
    top = np.array(top, float)
    curl = r.uniform(0.008, 0.02)
    pts = []
    for j in range(n + 1):
        v = j / n
        for i in range(n + 1):
            u = i / n - 0.5
            off = curl * v * v * (abs(u) * 2) ** 1.5 + 0.004 * math.sin(v * math.pi) + 0.002 * math.sin(u * 7 + seed)
            pts.append(top - a * u * size + nv * off - np.array((0, 0, v * size)))
    quads = []
    for j in range(n):
        for i in range(n):
            k = j * (n + 1) + i
            quads.append((k, k + n + 1, k + n + 2, k + 1))
    def uv(k):
        i, j = k % (n + 1), k // (n + 1)
        return (i / n, 1 - j / n)
    fr = mesh_object(f"{name}_front", area, [tuple(p) for p in pts], quads, front, uvs=[uv(k) for q in quads for k in q])
    back_pts = [tuple(np.array(p) - nv * 0.0006) for p in pts]
    bk = mesh_object(f"{name}_back", area, back_pts, [tuple(reversed(q)) for q in quads], back, uvs=[uv(k) for q in quads for k in reversed(q)])
    return fr, bk


def cobweb_material():
    """Cobweb cards: radial threads and a sagging spiral, alpha-tested."""
    n = 512
    yy, xx = np.mgrid[:n, :n].astype(np.float32)
    # The web hangs in a corner: its centre near one corner of the card.
    cx, cy = 0.08 * n, 0.08 * n
    dx, dy = xx - cx, yy - cy
    r = np.hypot(dx, dy) / n
    a = np.arctan2(dy, dx)
    radial = np.zeros((n, n), bool)
    for t in np.linspace(0.02, math.pi / 2 - 0.02, 9):
        radial |= (np.abs(np.sin(a - t)) * r * n < 0.9) & (r < 1.1)
    spiral = (np.abs(((r * 34 + a * 0.9) % 1.0) - 0.5) < 0.035) & (r < 0.95) & (r > 0.05)
    rng_ = np.random.default_rng(7)
    broken = rng_.random((n, n)) < 0.25
    web = (radial | (spiral & ~broken)).astype(np.float32)
    rgba = np.zeros((n, n, 4), np.float32)
    rgba[..., :3] = (0.78, 0.76, 0.72)
    rgba[..., 3] = web * 0.85
    img = bpy.data.images.new("T_studio_cobweb_BC", n, n, alpha=True)
    img.pixels.foreach_set(rgba[::-1].ravel())
    path = os.path.join(TEXTURES, "T_studio_cobweb_BC.png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return image_material("M_studio_cobweb", path, rough=1.0, cutout=True)


def cobweb(name, corner, u, v, size):
    """A web card spanning a corner: `corner` is the corner point, `u` and `v` the two
    directions along the surfaces it is strung between."""
    c = np.array(corner, float)
    u = np.array(u, float) * size
    v = np.array(v, float) * size
    verts = [tuple(c), tuple(c + u), tuple(c + u + v * 0.9), tuple(c + v)]
    return mesh_object(name, area, verts, [(0, 1, 2, 3)], m["cobweb"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])


# Cells of the crack atlas (columns, rows): tools/drawings/cracks.mjs paints one crack per cell.
CRACK_GRID = (4, 2)


def crack_material():
    """The crack decals' material: near-black, so blended over a wall it only darkens
    it, whatever light falls there; the atlas's alpha is the crack (glTF alphaMode
    BLEND). Not lightmapped (the bake skips "crack"), and hidden from the bake."""
    mat = bpy.data.materials.new("M_studio_cracks")
    mat.blend_method = "BLEND"
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image(os.path.join(TEXTURES, "T_studio_cracks_BC.png"), False)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 1.0
    mat["tile"] = 0.0
    return mat


def frame(x_axis, y_axis, origin):
    """A placement matrix from two axes (the third is their cross product) and an origin."""
    x = mathutils.Vector(x_axis).normalized()
    y = mathutils.Vector(y_axis).normalized()
    z = x.cross(y)
    m4 = mathutils.Matrix((
        (x.x, y.x, z.x, origin[0]),
        (x.y, y.y, z.y, origin[1]),
        (x.z, y.z, z.z, origin[2]),
        (0, 0, 0, 1)))
    return m4


BOOK_CLOTHS = [(0.12, 0.2, 0.17), (0.24, 0.11, 0.07), (0.1, 0.15, 0.23), (0.3, 0.24, 0.14), (0.2, 0.18, 0.12), (0.26, 0.07, 0.06), (0.09, 0.09, 0.08)]
BOOK_CATALOG = [(atlas_key, bid, item) for atlas_key, spec in BOOKS["atlases"].items() for bid, item in spec["items"].items()]
BOOK_BY_ID = {bid: (atlas_key, item) for atlas_key, bid, item in BOOK_CATALOG}


def _page_edges_material():
    """Yellowed deckle-edged book pages with fine horizontal paper leaf striations."""
    n = 256
    rgen = np.random.default_rng(19329)
    yy, xx = np.mgrid[:n, :n].astype(np.float32)
    stripes = 0.90 + 0.10 * np.sin(yy * 1.45) * 0.6 + rgen.normal(0, 0.035, (n, 1))
    grain = rgen.normal(0, 0.025, (n, n))
    base = np.array((0.74, 0.67, 0.52), np.float32)
    rgb = np.clip(base[None, None, :] * (stripes + grain)[..., None], 0.1, 1.0)
    path = save_png("T_studio_page_edges_BC", rgb)
    mat = image_material("M_studio_page_edges", path, rough=0.94, tile=0.06)
    return mat


def book_materials():
    if "book_covers" not in m:
        m["book_covers"] = [plain(f"M_studio_book_cloth_{i}", c, rough=0.85) for i, c in enumerate(BOOK_CLOTHS)]
        m["book_pages"] = _page_edges_material()
        m["book_gilt"] = plain("M_studio_book_gilt", (0.5, 0.38, 0.17), rough=0.45, metal=0.6)
    return m["book_covers"], m["book_pages"], m["book_gilt"]


def _atlas_rect_uv(rect, size=2048):
    x, y, w, h = rect
    return (x / size, (x + w) / size, 1.0 - (y + h) / size, 1.0 - y / size)


def _uv_box(name, x0, x1, y0, y1, z0, z1, mat, face_rects, fallback_rect, size=2048):
    """Axis-aligned box with exact per-face UV rectangles from a texture atlas."""
    verts = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    # Outward faces keyed by normal: +z, -z, -x, +x, -y, +y
    quads = [
        ("+z", (4, 5, 6, 7)),
        ("-z", (1, 0, 3, 2)),
        ("-x", (0, 4, 7, 3)),
        ("+x", (5, 1, 2, 6)),
        ("-y", (0, 1, 5, 4)),
        ("+y", (3, 7, 6, 2)),
    ]
    faces, uvs = [], []
    fu0, fu1, fv0, fv1 = _atlas_rect_uv(fallback_rect, size)
    # Inset fallback cloth swatch slightly to avoid any edge bleed
    pad_u, pad_v = (fu1 - fu0) * 0.15, (fv1 - fv0) * 0.15
    fb = (fu0 + pad_u, fu1 - pad_u, fv0 + pad_v, fv1 - pad_v)
    for key, q in quads:
        faces.append(q)
        u0, u1, v0, v1 = _atlas_rect_uv(face_rects[key], size) if key in face_rects else fb
        uvs += [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    return mesh_object(name, area, verts, faces, mat, uvs=uvs)


def book(name, placement, w, h, t, cover=0, bands=2, label=False, quarter=None, props=None):
    """A real bound book mapped to our 32-volume public-domain vintage cover & spine
    atlases (studio_books.json): boards slightly proud of a striated yellowed page block,
    real scanned front cover, color-matched titled spine and matching back board.
    When `cover` is a Blender Material (e.g. Sora's bespoke sketchbook), uses plain cloth.
    Its own frame: X across the cover (fore-edge +X, spine -X), Y up the height, Z
    through the thickness from the bottom board; `placement` puts that frame in the room."""
    _covers, pages, _gilt = book_materials()
    root = empty(name, area, (0, 0, 0), **(props or {}))
    b = min(0.0028, t * 0.14)
    if isinstance(cover, (int, str)):
        if isinstance(cover, str) and cover in BOOK_BY_ID:
            atlas_key, item = BOOK_BY_ID[cover]
        else:
            atlas_key, _bid, item = BOOK_CATALOG[int(cover) % len(BOOK_CATALOG)]
        mat = m[f"book_atlas_{atlas_key}"]
        sz = BOOKS["atlases"][atlas_key]["size"][0]
        parts = [
            _uv_box(f"{name}_board_low", -w / 2 + b, w / 2, -h / 2, h / 2, 0, b, mat,
                    {"-z": item["back"]}, item["back"], sz),
            _uv_box(f"{name}_board_up", -w / 2 + b, w / 2, -h / 2, h / 2, t - b, t, mat,
                    {"+z": item["front"]}, item["back"], sz),
            box(f"{name}_pages", area, -w / 2 + b, w / 2 - 0.0025, -h / 2 + 0.0025, h / 2 - 0.0025, b, t - b, pages),
            _uv_box(f"{name}_spine", -w / 2, -w / 2 + b, -h / 2, h / 2, 0, t, mat,
                    {"-x": item["spine"]}, item["back"], sz),
        ]
    else:
        cloth = cover
        parts = [
            box(f"{name}_board_low", area, -w / 2 + b, w / 2, -h / 2, h / 2, 0, b, cloth, edge=0.0008),
            box(f"{name}_board_up", area, -w / 2 + b, w / 2, -h / 2, h / 2, t - b, t, cloth, edge=0.0008),
            box(f"{name}_pages", area, -w / 2 + b, w / 2 - 0.0025, -h / 2 + 0.0025, h / 2 - 0.0025, b, t - b, pages),
            box(f"{name}_spine", area, -w / 2, -w / 2 + b, -h / 2, h / 2, 0, t, quarter or cloth, edge=0.0008),
        ]
        if quarter is not None:
            for z0, z1 in ((t, t + 0.0004), (-0.0004, 0)):
                parts.append(box(f"{name}_quarter_{z0:.3f}", area, -w / 2, -w / 2 + min(0.04, w * 0.18), -h / 2, h / 2, z0, z1, quarter))
    for part in parts:
        part.parent = root
    root.matrix_world = placement
    return root


def smooth_path(points, n=8):
    """Catmull-Rom through `points`: a cord or a cable that bends instead of kinking."""
    pts = [np.array(p, float) for p in points]
    pts = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    out.append(tuple(pts[-2]))
    return out


def mesh_points(prop):
    bpy.context.view_layer.update()
    objs = [prop] + list(prop.children_recursive)
    return np.array([tuple(o.matrix_world @ v.co) for o in objs if o.type == "MESH" for v in o.data.vertices])


def against_west_wall(prop, gap=0.002, wall_x=0.0125):
    """Slides a hung thing along X until its back just meets the west wall's plaster."""
    pts = mesh_points(prop)
    prop.location.x += (wall_x + gap) - pts[:, 0].min()


def hang_on_north_wall(prop, name, wall_y):
    """Hangs a basket or winnowing tray on the north hall wall facing -Y from a nail by a cord loop."""
    pts = mesh_points(prop)
    prop.location.y += (wall_y - 0.002) - pts[:, 1].max()
    pts = mesh_points(prop)
    top = pts[:, 2].max()
    rim = pts[pts[:, 2] > top - 0.012]
    p = rim.mean(axis=0)
    nail_z = top + 0.035
    tube(f"{name}_nail", area, [(p[0], wall_y + 0.004, nail_z), (p[0], wall_y - 0.032, nail_z + 0.004)], 0.0022, m["iron"], sides=6)
    nh = cylinder(f"{name}_nail_head", area, 0, 0, 0, 0.002, 0.0045, m["iron"], verts=8)
    nh.location = (p[0], wall_y - 0.032, nail_z + 0.004)
    nh.rotation_euler = (math.pi / 2, 0, 0)
    hook = (p[0], wall_y - 0.024, nail_z + 0.0045)
    for side, k in ((-1, 0), (1, 1)):
        q = rim[np.argmin(np.abs(rim[:, 0] - (p[0] + side * 0.03)))]
        tube(f"{name}_cord_{k}", area, smooth_path([tuple(q + np.array((0, 0, -0.003))), ((q[0] + hook[0]) / 2, (q[1] + hook[1]) / 2, (q[2] + hook[2]) / 2 + 0.004), hook], 6), 0.0016, m["cord"], sides=5)


def hang_on_nail(prop, name, wall_x=0.0125):
    """Hangs a thing on the west wall from a nail by a cord loop: the nail driven in just
    above where the thing's top really is, the cord running from it to the rim on either
    side, so nothing hangs from a nail it does not touch."""
    against_west_wall(prop)
    pts = mesh_points(prop)
    top = pts[:, 2].max()
    rim = pts[pts[:, 2] > top - 0.012]
    p = rim.mean(axis=0)
    nail_z = top + 0.035
    tube(f"{name}_nail", area, [(wall_x - 0.004, p[1], nail_z), (wall_x + 0.032, p[1], nail_z + 0.004)], 0.0022, m["iron"], sides=6)
    cylinder(f"{name}_nail_head", area, 0, 0, 0, 0.002, 0.0045, m["iron"], verts=8).location = (wall_x + 0.032, p[1], nail_z + 0.004)
    bpy.data.objects[f"{name}_nail_head"].rotation_euler = (0, math.pi / 2, 0)
    hook = (wall_x + 0.024, p[1], nail_z + 0.0045)
    for side, k in ((-1, 0), (1, 1)):
        q = rim[np.argmin(np.abs(rim[:, 1] - (p[1] + side * 0.03)))]
        tube(f"{name}_cord_{k}", area, smooth_path([tuple(q + np.array((0, 0, -0.003))), ((q[0] + hook[0]) / 2, (q[1] + hook[1]) / 2, (q[2] + hook[2]) / 2 + 0.004), hook], 6), 0.0016, m["cord"], sides=5)


def fits_on(prop, support, step=0.01, limit=0.2):
    """Moves a prop standing on a shelf in toward the wall (-X) until every part of its
    foot is over the shelf board, so nothing overhangs a curved front edge into the air."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for o in [support] + list(support.children_recursive):
        if o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        base = len(verts)
        verts += [o.matrix_world @ v.co for v in me.vertices]
        polys += [[base + i for i in poly.vertices] for poly in me.polygons]
        ev.to_mesh_clear()
    tree = BVHTree.FromPolygons(verts, polys)
    moved = 0.0
    while moved < limit:
        pts = mesh_points(prop)
        low = pts[pts[:, 2] < pts[:, 2].min() + 0.006]
        ring = low[np.argsort(-np.hypot(low[:, 0] - low[:, 0].mean(), low[:, 1] - low[:, 1].mean()))[:12]]
        ok = all(tree.ray_cast(mathutils.Vector(q) + mathutils.Vector((0, 0, 0.004)), mathutils.Vector((0, 0, -1)), 0.02)[0] is not None for q in ring)
        if ok:
            return
        prop.location.x -= step
        moved += step
    print(f"{prop.name}: no footing found within {limit} m", flush=True)


def jar_glaze_material():
    """A storage jar's glaze: iron brown, darker where it ran thick in drips down the body,
    paler where it thinned over the shoulder, flecked with iron spots. The jar's UVs run
    round it (0-1) and up it in metres, so the drips hang straight down."""
    n = 512
    rgen = np.random.default_rng(32)
    yy, xx = np.mgrid[:n, :n] / n
    base = np.array((0.23, 0.125, 0.06))  # sRGB, as the PNG is read
    tone = 1 + 0.12 * np.sin(xx * 2 * math.pi * 3 + 1.3) * np.sin(yy * 9)
    rgb = np.ones((n, n, 3), np.float32) * base * tone[..., None]
    for _ in range(70):
        cx, top_, length, width = rgen.uniform(0, 1), rgen.uniform(0.35, 0.95), rgen.uniform(0.05, 0.3), rgen.uniform(0.004, 0.012)
        dx = np.abs(((xx - cx + 0.5) % 1) - 0.5)
        run = (yy < top_) & (yy > top_ - length) & (dx < width * (0.6 + 0.4 * (yy - top_ + length) / length))
        rgb[run] *= rgen.uniform(0.55, 0.75)
    shoulder = np.clip((yy - 0.62) / 0.12, 0, 1) * np.clip((0.86 - yy) / 0.08, 0, 1)
    rgb *= (1 + 0.45 * shoulder)[..., None]
    spots = rgen.random((n, n)) < 0.0025
    rgb[spots] = (0.11, 0.065, 0.04)
    img = bpy.data.images.new("T_studio_jar_glaze_BC", width=n, height=n, alpha=False)
    rgba = np.concatenate([rgb, np.ones((n, n, 1))], axis=2).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(TEXTURES, "T_studio_jar_glaze_BC.png")
    img.file_format = "PNG"
    img.save()
    mat = image_material("M_studio_jar_dark_glaze", img.filepath_raw, rough=0.16)
    mat["tile"] = 0.0
    return mat


def save_png(name, rgb):
    """Writes an (n, n, 3) sRGB array (row 0 at the bottom, as Blender stores images) to
    art-source/textures/ep1/<name>.png and returns its path."""
    h, w = rgb.shape[:2]
    img = bpy.data.images.new(name, width=w, height=h, alpha=False)
    rgba = np.concatenate([np.clip(rgb, 0, 1), np.ones((h, w, 1))], axis=2).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(TEXTURES, f"{name}.png")
    img.file_format = "PNG"
    img.save()
    return img.filepath_raw


def top_projected_uvs(obj, cx, cy, radius):
    """UVs straight down onto a disc of `radius` round (cx, cy): turned ware whose pattern
    is painted round it (a plate's blue bands, an enamel dish's rim)."""
    mesh = obj.data
    layer = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    mw = obj.matrix_world
    for li, loop in enumerate(mesh.loops):
        co = mw @ mesh.vertices[loop.vertex_index].co
        layer.data[li].uv = ((co.x - cx) / (2 * radius) + 0.5, (co.y - cy) / (2 * radius) + 0.5)


def radial_ware_material(name, kind, seed, rough):
    """The glaze of round ware, painted as seen from above (top_projected_uvs), the disc's
    edge at the image's edge. kind "plate": a Chinese blue-and-white export plate of the
    kind every Phnom Penh kitchen had, cobalt bands at the rim and round the well, a
    ring of dots and a flower in the middle, the brushwork uneven, the rim chipped to the
    biscuit in two places. kind "enamel": white enamelled iron with a navy rim, chipped
    black at the edge and round the socket."""
    n = 1024
    rgen = np.random.default_rng(seed)
    yy, xx = (np.mgrid[:n, :n] + 0.5) / n * 2 - 1
    r = np.hypot(xx, yy)
    th = np.arctan2(yy, xx)
    w = 3.0 / n

    def band(r0, r1):
        return np.clip((r - r0) / w, 0, 1) * np.clip((r1 - r) / w, 0, 1)

    paint = np.zeros((n, n))
    if kind == "plate":
        base = np.array((0.88, 0.885, 0.85))
        blue = np.array((0.11, 0.17, 0.42))
        for r0, r1, a in ((0.935, 0.99, 1.0), (0.885, 0.897, 0.9), (0.628, 0.64, 0.85), (0.6, 0.607, 0.7)):
            paint = np.maximum(paint, a * band(r0, r1))
        # A ring of sixteen dots between the bands.
        for k in range(16):
            a = k * math.tau / 16 + 0.1
            d = np.hypot(xx - 0.76 * math.cos(a), yy - 0.76 * math.sin(a))
            paint = np.maximum(paint, 0.85 * np.clip((0.028 - d) / w, 0, 1))
        # The flower: eight petals washed in, outlined darker, a solid heart.
        rp = 0.3 * (0.55 + 0.45 * np.abs(np.cos(4 * th)))
        paint = np.maximum(paint, 0.45 * np.clip((rp - r) / w, 0, 1) * np.clip((r - 0.07) / w, 0, 1))
        paint = np.maximum(paint, 0.9 * np.clip(1 - np.abs(r - rp) / (2.2 * w), 0, 1))
        paint = np.maximum(paint, np.clip((0.07 - r) / w, 0, 1))
        chip = np.array((0.66, 0.6, 0.5))
    else:
        base = np.array((0.84, 0.845, 0.8))
        blue = np.array((0.06, 0.08, 0.2))
        paint = np.maximum(paint, band(0.9, 1.01))
        chip = np.array((0.05, 0.045, 0.04))
    # Brushed cobalt is never even: thicker and thinner along the stroke.
    wash = 0.75 + 0.25 * np.sin(th * 7 + r * 11) * np.sin(th * 3 - 1.7)
    rgb = base * (1 - paint[..., None]) + (blue * wash[..., None]) * paint[..., None]
    # Glaze pooled a little darker in the hollow of the well, specks in it.
    rgb *= (1 - 0.05 * np.exp(-((r - 0.62) / 0.05) ** 2))[..., None]
    specks = rgen.random((n, n)) < 0.0012
    rgb[specks] *= 0.6
    # Chips at the rim (and, on the enamel, round the socket and a few on the dish).
    spots = [(rgen.uniform(-math.pi, math.pi), 0.975, 0.035, 0.05) for _ in range(2 if kind == "plate" else 5)]
    if kind == "enamel":
        spots += [(rgen.uniform(-math.pi, math.pi), rgen.uniform(0.3, 0.8), 0.02, 0.025) for _ in range(4)]
    for a, rc, size, _ in spots:
        cx_, cy_ = rc * math.cos(a), rc * math.sin(a)
        ang = np.arctan2(yy - cy_, xx - cx_)
        d = np.hypot(xx - cx_, yy - cy_) * (1 + 0.22 * np.sin(ang * 3 + a) + 0.12 * np.sin(ang * 7 + 2 * a))
        mask = np.clip((size - d) / w, 0, 1)
        rgb = rgb * (1 - mask[..., None]) + chip * mask[..., None]
        if kind == "enamel":  # rust bleeds out round the bare iron
            halo = np.clip((size * 1.6 - d) / (size * 0.6), 0, 1) * (1 - mask)
            rgb = rgb * (1 - 0.5 * halo[..., None]) + np.array((0.32, 0.17, 0.08)) * 0.5 * halo[..., None]
    path = save_png(f"T_studio_{name}_BC", rgb)
    mat = image_material(f"M_studio_{name}", path, rough=rough)
    mat["tile"] = 0.0
    return mat


def swept(name, rings, mat, sides=20, cap_start=True, cap_end=True, smooth=True):
    """A closed tube through `rings`: (centre, unit normal, unit binormal, radius function
    of the angle, v) per ring, round each ring in the normal-binormal plane. UVs: u round
    (0-1), v as given. Caps close the ends at their centres."""
    verts, faces, uvs = [], [], []
    for c, nrm, bin_, rad, _ in rings:
        for k in range(sides + 1):
            a = math.tau * k / sides
            rr = rad(a)
            verts.append(tuple(c + (nrm * math.cos(a) + bin_ * math.sin(a)) * rr))
    for i in range(len(rings) - 1):
        for k in range(sides):
            a = i * (sides + 1) + k
            faces.append((a, a + sides + 1, a + sides + 2, a + 1))
            for (ii, kk) in ((i, k), (i + 1, k), (i + 1, k + 1), (i, k + 1)):
                uvs.append((kk / sides, rings[ii][4]))
    for cap, i, flip in ((cap_start, 0, True), (cap_end, len(rings) - 1, False)):
        if not cap:
            continue
        centre = len(verts)
        verts.append(tuple(rings[i][0]))
        for k in range(sides):
            a = i * (sides + 1) + k
            faces.append((centre, a + 1, a) if flip else (centre, a, a + 1))
            uvs += [(0.5, rings[i][4]), ((k + (0 if flip else 1)) / sides, rings[i][4]), ((k + (1 if flip else 0)) / sides, rings[i][4])]
    return mesh_object(name, area, verts, faces, mat, uvs=uvs, smooth=smooth)


def banana_skin_material():
    """Ripe bananas, the short plump chek nam va of every Phnom Penh market: yellow, going to
    brown sugar spots and a soft bruise or two, still green at the neck, the stalk fibrous
    and the blossom tip black, the five edges a shade darker. UVs: u round the finger, v
    along it from the stalk (0) to the tip (1)."""
    if "banana_skin" in m:
        return m["banana_skin"]
    n = 512
    rgen = np.random.default_rng(1932)
    v, u = (np.mgrid[:n, :n] + 0.5) / n
    rgb = np.ones((n, n, 3)) * np.array((0.83, 0.65, 0.17))
    # Faint streaks running along the finger, and its edges.
    col = np.convolve(np.tile(rgen.normal(0, 1, n), 3), np.ones(9) / 9, "same")[n:2 * n]
    rgb *= (1 + 0.05 * col)[None, :, None]
    f = (u * 5) % 1
    ridge = np.clip(1 - np.minimum(f, 1 - f) / 0.07, 0, 1)
    rgb = rgb * (1 - 0.2 * ridge[..., None]) + np.array((0.36, 0.38, 0.1)) * 0.12 * ridge[..., None]
    # Sugar spots, small and many, and two soft bruises.
    for _ in range(320):
        cu, cv = rgen.uniform(0, 1), rgen.uniform(0.14, 0.9)
        rad = rgen.uniform(1.2, 4.5) / n
        du = np.minimum(np.abs(u - cu), 1 - np.abs(u - cu))
        d = np.hypot(du, (v - cv) * 0.8)
        a = np.clip(1 - d / rad, 0, 1) ** 0.7 * rgen.uniform(0.5, 0.95)
        rgb = rgb * (1 - a[..., None]) + np.array((0.27, 0.15, 0.05)) * a[..., None]
    for _ in range(2):
        cu, cv = rgen.uniform(0, 1), rgen.uniform(0.3, 0.75)
        du = np.minimum(np.abs(u - cu), 1 - np.abs(u - cu))
        a = np.exp(-(du ** 2 + ((v - cv) * 0.5) ** 2) / (2 * 0.035 ** 2)) * 0.45
        rgb = rgb * (1 - a[..., None]) + np.array((0.4, 0.26, 0.08)) * a[..., None]
    # Green at the neck, the stalk grey-green and stringy; the tip black.
    neck = np.clip((0.17 - v) / 0.1, 0, 1)[..., None]
    rgb = rgb * (1 - 0.85 * neck) + np.array((0.4, 0.47, 0.15)) * 0.85 * neck
    stalk = np.clip((0.06 - v) / 0.025, 0, 1)[..., None]
    fibre = (0.85 + 0.3 * np.sin(u * math.tau * 23))[..., None]
    rgb = rgb * (1 - stalk) + np.array((0.3, 0.29, 0.15)) * fibre * stalk
    tip = np.clip((v - 0.93) / 0.045, 0, 1)[..., None]
    rgb = rgb * (1 - tip) + np.array((0.08, 0.065, 0.04)) * tip
    m["banana_skin"] = image_material("M_studio_banana_skin", save_png("T_studio_banana_skin_BC", rgb), rough=0.48)
    m["banana_skin"]["tile"] = 0.0
    m["banana_crown"] = plain("M_studio_banana_crown", (0.2, 0.19, 0.09), rough=0.85)
    return m["banana_skin"]


BANANA_PROFILE = ((0.0, 0.3), (0.04, 0.33), (0.1, 0.6), (0.18, 0.88), (0.45, 1.0), (0.72, 0.95), (0.86, 0.75), (0.95, 0.42), (1.0, 0.13))


def banana(name, start, heading, length, radius, bend, roll=0.0):
    """One banana finger: five-sided, thin at the neck, plump in the body, tapering to a
    black tip; it starts at `start` (the neck, where it joins the crown) and runs along
    `heading` (horizontal), curved so that it rests on its belly with both ends lifted."""
    d = mathutils.Vector(heading).normalized()
    up = mathutils.Vector((0, 0, 1))
    side = d.cross(up).normalized()
    R = length / bend
    s0 = math.sin(-bend / 2)
    lift = R * (1 - math.cos(bend / 2))
    ts, fs = zip(*BANANA_PROFILE)
    rings = []
    for i in range(29):
        t = i / 28
        a = bend * (t - 0.5)
        c = mathutils.Vector(start) + d * (R * (math.sin(a) - s0)) + up * (R * (1 - math.cos(a)) - lift)
        tangent = d * math.cos(a) + up * math.sin(a)
        nrm = (up * math.cos(a) - d * math.sin(a)).normalized()
        rr = radius * float(np.interp(t, ts, fs))

        def rad(ang, rr=rr):
            # Pentagonal, the edges rounded: between a circle and the polygon.
            seg = math.tau / 5
            poly = math.cos(math.pi / 5) / math.cos(((ang + roll) % seg) - math.pi / 5)
            return rr * (0.45 + 0.55 * poly)
        rings.append((c, nrm, side, rad, t))
        if i == 28:
            tip = c + tangent * 0.004
    rings.append((tip, rings[-1][1], side, lambda ang: 0.0008, 1.0))
    return swept(name, rings, banana_skin_material(), sides=20, cap_start=True, cap_end=True)


def banana_hand(name, at, heading_deg, count=4, length=0.12, radius=0.0155, seed=0):
    """A hand of bananas lying on its side: the fingers fanned out from a short crown, each
    resting on its belly with its neck and tip lifted. `at` is the middle of the necks, on
    the surface the hand lies on; settle() it afterwards."""
    rgen = np.random.default_rng(seed)
    banana_skin_material()
    root = empty(name, area, at)
    bpy.context.view_layer.update()  # the fingers are parented keeping their world place
    h = math.radians(heading_deg)
    fwd = mathutils.Vector((math.cos(h), math.sin(h), 0))
    side = mathutils.Vector((-math.sin(h), math.cos(h), 0))
    bend = 0.95
    lift = length / bend * (1 - math.cos(bend / 2))
    base = mathutils.Vector(at) + mathutils.Vector((0, 0, lift + radius * 0.93))
    for k in range(count):
        off = k - (count - 1) / 2
        a = h + off * math.radians(17) + float(rgen.normal(0, 0.03))
        start = base + side * (off * 0.011)
        f = banana(f"{name}_finger_{k}", start, (math.cos(a), math.sin(a), 0), length * float(rgen.uniform(0.94, 1.04)),
                   radius * float(rgen.uniform(0.95, 1.04)), bend + float(rgen.normal(0, 0.04)), roll=float(rgen.uniform(0, 1.2)))
        f.parent = root
        f.matrix_parent_inverse = root.matrix_world.inverted()
    # The crown: the stalk all the fingers grow from, cut off square.
    c0 = base - fwd * 0.003
    rings = []
    for i in range(7):
        t = i / 6
        c = c0 - fwd * (0.034 * t) + mathutils.Vector((0, 0, 0.006 * t * t))
        rings.append((c, mathutils.Vector((0, 0, 1)), side, (lambda ang, t=t: 0.0095 - 0.0025 * t + 0.0015 * math.sin(ang * 3)), t))
    crown = swept(f"{name}_crown", rings, m["banana_crown"], sides=14)
    crown.parent = root
    crown.matrix_parent_inverse = root.matrix_world.inverted()
    return root


def fruit_plate(name, x, y, z, heading_deg, count=4, seed=0):
    """A blue-and-white plate with a hand of bananas on it, both turned and modelled here
    (the library's carved plate came out torn and its bananas plastic)."""
    plate = [(0.0, 0.0035), (0.044, 0.0035), (0.046, 0.0), (0.056, 0.0), (0.058, 0.004), (0.086, 0.011), (0.107, 0.0175),
             (0.11, 0.0195), (0.1095, 0.0215), (0.106, 0.0215), (0.084, 0.0135), (0.068, 0.0085), (0.066, 0.0078), (0.0, 0.0076)]
    if "plate_glaze" not in m:
        m["plate_glaze"] = radial_ware_material("plate_glaze", "plate", 1904, rough=0.12)
    dish = turned(f"{name}_dish", plate, x, y, z, m["plate_glaze"], segments=48)
    top_projected_uvs(dish, x, y, 0.11)
    h = math.radians(heading_deg)
    hand = banana_hand(f"{name}_bananas", (x - 0.052 * math.cos(h), y - 0.052 * math.sin(h), z + 0.0076), heading_deg, count=count, seed=seed)
    settle(hand, max_drop=0.03)
    return dish, hand


def open_journal(cx, cy, z):
    """Sora's diary, open on the blotter where she writes up her day at night: the studio's
    save point (Prologue.ts finds it by name, `save_journal`; it replaces the game's stock
    folio and votive, which stood in the desk's book stack). Worn brown leather boards
    flat on the desk; the page blocks bow up out of the gutter, written in
    (tools/drawings/journal.mjs) down the left-hand page and a third of the right, a
    pencil study under it; a red silk ribbon down the page and over its foot onto the
    blotter, a pencil lying in the gutter. She sits at +x: the head of the page is at -x,
    the spine runs along x."""
    PH, PW, b = 0.215, 0.152, 0.0025
    root = empty("save_journal", area, (cx, cy, z))
    bpy.context.view_layer.update()  # the parts are parented keeping their world place
    leather = plain("M_studio_journal_leather", (0.15, 0.08, 0.042), rough=0.62)
    pages_mat = image_material("M_studio_journal_pages", texture("T_studio_journal_BC"), rough=0.93)
    pages_mat["tile"] = 0.0
    edges = book_materials()[1]
    x0, x1 = cx - PH / 2, cx + PH / 2
    parts = [
        box("save_journal_board_l", area, x0 - 0.004, x1 + 0.004, cy - PW - 0.007, cy - 0.005, z, z + b, leather, edge=0.0008),
        box("save_journal_board_r", area, x0 - 0.004, x1 + 0.004, cy + 0.005, cy + PW + 0.007, z, z + b, leather, edge=0.0008),
        box("save_journal_spine", area, x0 - 0.004, x1 + 0.004, cy - 0.007, cy + 0.007, z, z + 0.002, leather, edge=0.0006),
    ]

    def top(w, th):
        # Down into the gutter, where the two blocks meet; bowed up beside it.
        return z + b + th * (0.3 + 0.7 * min(1.0, w / 0.01)) + 0.008 * (1 - math.exp(-w / 0.016)) * (1 - 0.5 * w / PW)

    ws = [0.0, 0.002, 0.005, 0.009, 0.014, 0.02, 0.03, 0.045, 0.065, 0.09, 0.115, 0.135, PW - 0.003, PW - 0.0005]
    xs = list(np.linspace(x0 + 0.0015, x1 - 0.0015, 10))
    for s, th, tag in ((-1, 0.0068, "l"), (1, 0.0052, "r")):
        y_of = lambda w: cy + s * (0.0003 + w)  # noqa: E731
        # The page surface: a grid, its UVs the page's place in the spread.
        verts, faces, uvs = [], [], []
        for w in ws:
            for x in xs:
                verts.append((x, y_of(w), top(w, th) - (0.0006 if w >= PW - 0.001 else 0.0)))
        nx = len(xs)
        for i in range(len(ws) - 1):
            for j in range(nx - 1):
                a, bq, c, d = i * nx + j, i * nx + j + 1, (i + 1) * nx + j + 1, (i + 1) * nx + j
                pa, pb, pd = (mathutils.Vector(verts[k]) for k in (a, bq, d))
                face = (a, bq, c, d) if (pb - pa).cross(pd - pa).z >= 0 else (a, d, c, bq)
                faces.append(face)
                for k in face:
                    w = ws[k // nx]
                    x = xs[k % nx]
                    uvs.append((0.5 + s * 0.5 * min(1.0, w / PW), (x1 - x) / (x1 - x0)))
        parts.append(mesh_object(f"save_journal_pages_{tag}", area, verts, faces, pages_mat, uvs=uvs, smooth=True))
        # The edges of the page block: head, foot and fore-edge, down to the board.
        verts, faces = [], []
        for pts, out in (([(x0 + 0.0015, y_of(w), top(w, th)) for w in ws], (-1, 0, 0)),
                         ([(x1 - 0.0015, y_of(w), top(w, th)) for w in ws], (1, 0, 0)),
                         ([(x, y_of(PW - 0.0005), top(PW - 0.0005, th) - 0.0006) for x in xs], (0, s, 0))):
            base = len(verts)
            for p in pts:
                verts += [p, (p[0], p[1], z + b)]
            for k in range(len(pts) - 1):
                a, bq, c, d = base + 2 * k, base + 2 * k + 2, base + 2 * k + 3, base + 2 * k + 1
                pa, pb, pd = (mathutils.Vector(verts[i]) for i in (a, bq, d))
                faces.append((a, bq, c, d) if (pb - pa).cross(pd - pa).dot(mathutils.Vector(out)) >= 0 else (a, d, c, bq))
        parts.append(mesh_object(f"save_journal_edges_{tag}", area, verts, faces, edges))

    # The ribbon: out of the head of the spine, down the right-hand page by the gutter,
    # over the foot of the page and the board, and onto the blotter.
    th_r = 0.0052
    on_page = lambda x, w, dz=0.0005: (x, cy + 0.0003 + w, top(w, th_r) + dz)  # noqa: E731
    pts = [on_page(x0 + 0.003, 0.004), on_page(cx, 0.0045), on_page(x1 - 0.006, 0.005), on_page(x1 - 0.0024, 0.0052, 0.0001),
           on_page(x1 - 0.0009, 0.0054, -0.0016), (x1 - 0.0009, cy + 0.0059, z + b + 0.0012), (x1 + 0.0006, cy + 0.0061, z + b + 0.0005),
           (x1 + 0.0034, cy + 0.0063, z + b + 0.0005), (x1 + 0.0047, cy + 0.0065, z + b - 0.0006), (x1 + 0.0054, cy + 0.0067, z + 0.0006),
           (x1 + 0.009, cy + 0.0072, z + 0.0005), (x1 + 0.025, cy + 0.0105, z + 0.0005), (x1 + 0.041, cy + 0.009, z + 0.0005)]
    verts, faces, uvs = [], [], []
    total = 0.0
    for k, p in enumerate(pts):
        a = mathutils.Vector(pts[max(0, k - 1)])
        c = mathutils.Vector(pts[min(len(pts) - 1, k + 1)])
        t = (c - a).normalized()
        side = mathutils.Vector((0, 0.003, 0))  # flat across the page, whichever way the ribbon runs
        if k:
            total += (mathutils.Vector(p) - mathutils.Vector(pts[k - 1])).length
        verts += [tuple(mathutils.Vector(p) - side), tuple(mathutils.Vector(p) + side)]
        if k:
            i = 2 * k
            pa, pb, pd = (mathutils.Vector(verts[j]) for j in (i - 2, i - 1, i))
            face = (i - 2, i - 1, i + 1, i) if (pb - pa).cross(pd - pa).z >= 0 else (i - 2, i, i + 1, i - 1)
            faces.append(face)
    silk = plain("M_studio_journal_ribbon", (0.4, 0.045, 0.04), rough=0.4)
    silk.use_backface_culling = False
    parts.append(mesh_object("save_journal_ribbon", area, verts, faces, silk))
    # A pencil in the gutter, its end sharpened with a knife.
    a = mathutils.Vector((x0 + 0.032, cy - 0.0008, z + 0.0092))
    e = mathutils.Vector((x1 - 0.022, cy + 0.0012, z + 0.0092))
    d = (e - a).normalized()
    nrm = mathutils.Vector((0, 0, 1))
    bin_ = d.cross(nrm).normalized()
    hexa = lambda ang: 0.0034 / math.cos(((ang + 0.26) % (math.tau / 6)) - math.pi / 6)  # noqa: E731
    body = [(a + d * (t * (e - a).length), nrm, bin_, hexa, t) for t in (0.0, 0.5, 1.0)]
    parts.append(swept("save_journal_pencil", body, plain("M_studio_pencil_varnish", (0.34, 0.11, 0.05), rough=0.35), sides=6))
    cone = [(e + d * (0.016 * t), nrm, bin_, (lambda ang, t=t: 0.0033 * (1 - t) + 0.0007 * t), t) for t in (0.0, 0.5, 1.0)]
    parts.append(swept("save_journal_pencil_wood", cone, plain("M_studio_pencil_wood", (0.62, 0.45, 0.28), rough=0.8), sides=10))
    lead = [(e + d * (0.016 + 0.004 * t), nrm, bin_, (lambda ang, t=t: 0.0007 * (1 - t) + 0.0001), t) for t in (0.0, 1.0)]
    parts.append(swept("save_journal_pencil_lead", lead, plain("M_studio_graphite", (0.08, 0.08, 0.085), rough=0.35, metal=0.3), sides=8))
    for part in parts:
        part.parent = root
        part.matrix_parent_inverse = root.matrix_world.inverted()
    return root


def chamberstick(x, y, z):
    """An enamelled iron chamberstick by the diary: white with a navy rim, chipped, a ring
    handle; in it a candle burnt down a third, a crater round the wick and wax run down
    its side and pooled in the dish. The flame is the game's (Studio.ts, `desk_candle`)."""
    if "enamel_ware" not in m:
        m["enamel_ware"] = radial_ware_material("enamel_ware", "enamel", 1931, rough=0.22)
    dish = [(0.0, 0.0), (0.052, 0.0), (0.056, 0.002), (0.06, 0.012), (0.0625, 0.0145), (0.061, 0.0155), (0.058, 0.014),
            (0.054, 0.0045), (0.05, 0.0035), (0.0, 0.0035)]
    socket = [(0.0, 0.0035), (0.019, 0.0035), (0.017, 0.008), (0.0155, 0.035), (0.018, 0.038), (0.0185, 0.041), (0.0125, 0.041),
              (0.0125, 0.012), (0.0, 0.012)]
    parts = [turned("desk_candlestick_dish", dish, x, y, z, m["enamel_ware"], segments=40),
             turned("desk_candlestick_socket", socket, x, y, z, m["enamel_ware"], segments=28)]
    for p in parts:
        top_projected_uvs(p, x, y, 0.0625)
    navy = plain("M_studio_enamel_navy", (0.05, 0.07, 0.18), rough=0.3)
    # The ring handle, in the upright plane through the dish's centre, its inner side in the rim.
    hc = mathutils.Vector((x, y - 0.0755, z + 0.013))
    ring = [(hc + mathutils.Vector((0, 0.0135 * math.cos(a), 0.0135 * math.sin(a))), mathutils.Vector((0, math.cos(a), math.sin(a))),
             mathutils.Vector((1, 0, 0)), (lambda ang: 0.0033), a / math.tau) for a in np.linspace(0, math.tau, 33)]
    parts.append(swept("desk_candlestick_handle", ring, navy, sides=10, cap_start=False, cap_end=False))
    wax = m["candle"]
    parts.append(turned("desk_candle_wax", [(0.0, 0.012), (0.0119, 0.012), (0.0119, 0.086), (0.0118, 0.0885), (0.0113, 0.0915), (0.0096, 0.0905),
                                            (0.004, 0.0884), (0.0, 0.0879)], x, y, z, wax, segments=24))
    for k, (ang, length) in enumerate(((0.6, 0.022), (2.5, 0.034), (4.4, 0.014))):
        rings = []
        for i in range(7):
            t = i / 6
            c = mathutils.Vector((x + 0.0117 * math.cos(ang), y + 0.0117 * math.sin(ang), z + 0.0905 - length * t))
            out = mathutils.Vector((math.cos(ang), math.sin(ang), 0))
            rings.append((c, out, out.cross(mathutils.Vector((0, 0, 1))), (lambda a_, t=t: 0.0013 + 0.0011 * t * t), t))
        parts.append(swept(f"desk_candle_drip_{k}", rings, wax, sides=8))
    parts.append(turned("desk_candle_wax_pool", [(0.0, 0.0033), (0.0085, 0.0033), (0.008, 0.0046), (0.0, 0.0049)], x + 0.028, y + 0.014, z, wax, segments=14))
    parts.append(tube("desk_candle_wick", area, [(x, y, z + 0.0879), (x + 0.0006, y, z + 0.093), (x + 0.0022, y + 0.0004, z + 0.0965)],
                      0.0007, plain("M_studio_wick", (0.03, 0.025, 0.02), rough=0.9), sides=5))
    empty("light_flame_desk_candle", area, (x + 0.0016, y + 0.0003, z + 0.1045), radius=1.6, intensity=0.3)
    return parts


def rice_material():
    """Cooked rice, grain by grain: pale, slightly translucent-looking grains packed close."""
    n = 256
    rgen = np.random.default_rng(7)
    img_a = np.full((n, n, 4), (0.62, 0.6, 0.53, 1.0), dtype=np.float32)
    yy, xx = np.mgrid[:n, :n]
    for _ in range(900):
        cx, cy, ang = rgen.uniform(0, n), rgen.uniform(0, n), rgen.uniform(0, math.pi)
        dx, dy = (xx - cx + n / 2) % n - n / 2, (yy - cy + n / 2) % n - n / 2
        u = dx * math.cos(ang) + dy * math.sin(ang)
        v = -dx * math.sin(ang) + dy * math.cos(ang)
        g = (u / 5.5) ** 2 + (v / 2.4) ** 2
        mask = g < 1
        shade = rgen.uniform(0.82, 0.92)
        img_a[mask, :3] = np.array((shade, shade * 0.98, shade * 0.9)) * (1 - 0.18 * g[mask, None])
    img = bpy.data.images.new("T_studio_cooked_rice_BC", width=n, height=n, alpha=False)
    img.pixels.foreach_set(img_a.ravel())
    img.filepath_raw = os.path.join(TEXTURES, "T_studio_cooked_rice_BC.png")
    img.file_format = "PNG"
    img.save()
    mat = image_material("M_studio_cooked_rice", img.filepath_raw, rough=0.7)
    mat["tile"] = 0.0
    return mat


def wire_mesh_material():
    """Fine woven wire for the food cover: the wires opaque dark iron, the gaps almost
    clear (alpha blended), one tile a metre (the cover's UVs are in metres)."""
    n = 512
    yy, xx = np.mgrid[:n, :n]
    wire = ((xx % 8) < 2) | ((yy % 8) < 2)
    rgba = np.empty((n, n, 4), dtype=np.float32)
    rgba[:, :, :3] = (0.06, 0.06, 0.055)
    rgba[:, :, 3] = np.where(wire, 0.95, 0.06)
    img = bpy.data.images.new("T_studio_wire_mesh_BC", width=n, height=n, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(TEXTURES, "T_studio_wire_mesh_BC.png")
    img.file_format = "PNG"
    img.save()
    mat = plain("M_studio_wire_cover", (0.06, 0.06, 0.055), rough=0.5, metal=0.4, alpha=0.5)
    mat.use_backface_culling = False
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    bsdf = nodes.get("Principled BSDF")
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    return mat


def screw_eye(name, at, out):
    """A screw eye in the wall, its ring at `at` (where a line is tied), its shank back to
    the plaster along -`out`."""
    o = np.array(out, float)
    p = np.array(at, float)
    tube(f"{name}_shank", area, [tuple(p - o * 0.03), tuple(p - o * 0.004)], 0.0018, m["iron"], sides=5)
    ring = [tuple(p + (o * math.cos(a) + np.array((0, 0, 1)) * math.sin(a)) * 0.006) for a in np.linspace(0, math.tau, 13)]
    tube(f"{name}_ring", area, ring, 0.0015, m["iron"], sides=5)


def settle(prop, max_drop=0.15):
    """Lowers a placed prop straight down until it rests on whatever is under it (the
    floor, a brazier's rim, a pile of firewood), so nothing hangs a few centimetres up."""
    from mathutils.bvhtree import BVHTree
    bpy.context.view_layer.update()
    own = {prop, *prop.children_recursive}
    pts = np.array([tuple(o.matrix_world @ v.co) for o in own if o.type == "MESH" for v in o.data.vertices])
    lo, hi = pts.min(0), pts.max(0)
    low = pts[pts[:, 2] < lo[2] + 0.015]
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for o in area.all_objects:
        if o in own or o.type != "MESH" or o.name.startswith("col_"):
            continue
        b = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        if (max(p.x for p in b) < lo[0] - 0.02 or min(p.x for p in b) > hi[0] + 0.02 or max(p.y for p in b) < lo[1] - 0.02
                or min(p.y for p in b) > hi[1] + 0.02 or min(p.z for p in b) > hi[2]):
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        base = len(verts)
        verts += [o.matrix_world @ v.co for v in me.vertices]
        polys += [[base + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    if not polys:
        return
    tree = BVHTree.FromPolygons(verts, polys)
    drops = []
    for p in low[:: max(1, len(low) // 300)]:
        hit = tree.ray_cast(mathutils.Vector(p) + mathutils.Vector((0, 0, 0.002)), mathutils.Vector((0, 0, -1)), max_drop)
        if hit[0] is not None:
            drops.append(hit[3] - 0.002)
    if drops:
        prop.location.z -= max(0.0, min(drops))
        print(f"settled {prop.name} down {max(0.0, min(drops)) * 100:.1f} cm")


def hang_from_pegs(prop, name, wall_x=W - 0.012):
    """Hangs a scanned prop by its ropes from the east wall: finds where each rope ends
    at the top of the scan and drives a wooden peg into the wall there, the rope looped
    over it. (Nails set at a guessed height left the ropes ending in mid-air.)"""
    bpy.context.view_layer.update()
    pts = np.array([tuple(o.matrix_world @ v.co) for o in prop.children_recursive if o.type == "MESH" for v in o.data.vertices])
    top = pts[:, 2].max()
    tips = pts[pts[:, 2] > top - 0.06]
    # Two ropes: split the top points at the widest gap along the wall.
    order = np.sort(tips[:, 1])
    cut = order[np.argmax(np.diff(order))] if len(order) > 1 else order[0]
    for k, group in enumerate((tips[tips[:, 1] <= cut], tips[tips[:, 1] > cut])):
        if not len(group):
            continue
        tip = group[np.argmax(group[:, 2])]
        x, y, z = (float(v) for v in tip)
        peg_z = z - 0.012
        tube(f"{name}_peg_{k}", area, [(wall_x, y, peg_z), (min(x, wall_x) - 0.022, y, peg_z + 0.006)], 0.0085, m["worn"], sides=10, radius_end=0.011)
        loop = [(x, y + 0.016 * math.cos(a), peg_z + 0.016 * math.sin(a)) for a in np.linspace(math.pi + 0.35, -0.35, 14)]
        loop = [(x, y - 0.015, peg_z - 0.035)] + loop + [(x, y + 0.015, peg_z - 0.035)]
        tube(f"{name}_rope_loop_{k}", area, loop, 0.0045, m["cord"], sides=6)


def crack_decal(name, at, normal, up, size, variant, flip=False):
    """A crack in the plaster: a quad 1.5 mm off the wall showing one crack of the
    T_studio_cracks_BC atlas (tools/drawings/cracks.mjs: a jagged tapering line with
    branches, chipped paint and grime along it), blended over the wall. `at` is the
    crack's centre on the wall face, `up` the direction it runs, `size` (w, h) metres."""
    n = np.array(normal, float); n /= np.linalg.norm(n)
    u = np.array(up, float); u -= n * np.dot(u, n); u /= np.linalg.norm(u)
    r = np.cross(u, n)  # r x u = n: the quad faces out of the wall
    c = np.array(at, float) + n * 0.0015
    w, h = size
    corners = [c - r * w / 2 - u * h / 2, c + r * w / 2 - u * h / 2, c + r * w / 2 + u * h / 2, c - r * w / 2 + u * h / 2]
    cols, rows = CRACK_GRID
    col, row = variant % cols, variant // cols
    u0, u1 = col / cols, (col + 1) / cols
    v0, v1 = 1 - (row + 1) / rows, 1 - row / rows
    if flip:  # mirrored, so the same crack can run the other way
        u0, u1 = u1, u0
    uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    return mesh_object(name, area, [tuple(p) for p in corners], [(0, 1, 2, 3)], m["cracks"], uvs=uvs)


def hall():
    """The middle of the house: the hall between the studio and the back room, where the
    household cooks, eats and dries its washing in the rains, and where the stairs go
    down. Old: limewash flaking to the render, cracks from the door heads, soot over the
    brazier, a ceiling stain with a tin catching the drip, cobwebs in the high corners."""
    y0, y1 = AIR
    room_walls("hall", 0, W, y0, y1, "wen", gaps=[("n", P2_DOOR[0] - 0.05, P2_DOOR[1] + 0.05, 2.28)])
    # Picture rail and the old electric run along the walls.
    box("hall_picture_rail_w", area, 0, 0.025, y0, y1, 2.45, 2.49, m["wood"], edge=0.003)
    box("hall_picture_rail_e", area, W - 0.025, W, y0, STAIR[2], 2.45, 2.49, m["wood"], edge=0.003)

    # ---- Age: cracks, a brick patch, soot, a stained ceiling and a drip.
    box("hall_brick_patch", area, W - 0.016, W - 0.0125, 6.35, 6.75, 0.18, 0.45, m["brick"])
    # Settlement cracks (decals, see crack_decal): up from the back-room door's head to the
    # ceiling, high on the west wall, and up the dado from the old brick patch.
    crack_decal("hall_crack_door_head", (1.36, y1 - 0.012, 2.82), (0, -1, 0), (0.42, 0, 1), (0.55, 1.1), 0)
    crack_decal("hall_crack_w", (0.012, 8.78, 2.98), (1, 0, 0), (0, -0.2, 1), (0.42, 0.85), 1)
    crack_decal("hall_crack_e", (W - 0.012, 6.9, 0.78), (-1, 0, 0), (0, 0.12, 1), (0.36, 0.72), 2)

    # The roof leaks over the east of the hall; a rusty basin catches the drip. The soot over
    # the fire and the leak's stain are in the bake (MARKS in bake_studio_lightmap.py).
    dx_, dy_ = 3.05, 7.4
    basin = [(0.0, 0.0), (0.13, 0.0), (0.17, 0.08), (0.165, 0.09), (0.0, 0.085)]
    turned("hall_drip_basin", basin, dx_, dy_, 0.0, m["rust"], segments=24)
    # Water to 5 cm, meeting the basin's flared wall all round.
    cylinder("hall_drip_water", area, dx_, dy_, 0.004, 0.05, 0.1525, m["water"], verts=24)
    collider("hall_drip_basin", area, dx_ - 0.17, dx_ + 0.17, dy_ - 0.17, dy_ + 0.17, 0, 0.1)

    # ---- The dining table under the hanging lamp: scanned furniture and kitchenware.
    tx, ty = 2.1, 7.95
    lib("wooden_table_02", (tx, ty, 0), 0, name="hall_table", budget=2000)
    top = surface_z(tx, ty, 1.2)
    box("hall_table_mat", area, tx - 0.36, tx + 0.36, ty - 0.24, ty + 0.24, top, top + 0.004, m["mat"], edge=0.002)
    top += 0.004
    # The food cover: woven wire on a cane hoop, a turned wooden knob; the bowl under it
    # shows through the mesh. Its UVs in metres round and up, so the weave keeps its size.
    fx, fy = tx + 0.12, ty + 0.04
    dome = [(0.2 * math.cos(t), 0.205 * math.sin(t)) for t in np.linspace(0, math.pi / 2 - 0.06, 14)] + [(0.0, 0.207)]
    cover = turned("hall_food_cover", dome, fx, fy, top + 0.006, wire_mesh_material(), segments=40)
    for loop in cover.data.uv_layers[0].data:
        loop.uv[0] *= 2 * math.pi * 0.2
    hoop = [(fx + 0.203 * math.cos(a), fy + 0.203 * math.sin(a), top + 0.006) for a in np.linspace(0, math.tau, 41)]
    tube("hall_food_cover_hoop", area, hoop, 0.006, m["bamboo"], sides=8)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        rib = [(fx + 0.2025 * math.cos(t) * math.cos(a), fy + 0.2025 * math.cos(t) * math.sin(a), top + 0.006 + 0.2075 * math.sin(t)) for t in np.linspace(0, math.pi / 2, 12)]
        tube(f"hall_food_cover_rib_{k}", area, rib, 0.0022, m["bamboo"], sides=5)
    turned("hall_food_cover_knob", [(0.0, 0.0), (0.014, 0.0), (0.009, 0.012), (0.013, 0.024), (0.0, 0.03)], fx, fy, top + 0.208, m["worn"], segments=12)
    lib("wooden_bowl_02", (tx + 0.12, ty + 0.04, top), 0, name="hall_bowl_under_cover", collide=False, budget=600)
    lib("ceramic_pot", (tx - 0.22, ty + 0.06, top), 25, name="hall_rice_pot", collide=False, scale=0.42, budget=1500)
    # Rice bowls: a foot ring, a thin flared wall, a flat inside; cold rice left in them.
    bowl = [(0.026, 0.0), (0.028, 0.0), (0.028, 0.007), (0.038, 0.014), (0.05, 0.034), (0.057, 0.058), (0.054, 0.059),
            (0.047, 0.04), (0.035, 0.022), (0.02, 0.013), (0.0, 0.012)]
    rice = rice_material()
    for k, (bx, by) in enumerate(((tx - 0.3, ty - 0.2), (tx + 0.02, ty - 0.22))):
        turned(f"hall_rice_bowl_{k}", [(0.0, 0.006)] + bowl, bx, by, top, m["porcelain"], segments=28)
        # From where it meets the bowl's wall up to its crown.
        mound = [(0.046, 0.04), (0.038, 0.047), (0.027, 0.052 + 0.002 * k), (0.013, 0.055 + 0.003 * k), (0.0, 0.056 + 0.003 * k)]
        heap = turned(f"hall_rice_{k}", mound, bx, by, top, rice, segments=24)
        # Projected from above (one 14 cm tile, grains about 6 mm), so they lie evenly
        # instead of swirling round the crown.
        for poly in heap.data.polygons:
            for li, vi in zip(poly.loop_indices, poly.vertices):
                co = heap.data.vertices[vi].co
                heap.data.uv_layers[0].data[li].uv = (co.x / 0.14, co.y / 0.14)
        band = [(bx + 0.0555 * math.cos(a), by + 0.0555 * math.sin(a), top + 0.054) for a in np.linspace(0, math.tau, 41)]
        tube(f"hall_rice_bowl_band_{k}", area, band, 0.0012, plain("M_studio_bowl_blue", (0.08, 0.13, 0.36), rough=0.2), sides=4)
        # Weld the turned shape's seam first, or each side of it gets its own lumps (a crack).
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(heap.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bm.to_mesh(heap.data)
        bm.free()
        for v in heap.data.vertices:  # cooked rice is lumpy, not turned smooth
            v.co.z += float(rng.normal(0, 0.0012)) * (v.co.z > top + 0.025)
        for e in (-1, 1):
            tube(f"hall_chopstick_{k}_{e}", area, [(bx + 0.078 + e * 0.006, by - 0.1, top + 0.0028), (bx + 0.082 + e * 0.009, by + 0.12, top + 0.0022)], 0.0028, m["worn"], sides=6, radius_end=0.0018)
    # A blue-and-white plate with a hand of bananas on it (the limes and lychees read as
    # painted balls; the library's carved plate came out torn, its bananas plastic).
    fruit_plate("hall_fruit_plate", tx + 0.4, ty - 0.12, top, 35, count=4, seed=3)
    for k, (sx_, sy_, rot, mid, sc) in enumerate(((tx - 0.3, ty - 0.50, 10, "wooden_stool_01", 1.0), (tx + 0.32, ty - 0.50, 35, "painted_wooden_stool", 1.0),
                                                   (tx + 0.88, ty + 0.03, 80, "chinese_stool", 0.85))):
        lib(mid, (sx_, sy_, 0), rot, name=f"hall_stool_{k}", scale=sc, budget=2000)

    # ---- The hanging lamp over the table: an enamelled steel shade on its rod, the hall's light.
    lamp = lib("hanging_industrial_lamp", (tx, ty, H), 0, name="hall_lamp", collide=False, scale=0.6, budget=2500)
    bpy.context.view_layer.update()
    # The bulb is the faces with the glass material; the baked light sits just under it,
    # inside the shade's mouth (a light inside the glass would be lost in the bake).
    glass = []
    for o in lamp.children_recursive:
        if o.type != "MESH":
            continue
        slots = [i for i, sl in enumerate(o.material_slots) if sl.material and "glass" in sl.material.name.lower()]
        for poly in o.data.polygons:
            if poly.material_index in slots:
                glass += [o.matrix_world @ o.data.vertices[i].co for i in poly.vertices]
    bz = min(p.z for p in glass) if glass else 2.62
    empty("marker_airwell_bulb", area, (tx, ty, bz - 0.025))
    # Hall lamp is now wired cleanly from `hall_switch` on the south partition (below), keeping
    # the west doorway swing zone 100% clear of boxy plates or loose runs.

    # ---- The food safe against the back wall: screened doors, legs standing in tins of
    # water against the ants. A scanned cupboard stands in for it when it is there.
    fx0, fx1, fy1 = 1.45, 2.3, y1 - 0.0125
    fy0 = fy1 - 0.4
    for e, x in (("w", fx0), ("e", fx1 - 0.04)):
        for yy in (fy0, fy1 - 0.04):
            box(f"food_safe_post_{e}_{yy:.2f}", area, x, x + 0.04, yy, yy + 0.04, 0.12, 1.55, m["planks"], edge=0.004)
            turned(f"food_safe_ant_tin_{e}_{yy:.2f}", [(0.0, 0.0), (0.04, 0.0), (0.042, 0.06), (0.038, 0.06), (0.0, 0.004)], x + 0.02, yy + 0.02, 0.0, m["rust"], segments=14)
            box(f"food_safe_ant_water_{e}_{yy:.2f}", area, x - 0.012, x + 0.052, yy - 0.012, yy + 0.052, 0.05, 0.052, m["water"])
    for z in (0.12, 0.62, 1.1, 1.52):
        box(f"food_safe_shelf_{z}", area, fx0 + 0.04, fx1 - 0.04, fy0 + 0.02, fy1 - 0.02, z, z + 0.025, m["planks"])
    box("food_safe_top", area, fx0 - 0.02, fx1 + 0.02, fy0 - 0.02, fy1, 1.55, 1.59, m["planks"], edge=0.006)
    box("food_safe_back", area, fx0, fx1, fy1 - 0.01, fy1, 0.12, 1.55, m["planks"])
    for e, (a, b) in (("w", (fx0 + 0.04, (fx0 + fx1) / 2)), ("e", ((fx0 + fx1) / 2, fx1 - 0.04))):
        for nm, (u0, u1, z0, z1) in (("l", (a, a + 0.03, 0.15, 1.52)), ("r", (b - 0.03, b, 0.15, 1.52)), ("b", (a, b, 0.15, 0.2)), ("t", (a, b, 1.47, 1.52)), ("m", (a, b, 0.6, 0.65))):
            box(f"food_safe_door_{e}_{nm}", area, u0, u1, fy0 - 0.02, fy0, z0, z1, m["planks"], edge=0.003)
        for z0, z1 in ((0.2, 0.6), (0.65, 1.47)):
            box(f"food_safe_screen_{e}_{z0}", area, a + 0.03, b - 0.03, fy0 - 0.012, fy0 - 0.008, z0, z1, m["mesh_cover"])
        box(f"food_safe_turnbuckle_{e}", area, b - 0.045 if e == "w" else a + 0.015, b - 0.015 if e == "w" else a + 0.045, fy0 - 0.03, fy0 - 0.02, 0.98, 1.0, m["brass"])
    collider("food_safe", area, fx0 - 0.02, fx1 + 0.02, fy0 - 0.03, fy1, 0, 1.6)
    # Behind the screens: crocks, a brass pot, the oil tin; bananas and a crock on top.
    for k, (mid, xx, z, sc, rot) in enumerate((("ceramic_pot", fx0 + 0.22, 1.125, 0.38, 20), ("brass_pot_01", fx0 + 0.6, 1.125, 0.5, 0),
                                               ("oil_tin", fx0 + 0.25, 0.645, 0.9, 40), ("jug_01", fx0 + 0.6, 0.645, 0.75, 200),
                                               ("wooden_bowl_02", fx0 + 0.25, 0.145, 1.0, 0), ("ceramic_pot", fx0 + 0.6, 0.145, 0.4, 70))):
        lib(mid, (xx, fy0 + 0.2, z), rot, name=f"food_safe_store_{k}", collide=False, scale=sc, budget=900)
    settle(banana_hand("food_safe_bananas", (fx0 + 0.3, fy0 + 0.2, 1.59), 20, count=5, seed=7), max_drop=0.05)
    lib("ceramic_pot", (fx0 + 0.66, fy0 + 0.2, 1.59), 160, name="food_safe_top_crock", collide=False, scale=0.4, budget=900)

    # ---- The big glazed water jar in the corner by the stairs, its lid half off, a dipper;
    # a smaller jar beside it.
    jx, jy = 2.95, y1 - 0.38
    # A Martaban storage jar, not the scan (its texture broke up like crumpled foil): thrown
    # stoneware in a dark brown glaze that stops above the bare clay foot, four lug handles
    # on the shoulder, a rolled rim; the water inside under its lid.
    glaze = jar_glaze_material()
    raw = [(0.0, 0.0), (0.15, 0.0), (0.162, 0.014), (0.2, 0.058), (0.236, 0.108)]
    body = [(0.236, 0.108), (0.262, 0.16), (0.292, 0.29), (0.3, 0.38), (0.287, 0.47), (0.245, 0.57), (0.18, 0.64), (0.135, 0.675),
            (0.126, 0.695), (0.13, 0.712), (0.142, 0.726), (0.138, 0.742), (0.122, 0.746), (0.112, 0.735), (0.108, 0.7), (0.0, 0.69)]
    turned("hall_water_jar_foot", raw, jx, jy, 0.0, m["terracotta"], segments=48)
    jar = turned("hall_water_jar", body, jx, jy, 0.0, glaze, segments=48)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        c, s_ = math.cos(a), math.sin(a)
        lug = [(jx + c * (0.242 + 0.022 * math.sin(t)), jy + s_ * (0.242 + 0.022 * math.sin(t)), 0.575 + 0.03 * math.cos(t)) for t in np.linspace(-0.3, math.pi + 0.3, 11)]
        tube(f"hall_water_jar_lug_{k}", area, lug, 0.0075, glaze, sides=8)
    # The mouth as the scan really has it: its rim height, centre and radius.
    mouth_c, mouth_r, rim = (jx, jy), 0.165, 0.73
    if jar is not None:
        pts = mesh_points(jar)
        rim = float(pts[:, 2].max())
        lip = pts[pts[:, 2] > rim - 0.012]
        mouth_c = (float(lip[:, 0].mean()), float(lip[:, 1].mean()))
        mouth_r = float(np.median(np.hypot(lip[:, 0] - mouth_c[0], lip[:, 1] - mouth_c[1])))
    cylinder("hall_water_jar_water", area, mouth_c[0], mouth_c[1], rim - 0.06, rim - 0.058, mouth_r - 0.02, m["water"], verts=24)
    # A plank lid lying flat on the rim, pushed a little aside; two battens across it.
    lr = mouth_r + 0.035
    lx_, ly_ = mouth_c[0] - 0.02, mouth_c[1] + 0.015
    turned("hall_jar_lid", [(0.0, 0.0), (lr, 0.0), (lr, 0.018), (0.0, 0.018)], lx_, ly_, rim, m["planks"], segments=28)
    for k, off in enumerate((-0.45, 0.45)):
        box(f"hall_jar_lid_batten_{k}", area, lx_ - lr * 0.8, lx_ + lr * 0.8, ly_ + off * lr - 0.014, ly_ + off * lr + 0.014, rim + 0.018, rim + 0.03, m["planks"], edge=0.002)
    # The dipper left on the lid: half a coconut shell, rough and dark outside, its long
    # bamboo handle pushed through the rim and lying across the lid past its edge.
    top_lid = rim + 0.018
    shell = plain("M_studio_coconut_shell", (0.1, 0.06, 0.03), rough=0.9)
    dxp, dyp = lx_ - 0.05, ly_ - 0.03
    cup = turned("hall_dipper_shell", [(0.0, 0.0), (0.03, 0.002), (0.055, 0.018), (0.064, 0.04), (0.061, 0.045), (0.054, 0.028), (0.0, 0.012)],
                 dxp, dyp, top_lid, shell, segments=20)
    for v in cup.data.vertices:  # a shell is never truly round
        v.co.x += float(rng.normal(0, 0.0012))
        v.co.y += float(rng.normal(0, 0.0012))
    stick = plain("M_studio_dipper_bamboo", (0.42, 0.32, 0.16), rough=0.6)
    d = np.array((math.cos(0.5), math.sin(0.5), 0.0))
    start = np.array((dxp, dyp, top_lid + 0.034)) - d * 0.03
    tube("hall_dipper_handle", area, [tuple(start), tuple(np.array((dxp, dyp, top_lid + 0.034)) + d * 0.064), tuple(np.array((dxp, dyp, top_lid + 0.0115)) + d * 0.36)],
         0.0075, stick, sides=8)
    collider("hall_water_jar", area, jx - 0.3, jx + 0.3, jy - 0.3, jy + 0.3, 0, rim + 0.02)
    scan("jar_handles", (jx + 0.1, jy - 0.58, 0.0), 200, name="hall_small_jar")

    # ---- Rice chest tucked cleanly against the east wall south of the stairs (leaves BOTH the
    # west partition-door swing zone AND the entire 1.08 m south hall walkway to the telephone,
    # lantern, and stair gate 100% open!), with winnowing tray & baskets on the north hall wall!
    lib("wooden_crate_01", (W - 0.24, y0 + 0.36, 0), 90, name="hall_rice_chest", scale=0.76, budget=3000)
    lid_z = surface_z(W - 0.24, y0 + 0.36, 1.0)
    lib("wicker_basket_02", (W - 0.24, y0 + 0.22, lid_z), 100, name="hall_chest_basket", collide=False, scale=0.82, budget=2500)
    for k, (dx, dy) in enumerate(((0.0, 0.0), (0.04, 0.03), (-0.04, 0.04), (0.02, -0.04))):
        lib("yellow_onion", (W - 0.24 + dx, y0 + 0.22 + dy, lid_z + 0.02), k * 80, name=f"hall_onion_{k}", collide=False, budget=300)
    lib("sweet_potato", (W - 0.22, y0 + 0.48, lid_z + 0.03), 30, name="hall_sweet_potato_0", collide=False, budget=300)
    lib("sweet_potato", (W - 0.28, y0 + 0.54, lid_z + 0.03), 100, name="hall_sweet_potato_1", collide=False, budget=300)
    # The winnowing tray and two woven baskets hung on nails on the north hall wall above the water jar.
    tray = scan("winnowing_tray", (2.86, y1 - 0.03, 1.98), 0, name="kitchen_winnowing_tray", collide=False)
    if tray is None:
        tray = lib("carved_wooden_plate", (2.86, y1 - 0.03, 1.98), 0, name="kitchen_winnowing_tray", collide=False, scale=1.6, budget=900)
    tray.rotation_euler = (math.pi / 2 - 0.06, 0.0, 0.0)
    hang_on_north_wall(tray, "kitchen_tray", y1 - 0.0125)
    for key, xx, z in (("basket_round", 2.58, 1.40), ("basket_deep", 3.12, 1.36)):
        b = scan(key, (xx, y1 - 0.03, z), 0, name=f"kitchen_hung_{key}", collide=False)
        if b is not None:
            b.rotation_euler = (math.pi / 2 - 0.1, 0.0, 0.0)
            hang_on_north_wall(b, f"kitchen_{key}", y1 - 0.0125)

    # The cooking fire: a clay pot on its clay stove, the cook's low stool in front.
    cx_, cy_ = 0.25, 7.47
    stove = scan("cooking_pot", (cx_, cy_, 0.0), 90, name="kitchen_stove")
    if stove is None:
        prof = [(0.0, 0.0), (0.14, 0.0), (0.16, 0.06), (0.15, 0.2), (0.17, 0.26), (0.13, 0.27), (0.11, 0.22), (0.0, 0.22)]
        turned("kitchen_brazier", prof, cx_, cy_, 0.0, m["terracotta"], segments=24)
        collider("kitchen_brazier", area, cx_ - 0.18, cx_ + 0.18, cy_ - 0.18, cy_ + 0.18, 0, 0.3)
    lib("wooden_stool_02", (cx_ + 0.34, cy_ + 0.02, 0.0), 95, name="kitchen_squat_stool", budget=1200)
    # The brazier for the kettle, and the brass wok hung on the wall over it.
    kx, ky = 0.22, 7.93
    brazier = scan("clay_stove", (kx, ky, 0.0), 40, name="kitchen_kettle_brazier")
    if brazier is not None:
        # The kettle sits down in the bowl's mouth: the rim, not the wire handle over it.
        bpy.context.view_layer.update()
        ring = sorted((o.matrix_world @ v.co).z for o in brazier.children_recursive if o.type == "MESH" for v in o.data.vertices
                      if 0.12 < math.hypot((o.matrix_world @ v.co).x - kx, (o.matrix_world @ v.co).y - ky) < 0.17)
        rim_z = ring[int(len(ring) * 0.8)] if ring else 0.3
        kettle = scan("kettle", (kx, ky, rim_z - 0.03), 115, name="kitchen_kettle", collide=False)
        if kettle is not None:
            settle(kettle)
    wok = lib("brass_pot_02", (0.016, 7.52, 0.92), 0, name="kitchen_wok", collide=False, scale=0.8, budget=1200)
    wok.rotation_euler = (0.0, math.pi / 2, 0.0)
    hang_on_nail(wok, "kitchen_wok")
    # Firewood stacked against the wall, the hatchet on top.
    for k in range(9):
        yy = 8.15 + (k % 3) * 0.048
        zz = 0.025 + (k // 3) * 0.045
        tube(f"kitchen_firewood_{k}", area, [(0.03, yy, zz), (0.4 + 0.03 * (k % 2), yy + 0.012 * ((k % 3) - 1), zz)], 0.021 + 0.004 * (k % 3), m["bark"], sides=7)
    collider("kitchen_firewood", area, 0.0, 0.45, 8.11, 8.3, 0, 0.15)
    hatchet = lib("hatchet", (0.22, 8.2, 0.17), 0, name="kitchen_hatchet", collide=False, budget=800)
    hatchet.rotation_euler = (0.0, math.pi / 2, 0.15)
    settle(hatchet)

    # The painted kitchen shelves, standing against the wall.
    sy = 8.56
    shelves = lib("painted_wooden_shelves", (0.0125, sy, 0.0), 90, name="kitchen_shelves", budget=1200)
    # A narrow corner shelf: one or two things a board, kept clear of its side boards.
    picks = (("oil_tin", 0.0, 20, 0.85), ("ceramic_pot", -0.06, 60, 0.3), ("antique_ceramic_vase_01", 0.08, 0, 0.34))
    levels = sorted({round(surface_z(0.2, sy, z), 3) for z in (0.3, 0.6, 0.9, 1.3)})
    levels = [z for z in levels if 0.05 < z < 1.2]
    for k, (mid, dy, rot, sc) in enumerate(picks):
        if not levels:
            break
        z = levels[min(len(levels) - 1, (0, 1, 1)[k])]
        ware = lib(mid, (0.19, sy + dy, z), rot, name=f"kitchen_shelf_ware_{k}", collide=False, scale=sc, budget=900)
        fits_on(ware, shelves)
    # The cutting board hung on the wall beside the shelves (it used to stick through them).
    board = lib("wooden_cutting_board", (0.03, sy - 0.42, 1.3), 90, name="kitchen_cutting_board", collide=False, budget=600)
    board.rotation_euler = (0.0, math.pi / 2, math.pi / 2)
    hang_on_nail(board, "kitchen_cutting_board")

    # Plank shelves on iron brackets over the fire: glazed jars, crocks, pots, a jug; the
    # spoon hanging.
    for k, z in enumerate((1.3, 1.68)):
        box(f"kitchen_plank_shelf_{k}", area, 0.012, 0.28, 7.2, 8.12, z, z + 0.028, m["planks"], edge=0.004)
        for yy in (7.32, 8.0):
            tube(f"kitchen_bracket_{k}_{yy}", area, [(0.014, yy, z - 0.2), (0.014, yy, z), (0.25, yy, z)], 0.006, m["iron"], sides=4)
            tube(f"kitchen_bracket_brace_{k}_{yy}", area, [(0.014, yy, z - 0.18), (0.2, yy, z - 0.004)], 0.005, m["iron"], sides=4)
    collider("kitchen_plank_shelves", area, 0, 0.28, 7.2, 8.12, 1.1, 1.75)
    for k, (mid, yy, z, sc, rot) in enumerate((("ceramic_pot", 7.36, 1.328, 0.36, 0), ("antique_ceramic_vase_01", 7.98, 1.328, 0.5, 0),
                                               ("brass_pot_01", 7.34, 1.708, 0.5, 0), ("jug_01", 7.62, 1.708, 0.7, 260), ("oil_tin", 7.82, 1.708, 0.85, 10))):
        lib(mid, (0.15, yy, z), rot, name=f"kitchen_store_{k}", collide=False, scale=sc, budget=900)
    scan("jar_plain", (0.15, 8.0, 1.708), 30, name="kitchen_store_glazed_jar", collide=False, scale=0.62)
    scan("jar_handles", (0.15, 7.68, 1.328), 120, name="kitchen_store_handled_jar", collide=False, scale=0.5)
    lib("wooden_spoon", (0.27, 7.86, 1.12), 0, name="kitchen_ladle", collide=False, budget=600).rotation_euler = (math.pi / 2 - 0.05, 0.0, math.pi / 2)

    # The rice sack by the back door, against the wall beside the food safe.
    scan("rice_sack", (1.27, y1 - 0.24, 0.0), 95, name="hall_rice_sack")

    # ---- Washing drying indoors in the rains, on a line across the stairwell: the glow from
    # the floor below comes up behind it.
    a_, b_ = (W - 0.02, 7.15, 2.45), (3.55, y1 - 0.02, 2.45)
    line = sag(a_, b_, 0.06, n=14)
    tube("hall_washing_line", area, line, 0.002, m["string"], sides=4)
    screw_eye("hall_washing_line_eye_e", a_, (-1, 0, 0))
    screw_eye("hall_washing_line_eye_n", b_, (0, -1, 0))
    for name, t, width, drop, mat in (("krama", 0.3, 0.45, 0.85, m["krama"]), ("sampot", 0.62, 0.5, 1.0, m["sampot"])):
        p = line[round(t * (len(line) - 1))]
        d = np.array(b_[:2]) - np.array(a_[:2])
        d /= np.linalg.norm(d)
        obj = draped(f"hall_laundry_{name}", -width / 2, width / 2, 0.0, 0.0, drop, mat)
        obj.location = (p[0], p[1], p[2] + 0.003)
        obj.rotation_euler = (0, 0, math.atan2(d[1], d[0]))

    # ---- Pegs by the door (shifted east of `hall_switch`) with a krama and a cotton cloth; the sleeping mat; the broom.
    box("hall_peg_rail", area, 1.56, 2.01, y0, y0 + 0.02, 1.62, 1.68, m["wood"], edge=0.004)
    for k, x in enumerate((1.64, 1.79, 1.94)):
        tube(f"hall_peg_{k}", area, [(x, y0 + 0.02, 1.65), (x, y0 + 0.09, 1.67)], 0.008, m["wood"], sides=6)
    peg_cloth("hall_peg_krama", (1.94, y0 + 0.075, 1.675), 0.24, 0.62, m["krama"], seed=3)
    peg_cloth("hall_peg_sampot", (1.64, y0 + 0.075, 1.675), 0.22, 0.5, m["sampot"], seed=8)
    mat_roll = scan("straw_mat", (W - 0.13, 6.72, 2.02 - 0.72), 90, name="hall_sleeping_mat", collide=False)
    if mat_roll is None:
        tube("hall_sleeping_mat", area, [(W - 0.12, STAIR[2] - 0.15, 0.04), (W - 0.12, STAIR[2] - 0.15, 0.9)], 0.06, m["mat"], sides=14)
    else:
        hang_from_pegs(mat_roll, "hall_mat")
    # The straw broom, bristles down, leaning beside the stair gate post.
    broom = scan("broom", (W - 0.10, STAIR[2] - 0.14, 0.35), 0, name="hall_broom", collide=False)
    if broom is not None:
        broom.rotation_euler = (0.0, math.radians(72), math.pi)
        settle(broom)

    # ---- Cobwebs in the high corners and over the stairs.
    for k, (corner, u, v, size) in enumerate((((0.0125, y0 + 0.01, H), (1, 0, 0), (0, 1, -0.6), 0.55),
                                                ((W - 0.0125, y1 - 0.0125, H), (-1, 0, 0), (0, -1, -0.5), 0.6),
                                                ((0.0125, y1 - 0.0125, H), (1, 0, 0), (0, -1, -0.7), 0.45),
                                                ((W - 0.0125, STAIR[2] + 0.4, 2.0), (0, 1, 0.4), (-1, 0, -0.3), 0.5))):
        cobweb(f"hall_cobweb_{k}", corner, u, v, size)


    # The stairs down: an opening in the floor, treads descending north into the dark,
    # a turned balustrade on the open side and a child gate at the head (the way out).
    sx0, sx1, sy0, sy1 = STAIR
    rise, going = 0.19, 0.25
    for i in range(int((sy1 - sy0) / going)):
        y = sy0 + i * going
        z = -rise * (i + 1)
        box(f"stair_tread_{i}", area, sx0, sx1, y, y + going + 0.02, z - 0.035, z, m["stair"], edge=0.006)
        box(f"stair_riser_{i}", area, sx0, sx1, y, y + 0.02, z, z + rise - 0.035, m["wood"])
    box("stair_well_wall_west", area, sx0 - 0.04, sx0, sy0, sy1, -3.2, 0, m["limewash"])
    box("stair_well_wall_north", area, sx0, sx1, sy1, sy1 + 0.04, -3.2, 0, m["limewash"])
    box("stair_floor_edge", area, sx0 - 0.06, sx1, sy0 - 0.04, sy0, -0.06, 0.0, m["wood"], edge=0.006)
    box("stair_handrail", area, sx0 - 0.07, sx0 - 0.01, sy0, sy1, 0.92, 0.97, m["teak"], edge=0.01)
    box("stair_bottom_rail", area, sx0 - 0.06, sx0 - 0.02, sy0, sy1, 0.0, 0.06, m["teak"])
    for i in range(int((sy1 - sy0) / 0.13)):
        turned(f"stair_baluster_{i}", [(r * 0.7, z * 1.15) for r, z in BALUSTER], sx0 - 0.04, sy0 + 0.07 + i * 0.13, 0.06, m["teak"], segments=8)
    for y in (sy0, sy1):
        box(f"stair_newel_{y:.2f}", area, sx0 - 0.08, sx0, y - 0.04, y + 0.04, 0, 1.08, m["teak"], edge=0.01)
    collider("stair_balustrade", area, sx0 - 0.08, sx0, sy0, sy1, 0, 1.0)
    collider("stair_well", area, sx0, sx1, sy0 + 0.05, sy1, -0.5, 1.0)
    # The gate: closed until Sora has packed (interact_door, P07), upgraded with turned balusters & brass latch.
    gate = empty("interact_door", area, ((sx0 + sx1) / 2, sy0 - 0.02, 0.5), action="open")
    gate["requires"] = "ep1.kit.collected"
    for nm, a in (("top", (sx0 + 0.02, sx1 - 0.02, 0.86, 0.925)), ("bottom", (sx0 + 0.02, sx1 - 0.02, 0.075, 0.135)),
                  ("stile_w", (sx0 + 0.02, sx0 + 0.075, 0.075, 0.925)), ("stile_e", (sx1 - 0.075, sx1 - 0.02, 0.075, 0.925))):
        attach(box(f"stair_gate_{nm}", area, a[0], a[1], sy0 - 0.038, sy0 - 0.004, a[2], a[3], m["teak"], edge=0.006), gate)
    for i in range(7):
        x = sx0 + 0.13 + i * (sx1 - sx0 - 0.26) / 6
        attach(turned(f"stair_gate_bar_{i}", [(r * 0.65, z * 1.05) for r, z in BALUSTER], x, sy0 - 0.021, 0.13, m["teak"], segments=10), gate)
    for k, z in enumerate((0.24, 0.76)):
        attach(box(f"stair_gate_hinge_{k}", area, sx1 - 0.08, sx1 + 0.01, sy0 - 0.044, sy0 - 0.036, z - 0.024, z + 0.024, m["iron"], edge=0.002), gate)
        attach(cylinder(f"stair_gate_hinge_pin_{k}", area, sx1 + 0.004, sy0 - 0.042, z - 0.034, z + 0.034, 0.0055, m["iron"], verts=8), gate)
    attach(box("stair_gate_latch_plate", area, sx0 - 0.008, sx0 + 0.075, sy0 - 0.046, sy0 - 0.036, 0.78, 0.88, m["brass"], edge=0.002), gate)
    attach(box("stair_gate_latch", area, sx0 - 0.02, sx0 + 0.06, sy0 - 0.056, sy0 - 0.044, 0.825, 0.855, m["brass"], edge=0.003), gate)
    # The post the gate hangs on, between the stair opening and the east wall.
    box("stair_gate_post", area, sx1 + 0.005, W - 0.012, sy0 - 0.045, sy0 + 0.035, 0, 1.0, m["teak"], edge=0.006)
    collider("stair_gate_post", area, sx1, W, sy0 - 0.045, sy0 + 0.035, 0, 1.0)
    collider("door", area, sx0, sx1, sy0 - 0.05, sy0 + 0.02, 0, 0.95)
    # Warm light rising from the floor below: the bulb is in the bake only.
    empty("marker_stair_glow", area, ((sx0 + sx1) / 2, sy1 - 0.4, -2.4))
    # Telephone and lantern on the hall side of the partition.
    telephone((2.95, P1[1], 1.47))
    lantern_hook((2.42, P1[1], 1.62))
    pinned_poster(4, "A36155", (3.85, P1[1] + 0.014, 1.75), (-1, 0, 0), 0.42, tilt=-0.012)
    # 1930s rotary/tumbler hall light switch wired continuously up cleats to the hanging dining lamp!
    vintage_wall_switch(area, m, turned, "hall_switch", (1.32, P1[1], 1.30), (math.pi / 2, 0, math.pi), toggle_angle_deg=26)
    wire = [(1.32, P1[1] + 0.008, 1.348), (1.32, P1[1] + 0.008, H - 0.03), (tx, P1[1] + 0.008, H - 0.03), (tx, ty, H - 0.03)]
    tube("airwell_wiring", area, wire, 0.0035, m["cord"], sides=5)
    for k, z in enumerate((1.95, 2.65)):
        cl = turned(f"airwell_cleat_{k}", [(0.0, 0.0), (0.012, 0.0), (0.012, 0.02), (0.008, 0.024), (0.0, 0.024)], 0, 0, 0, m["porcelain"], segments=10)
        cl.location = (1.32, P1[1], z)
        cl.rotation_euler = (-math.pi / 2, 0, 0)


def wall_p2():
    """Masonry wall between the hall and the back room, with its doorway and a hyper-detailed
    1932 colonial bedroom door (raised lower panel + upper ventilation louvres, openable with E)."""
    y0, y1 = P2
    d0, d1 = P2_DOOR
    wall("wall_p2_east", d1, W, y0, y1, 0, H, m["limewash"])
    wall("wall_p2_west", 0, d0, y0, y1, 0, H, m["limewash"])
    wall("wall_p2_head", d0, d1, y0, y1, 2.2, H, m["limewash"], solid=False)
    for x in (d0, d1):
        box(f"wall_p2_door_frame_{x:.2f}", area, x - 0.05, x + 0.05, y0 - 0.02, y1 + 0.02, 0, 2.25, m["wood"], edge=0.006)
    box("wall_p2_door_frame_head", area, d0 - 0.05, d1 + 0.05, y0 - 0.02, y1 + 0.02, 2.2, 2.28, m["wood"], edge=0.006)
    # Detailed bedroom privacy + tropical-louvred door, hinged on west jamb (openable/closable + haunted!)
    leaf = (d1 - d0) - 0.025
    door = empty("haunt_bedroom_door", area, (d0 + 0.012, y1, 0.004), (0, 0, math.radians(88)), action="use")
    bpy.context.view_layer.update()
    bparts = [
        box("bed_door_stile_l", area, 0.0, 0.08, 0.0, 0.042, 0.0, 2.18, m["teak"], edge=0.004),
        box("bed_door_stile_r", area, leaf - 0.08, leaf, 0.0, 0.042, 0.0, 2.18, m["teak"], edge=0.004),
        box("bed_door_rail_bot", area, 0.0, leaf, 0.0, 0.042, 0.0, 0.20, m["teak"], edge=0.004),
        box("bed_door_rail_mid", area, 0.0, leaf, 0.0, 0.042, 0.94, 1.07, m["teak"], edge=0.004),
        box("bed_door_rail_top", area, 0.0, leaf, 0.0, 0.042, 2.06, 2.18, m["teak"], edge=0.004),
        # Solid bevelled lower privacy panel
        box("bed_door_panel_lo", area, 0.08, leaf - 0.08, 0.009, 0.033, 0.20, 0.94, m["wood"]),
        box("bed_door_raise_lo", area, 0.11, leaf - 0.11, 0.004, 0.038, 0.23, 0.91, m["rosewood"], edge=0.010),
        # Interior colonial rim-lock box on bedroom side
        box("bed_door_rimlock", area, leaf - 0.14, leaf - 0.015, 0.042, 0.064, 0.94, 1.06, m["iron"], edge=0.003),
    ]
    # Upper tropical ventilation louvres (15 angled colonial slats)
    for j in range(15):
        lz = 1.10 + j * 0.062
        bparts.append(box(f"bed_door_louvre_{j}", area, 0.08, leaf - 0.08, 0.005, 0.037, lz, lz + 0.038, m["shutter"], tilt=(0.48, 0, 0)))
    # Brass escutcheon plates, keyholes & turned brass knobs on BOTH sides
    for side, yy, rot in (("s", -0.002, math.pi / 2), ("n", 0.044, -math.pi / 2)):
        bparts.append(box(f"bed_door_plate_{side}", area, leaf - 0.095, leaf - 0.045, yy - 0.003, yy + 0.003, 0.89, 1.08, m["brass"], edge=0.002))
        bparts.append(box(f"bed_door_keyhole_{side}", area, leaf - 0.074, leaf - 0.066, yy - 0.004, yy + 0.004, 0.915, 0.94, m["dark"]))
        kb = turned(f"bed_door_knob_{side}", [(0.0, 0.0), (0.016, 0.0), (0.010, 0.028), (0.023, 0.048), (0.0, 0.060)], 0, 0, 0, m["brass"], segments=16)
        kb.location = (leaf - 0.070, yy, 1.00)
        kb.rotation_euler = (rot, 0, 0)
        bparts.append(kb)
    for k, hz in enumerate((0.26, 1.09, 1.92)):
        bparts.append(box(f"bed_door_hinge_{k}", area, -0.006, 0.048, 0.038, 0.048, hz - 0.038, hz + 0.038, m["iron"], edge=0.002))
        bparts.append(cylinder(f"bed_door_hinge_pin_{k}", area, -0.004, 0.046, hz - 0.044, hz + 0.044, 0.006, m["iron"], verts=8))
    for p in bparts:
        p.parent = door


def back_room_shell():
    y0, y1 = P2[1], BACK
    # North wall now opens into the 1932 rear bathroom (P3_DOOR = BATH_DOOR); build_bathroom()
    # supplies the P3 partition wall, louvred door, and outer north wet-room enclosure.
    room_walls("back", 0, W, y0, y1, "wens",
               gaps=[("s", P2_DOOR[0] - 0.05, P2_DOOR[1] + 0.05, 2.28),
                     ("n", BATH_DOOR[0] - 0.04, BATH_DOOR[1] + 0.04, 2.24)])
    build_bathroom(area, m, {
        "wall": wall,
        "turned": turned,
        "draped": draped,
        "attach": attach,
        "textured_material": textured_material,
        "crack_decal": crack_decal,
        "cobweb": cobweb,
        "smooth_path": smooth_path,
    })


# =============================================================== front studio


def front_studio():
    tx, ty = 3.0, 0.72
    drafting_table(tx, ty)
    bankers_lamp(2.05, 0.77)
    writing_desk()
    plan_chest(0.0, 3.35)
    case = lib("wooden_bookshelf_worn", (0.3, 5.15, 0), 90, budget=5000)
    shelf_books_on_bookcase(case)
    # Candle shelf, satchel and books on the partition, east of the doorway (P04/P05).
    shelf_and_candle()
    # Tea corner against the east wall, under the colour poster (tray & vintage book clearly separated!).
    lib("chinese_tea_table", (3.75, 2.75, 0), 0, budget=3000)
    tea_tray(3.52, 2.78, 0.5)
    # A paraffin lamp left burning low on the tea table: the posters' light.
    lamp = lib("vintage_oil_lamp", (4.02, 2.98, 0.5), 0, collide=False, scale=0.42, budget=3000)
    empty("marker_tea_lamp", area, flame_point(lamp))
    # A novel left face-up clearly beside the tea tray (Maupassant's Sur l'Eau, 1888) with 12+ cm clearance.
    book("tea_table_book", frame((math.cos(-0.22), math.sin(-0.22), 0), (-math.sin(-0.22), math.cos(-0.22), 0), (3.98, 2.47, 0.502)),
         0.16, 0.22, 0.026, cover="BK21_SUR_LEAU")
    lib("chinese_armchair", (3.75, 3.5, 0), 0, scale=0.74, budget=3000)
    stool_pivot = empty("haunt_stool", area, (3.05, 2.55, 0))
    bpy.context.view_layer.update()
    stool = lib("wooden_stool_01", (3.05, 2.55, 0), 10, collide=False, budget=2500)
    attach(stool, stool_pivot)
    box("rug", area, 2.6, 4.45, 1.85, 3.9, 0.0, 0.012, m["rug"], edge=0.003)
    for k, y in enumerate(np.linspace(1.9, 3.85, 34)):
        tube(f"rug_fringe_w_{k}", area, [(2.6, y, 0.006), (2.555, y + 0.004, 0.003)], 0.0015, m["paper"], sides=4)
        tube(f"rug_fringe_e_{k}", area, [(4.45, y, 0.006), (4.495, y - 0.004, 0.003)], 0.0015, m["paper"], sides=4)
    lib("chinese_sofa", (W - 0.4, 4.95, 0), 270, scale=0.78, budget=2500)
    # On the walls: the user's posters (90s Posters/), six pinned sheets and three framed
    # pictures, handed out to these slots at random each time the room loads
    # (posterShuffle.ts); the postcards pinned in a row above the bench; Wat Phnom by the
    # drafting table (her reference for the illustration).
    east, west = (0, -1, 0), (0, 1, 0)
    pinned_poster(0, "POSTER90_3", (W - 0.014, 2.6, 1.95), east, 0.6, tilt=0.012)
    pinned_poster(1, "POSTER90_1", (W - 0.014, 3.52, 1.86), east, 0.42, tilt=-0.02)
    for k, (item, dy, dz, tl) in enumerate((("DIEU1658", 4.25, 1.62, 0.03), ("DIEU1662", 4.47, 1.66, -0.02), ("DIEUPROM", 4.69, 1.6, 0.04),
                                             ("DIEU1604", 4.91, 1.65, -0.03), ("THRONE1910", 5.13, 1.61, 0.02))):
        print_sheet(f"postcard_{k}", "cards", item, (W - 0.013, dy, dz), east, (0, 0, 1), 0.14, thickness=0.0006, tilt=tl)
        pin(f"postcard_pin_{k}", (W - 0.012, dy, dz + 0.04), (-1, 0, 0))
    print_sheet("wat_phnom_reference", "posters", "A35914", (2.3, 0.014, 1.62), (-1, 0, 0), (0, 0, 1), 0.3, tilt=-0.015)
    pin("wat_phnom_pin", (2.3, 0.013, 1.73), (0, 1, 0))
    top = framed_picture(0, "POSTER90_5", (0.013, 4.0, 1.85), west, 0.52)
    tube("framed_picture_0_cord", area, [(0.012, 3.84, top - 0.01), (0.012, 4.0, 2.45), (0.012, 4.16, top - 0.01)], 0.0015, m["string"], sides=4)
    pinned_poster(2, "POSTER90_7", (0.014, 1.1, 1.8), west, 0.5, tilt=-0.015)
    pinned_poster(3, "POSTER90_2", (2.75, P1[0] - 0.014, 2.0), (1, 0, 0), 0.4, tilt=0.01)
    frame_print("framed_hanuman", "colour", "A36116", (4.05, P1[0] - 0.013, 1.75), (1, 0, 0), (0, 0, 1), 0.34)
    framed_picture(1, "POSTER90_4", (W - 0.013, 1.15, 1.75), east, 0.46)
    # Settlement cracks above the picture rails.
    crack_decal("studio_crack_w", (0.012, 4.72, 2.92), (1, 0, 0), (0, 0.3, 1), (0.4, 0.8), 3)
    crack_decal("studio_crack_e", (W - 0.012, 4.58, 2.95), (-1, 0, 0), (0, -0.25, 1), (0.42, 0.85), 4, flip=True)
    crack_decal("studio_crack_facade", (1.95, 0.012, 2.05), (0, 1, 0), (0.2, 0, 1), (0.34, 0.68), 5)
    box("picture_rail_west", area, 0, 0.025, 0, P1[0], 2.45, 2.49, m["wood"], edge=0.003)
    box("picture_rail_east", area, W - 0.025, W, 0, P1[0], 2.45, 2.49, m["wood"], edge=0.003)
    # On a joist (the planks are 17 cm above the joists' undersides).
    ceiling_fan(2.3, FRONT * 6 / 11)
    # Wiring on porcelain cleats directly from the sconce rosette up to the ceiling joist (meets fan_wiring!)
    wire = [(0.008, 2.15, 1.62), (0.0135, 2.15, 1.72), (0.0135, 2.15, H - 0.172)]
    tube("studio_surface_wiring", area, wire, 0.0035, m["cord"], sides=5)
    for k, z in enumerate((2.08, 2.68)):
        cl = turned(f"studio_cleat_{k}", [(0.0, 0.0), (0.012, 0.0), (0.012, 0.02), (0.008, 0.024), (0.0, 0.024)], 0, 0, 0, m["porcelain"], segments=10)
        cl.location = (0.0, 2.15, z)
        cl.rotation_euler = (0, math.pi / 2, 0)
    junc = turned("studio_wiring_junction", [(0.0, 0.0), (0.022, 0.0), (0.020, 0.012), (0.012, 0.016), (0.0, 0.016)], 0, 0, 0, m["porcelain"], segments=16)
    junc.location = (0.0, 2.15, H - 0.172)
    junc.rotation_euler = (0, math.pi / 2, 0)
    # Museum-grade 1930s Bakelite & brass tumbler switch by the partition doorway, wired cleanly to ceiling!
    vintage_wall_switch(area, m, turned, "studio_switch", (1.34, P1[0], 1.30), (math.pi / 2, 0, 0), toggle_angle_deg=26)
    tube("studio_switch_wiring", area, [(1.34, P1[0] - 0.008, 1.348), (1.34, P1[0] - 0.008, H - 0.172)], 0.0035, m["cord"], sides=5)
    for k, z in enumerate((1.95, 2.65)):
        cl = turned(f"studio_sw_cleat_{k}", [(0.0, 0.0), (0.012, 0.0), (0.012, 0.02), (0.008, 0.024), (0.0, 0.024)], 0, 0, 0, m["porcelain"], segments=10)
        cl.location = (1.34, P1[0], z)
        cl.rotation_euler = (math.pi / 2, 0, 0)
    dress_working_studio(tx, ty)
    empty("spawn_player", area, (tx, ty + 0.95, 0), (0, 0, math.pi), checkpoint="CP0")


def drafting_table(tx, ty):
    """Sora's drafting table under the east door (P02): oak trestles, a breadboarded top
    tilted toward her, its front edge resting on the trestles and its back held up by an
    iron stay in a ratchet, a tray for pens along the front; the Wat Phnom illustration
    inked to the middle. (The board used to float: tilted about its middle, it passed
    through the trestle tops in front and hung in the air behind, the tray above its edge.)"""
    lift = 0.06          # the board sits this much higher than the trestles' tops would put it
    tilt = (-0.26, 0, 0)
    for s in (-1, 1):
        x = tx + s * 0.55
        box(f"drafting_trestle_{s}", area, x - 0.028, x + 0.028, ty - 0.3, ty + 0.3, 0.05, 0.86, m["worn"], edge=0.006)
        box(f"drafting_foot_{s}", area, x - 0.045, x + 0.045, ty - 0.36, ty + 0.36, 0, 0.055, m["worn"], edge=0.008)
        # The ratchet on the back of the trestle and the stay standing in its third notch,
        # up to the underside of the board.
        rx = x - s * 0.034
        box(f"drafting_ratchet_{s}", area, rx - 0.006, rx + 0.006, ty - 0.34, ty - 0.1, 0.7, 0.86, m["iron"])
        for j in range(5):
            box(f"drafting_ratchet_tooth_{s}_{j}", area, rx - 0.008, rx + 0.008, ty - 0.32 + j * 0.045, ty - 0.3 + j * 0.045, 0.85, 0.87, m["iron"])
        box(f"drafting_stay_{s}", area, rx - 0.007, rx + 0.007, ty - 0.215, ty - 0.2, 0.86, 1.0, m["iron"], tilt=(0.06, 0, 0))
    box("drafting_stretcher", area, tx - 0.55, tx + 0.55, ty - 0.02, ty + 0.02, 0.2, 0.26, m["worn"], edge=0.004)
    z = lambda v: v + lift
    box("drafting_top", area, tx - 0.62, tx + 0.62, ty - 0.38, ty + 0.38, z(0.88), z(0.91), m["teak"], tilt=tilt, edge=0.004)
    for s in (-1, 1):
        box(f"drafting_breadboard_{s}", area, tx + s * 0.62 - 0.035, tx + s * 0.62 + 0.035, ty - 0.39, ty + 0.39, z(0.878), z(0.912), m["worn"], tilt=tilt, edge=0.004)
    # The pen tray hung on the board's front edge: a shallow trough with a lip.
    box("drafting_ledge", area, tx - 0.62, tx + 0.62, ty + 0.355, ty + 0.47, 0.835, 0.858, m["worn"], edge=0.003)
    box("drafting_ledge_lip", area, tx - 0.62, tx + 0.62, ty + 0.455, ty + 0.47, 0.858, 0.874, m["worn"], edge=0.002)
    collider("drafting_table", area, tx - 0.66, tx + 0.66, ty - 0.4, ty + 0.47, 0, 1.0)
    illustration = box("interact_illustration", area, tx - 0.3, tx + 0.3, ty - 0.21, ty + 0.21, z(0.912), z(0.914), m["illustration"],
                       tilt=tilt, action="examine")
    picture_uvs(illustration, (-1, 0, 0), (0, -1, 0))
    # Brass clips holding the sheet at its far edge, the T-square lying on the board:
    # each set on the sloping top (z_top), not tilted about its own middle in mid-air.
    z_top = lambda dy: z(0.91) + 0.015 * (1 / math.cos(0.26) - 1) - math.tan(0.26) * dy
    for s in (-1, 1):
        box(f"drafting_clip_{s}", area, tx + s * 0.28 - 0.015, tx + s * 0.28 + 0.015, ty - 0.24, ty - 0.2, z_top(-0.22) + 0.002, z_top(-0.22) + 0.009, m["brass"], tilt=tilt, edge=0.002)
    box("t_square_blade", area, tx - 0.5, tx + 0.25, ty + 0.22, ty + 0.25, z_top(0.235), z_top(0.235) + 0.008, m["teak"], tilt=tilt)
    box("t_square_head", area, tx - 0.55, tx - 0.5, ty - 0.12, ty + 0.3, z_top(0.09), z_top(0.09) + 0.03, m["wood"], tilt=tilt)
    t = 0.858
    cylinder("ink_jar", area, tx + 0.45, ty + 0.41, t, t + 0.07, 0.03, m["ink"])
    cylinder("ink_jar_cap", area, tx + 0.45, ty + 0.41, t + 0.07, t + 0.085, 0.022, m["iron"])
    cylinder("water_jar_for_brushes", area, tx - 0.42, ty + 0.41, t, t + 0.1, 0.04, plain("M_studio_jar_glass", (0.16, 0.2, 0.18), rough=0.12, alpha=0.35))
    cylinder("water_jar_for_brushes_water", area, tx - 0.42, ty + 0.41, t + 0.004, t + 0.07, 0.037, m["water"])
    # A pencil lying in the tray.
    tube("drafting_pencil", area, [(tx + 0.08, ty + 0.4, t + 0.0035), (tx + 0.25, ty + 0.425, t + 0.0035)], 0.0035, m["worn"], sides=6)
    lib("chinese_stool", (tx, ty + 0.75, 0), 0, collide=False, budget=2000)


def bankers_lamp(lx, ly):
    """Green-shaded banker's lamp on its stand: the key light (bulb in the bake; marker
    for the runtime light). Shade: cased glass, green outside, opal white inside."""
    box("lamp_stand_top", area, lx - 0.21, lx + 0.21, ly - 0.21, ly + 0.21, 0.86, 0.9, m["rosewood"], edge=0.006)
    for ox in (-0.17, 0.17):
        for oy in (-0.17, 0.17):
            turned(f"lamp_stand_leg_{ox}_{oy}", [(0.0, 0.0), (0.016, 0.0), (0.02, 0.1), (0.018, 0.5), (0.024, 0.78), (0.024, 0.86), (0.0, 0.86)], lx + ox, ly + oy, 0, m["rosewood"], segments=10)
    box("lamp_stand_shelf", area, lx - 0.19, lx + 0.19, ly - 0.19, ly + 0.19, 0.25, 0.27, m["rosewood"], edge=0.004)
    collider("lamp_stand", area, lx - 0.21, lx + 0.21, ly - 0.21, ly + 0.21, 0, 0.9)
    z = 0.9
    turned("desk_lamp_base", [(0.0, 0.0), (0.09, 0.0), (0.095, 0.01), (0.085, 0.024), (0.055, 0.033), (0.024, 0.037), (0.0, 0.037)], lx, ly, z, m["brass"], segments=32)
    turned("desk_lamp_stem", [(0.0, 0.0), (0.011, 0.0), (0.011, 0.25), (0.0, 0.25)], lx, ly, z + 0.035, m["brass"], segments=12)
    turned("desk_lamp_collar", [(0.0, 0.0), (0.02, 0.0), (0.02, 0.012), (0.0, 0.012)], lx, ly, z + 0.04, m["brass"], segments=16)
    sy = ly - 0.07
    tube("desk_lamp_harp", area, [(lx, ly, z + 0.28), (lx, ly - 0.02, z + 0.31), (lx, sy, z + 0.31)], 0.007, m["brass"], sides=8)
    # The shade: a half-cylinder 0.30 m long with rounded ends, outer green, inner opal.
    for name, rad, mat in (("desk_lamp_shade", 0.078, m["green_glass"]), ("desk_lamp_shade_inner", 0.074, m["opal"])):
        verts, faces = [], []
        n, length = 20, 0.3
        for i in range(n + 1):
            a = math.pi * i / n
            for x in (-length / 2, length / 2):
                verts.append((lx + x, sy + math.cos(a) * rad, z + 0.31 + math.sin(a) * rad * 0.85 - 0.02))
        for i in range(n):
            k = i * 2
            faces.append((k, k + 1, k + 3, k + 2) if mat is m["green_glass"] else (k + 2, k + 3, k + 1, k))
        obj = mesh_object(name, area, verts, faces, mat, smooth=True)
        for side in (-1, 1):
            cap = [(lx + side * length / 2, sy + math.cos(math.pi * i / n) * rad, z + 0.31 + math.sin(math.pi * i / n) * rad * 0.85 - 0.02) for i in range(n + 1)]
            base = len(verts)
            mesh_object(f"{name}_cap_{side}", area, cap, [tuple(range(n + 1)) if side > 0 else tuple(reversed(range(n + 1)))], mat)
    tube("desk_lamp_shade_binding", area, [(lx - 0.15, sy + math.cos(a) * 0.079, z + 0.31 + math.sin(a) * 0.079 * 0.85 - 0.02) for a in np.linspace(0, math.pi, 13)], 0.003, m["brass"], sides=5)
    tube("desk_lamp_shade_binding_e", area, [(lx + 0.15, sy + math.cos(a) * 0.079, z + 0.31 + math.sin(a) * 0.079 * 0.85 - 0.02) for a in np.linspace(0, math.pi, 13)], 0.003, m["brass"], sides=5)
    cylinder("desk_lamp_bulb", area, lx, sy, z + 0.25, z + 0.29, 0.022, m["bulb"], verts=12)
    tube("desk_lamp_pull_chain", area, [(lx + 0.05, sy - 0.02, z + 0.27), (lx + 0.05, sy - 0.025, z + 0.16)], 0.0012, m["brass"], sides=4)
    turned("desk_lamp_pull", [(0.0, 0.0), (0.006, 0.004), (0.004, 0.02), (0.0, 0.024)], lx + 0.05, sy - 0.025, z + 0.14, m["brass"], segments=8)
    # The braided lead: out of the base, across the stand's top, over its back edge, hanging
    # in a slack curve to the floor, along the floor to a porcelain socket on the wall.
    sock = (lx + 0.2, 0.0125, 0.32)
    box("desk_lamp_socket_block", area, sock[0] - 0.035, sock[0] + 0.035, 0.0125, 0.027, sock[2] - 0.035, sock[2] + 0.035, m["wood"], edge=0.003)
    turned("desk_lamp_socket", [(0.0, 0.0), (0.026, 0.0), (0.024, 0.016), (0.012, 0.022), (0.0, 0.023)], 0, 0, 0, m["porcelain"], segments=20).location = (sock[0], 0.027, sock[2])
    bpy.data.objects["desk_lamp_socket"].rotation_euler = (-math.pi / 2, 0, 0)
    turned("desk_lamp_plug", [(0.0, 0.0), (0.011, 0.0), (0.011, 0.024), (0.005, 0.03), (0.0, 0.03)], 0, 0, 0, m["ebonite"], segments=12).location = (sock[0], 0.048, sock[2])
    bpy.data.objects["desk_lamp_plug"].rotation_euler = (-math.pi / 2, 0, 0)
    lead = [(lx - 0.03, ly - 0.085, z + 0.006), (lx - 0.04, ly - 0.15, z + 0.0032), (lx - 0.04, ly - 0.205, z + 0.0032),
            (lx - 0.035, ly - 0.215, z - 0.012), (lx - 0.02, ly - 0.235, 0.55), (lx + 0.02, ly - 0.27, 0.12),
            (lx + 0.07, ly - 0.33, 0.004), (lx + 0.13, ly - 0.45, 0.0035), (lx + 0.17, ly - 0.6, 0.0035),
            (sock[0] - 0.01, 0.07, 0.0035), (sock[0], 0.075, 0.03), (sock[0], 0.075, sock[2] - 0.06), (sock[0], 0.075, sock[2])]
    tube("desk_lamp_braided_lead", area, smooth_path(lead, 6), 0.0032, m["cord"], sides=6)
    empty("marker_desk_lamp", area, (lx, sy, z + 0.26))


def writing_desk():
    """The writing desk on the west wall, as the prologue code expects it: top x 0.02-0.68,
    y 1.75-3.25, the drawer at y 2.25-2.75 facing the room (+x)."""
    dx0, dx1, dy0, dy1 = 0.02, 0.68, 1.75, 3.25
    box("desk_top", area, dx0, dx1, dy0, dy1, 0.74, 0.78, m["rosewood"], edge=0.008)
    box("desk_top_moulding", area, dx1 - 0.01, dx1 + 0.012, dy0, dy1, 0.735, 0.765, m["rosewood"], edge=0.006)
    for k, (y0, y1) in enumerate([(dy0 + 0.03, dy0 + 0.08), (dy1 - 0.08, dy1 - 0.03)]):
        for x0, x1 in [(dx0 + 0.03, dx0 + 0.08), (dx1 - 0.08, dx1 - 0.03)]:
            turned(f"desk_leg_{k}_{x0:.2f}", [(0.0, 0.0), (0.02, 0.0), (0.026, 0.05), (0.018, 0.18), (0.022, 0.5), (0.028, 0.6), (0.028, 0.74), (0.0, 0.74)],
                   (x0 + x1) / 2, (y0 + y1) / 2, 0, m["rosewood"], segments=12)
    box("desk_apron_s", area, dx1 - 0.04, dx1 - 0.02, dy0 + 0.08, 2.24, 0.6, 0.74, m["rosewood"], edge=0.003)
    box("desk_apron_n", area, dx1 - 0.04, dx1 - 0.02, 2.76, dy1 - 0.08, 0.6, 0.74, m["rosewood"], edge=0.003)
    collider("desk", area, dx0, dx1, dy0, dy1, 0, 0.78)
    box("interact_drawer", area, dx1 - 0.03, dx1 + 0.0, 2.25, 2.75, 0.62, 0.72, m["worn"], edge=0.004, action="open", items="letters,matchbox", beat="P03")
    box("drawer_knob", area, dx1 + 0.0, dx1 + 0.025, 2.48, 2.52, 0.66, 0.68, m["brass"])
    for k in range(5):
        box(f"letter_{k}", area, 0.35, 0.55, 2.4 + rng.uniform(-0.01, 0.01), 2.56, 0.64 + k * 0.006, 0.645 + k * 0.006, m["paper"])
    box("letters_string", area, 0.44, 0.46, 2.39, 2.57, 0.64, 0.675, plain("M_red_string", (0.5, 0.05, 0.04)))
    box("matchbox", area, 0.25, 0.3, 2.62, 2.66, 0.64, 0.655, m["brass"], edge=0.002)
    # Sora's sketchbook: landscape, quarter-bound, black cloth boards and a leather spine.
    sk = book("interact_sketchbook", frame((0, 1, 0), (-1, 0, 0), (0.30, 2.16, 0.78)), 0.32, 0.24, 0.024,
              cover=plain("M_studio_sketchbook_cloth", (0.03, 0.035, 0.03), rough=0.92), bands=0,
              quarter=m["leather"], props={"action": "pickup", "item": "sketchbook"})
    label = box("interact_sketchbook_label", area, 0.02, 0.11, -0.035, 0.035, 0.024, 0.0244, m["paper"])
    label.parent = sk
    # On the desk: letters waiting for an answer, a blotter, ink, a dip pen, the brush cup.
    box("desk_blotter", area, 0.12, 0.6, 2.45, 3.05, 0.78, 0.786, plain("M_studio_blotter", (0.18, 0.22, 0.16), rough=0.95), edge=0.002)
    for k in range(4):
        box(f"desk_envelope_{k}", area, 0.18, 0.3, 2.78 + k * 0.004, 2.86 + k * 0.004, 0.786 + k * 0.0016, 0.787 + k * 0.0016, m["paper"], tilt=(0, 0, 0.08))
    cylinder("desk_ink_bottle", area, 0.55, 1.95, 0.78, 0.86, 0.025, m["ink"])
    cylinder("desk_ink_bottle_cap", area, 0.55, 1.95, 0.86, 0.875, 0.016, m["iron"])
    cup = [(0.0, 0.0), (0.026, 0.0), (0.03, 0.008), (0.034, 0.082), (0.036, 0.088), (0.032, 0.09), (0.029, 0.016), (0.0, 0.016)]
    turned("desk_brush_cup", cup, 0.22, 1.92, 0.78, m["porcelain"], segments=20)
    for i in range(4):
        pen = cylinder(f"desk_dip_pen_{i}", area, 0.22 + (i - 1.5) * 0.009, 1.92, 0.79, 0.96, 0.0028, m["wood"] if i % 2 else m["rosewood"], verts=6)
        pen.rotation_euler = (0.13 * (i - 1.5), 0.1, 0)
    ruler = box("desk_ruler", area, 0.25, 0.56, 3.08, 3.107, 0.786, 0.789, m["worn"], tilt=(0, 0, -0.14))
    for k, (w, d, h, cov) in enumerate(((0.20, 0.27, 0.036, "BK02_CAMBODGE"),
                                        (0.18, 0.25, 0.032, "BK05_LETTRES_AN"),
                                        (0.17, 0.24, 0.028, "BK01_INDOCHINE"))):
        z = 0.786 + sum((0.036, 0.032, 0.028)[:k])
        a = float((-0.07, 0.09, -0.04)[k])
        # Lying in a stack, spines to the room (+x), real cover face-up under the sconce.
        book(f"desk_book_{k}", frame((-math.cos(a), -math.sin(a), 0), (math.sin(a), -math.cos(a), 0), (0.31, 3.09, z)), w, d, h,
             cover=cov)
    # Sora's diary open on the blotter, the candle she writes it by beside it: the studio's
    # save point, clear of the books and the photograph.
    open_journal(0.42, 2.62, 0.786)
    chamberstick(0.53, 2.95, 0.786)
    # The photograph in its standing frame, turned to face the chair (it showed its back).
    photo_frame = lib("standing_picture_frame_01", (0.14, 3.2, 0.786), 320, collide=False)
    # Its picture is one of Busy's 1921 photographs of a royal dancer (the frame's own
    # artwork came out black).
    photo = image_material("M_studio_desk_photo", os.path.join(LIB, "archive", "A36113.jpg"), rough=0.4)
    m["photo_glass"] = plain("M_studio_photo_glass", (0.02, 0.02, 0.02), rough=0.05, alpha=0.12)
    for part in photo_frame.children_recursive:
        if part.type == "MESH":
            for slot in part.material_slots:
                if slot.material and slot.material.name.endswith("_artwork"):
                    slot.material = photo
                elif slot.material and slot.material.name.endswith("_glass"):
                    slot.material = m["photo_glass"]
    lib("wicker_basket_01", (0.35, 1.45, 0), 0, collide=False, budget=3000)
    # The chair pushed back from the desk, turned a little as Sora left it: the drawer
    # opens into clear floor and she can step right up to it (it stood 10 cm off the
    # desk, in the drawer's way and between her and its contents).
    lib("chinese_armchair", (1.5, 2.0, 0), 252, scale=0.74, budget=2500)
    # Clock on its bracket above the desk (stops at 8:12, P05) and the wall sconce.
    box("clock_bracket", area, 0.0, 0.24, 2.85, 3.2, 1.92, 1.95, m["rosewood"], edge=0.004)
    lib("mantel_clock_01", (0.12, 3.02, 1.95), 90, collide=False, budget=3000)
    empty("marker_clock", area, (0.14, 3.02, 2.1))
    wall_sconce(0.0, 2.15, 1.62)


def wall_sconce(x, y, z):
    """Brass gooseneck sconce with a glazed shade over the desk (bulb in the bake)."""
    turned("sconce_rosette", [(0.0, 0.0), (0.055, 0.0), (0.05, 0.012), (0.0, 0.014)], 0, 0, 0, m["brass"], segments=20).location = (x, y, z)
    bpy.data.objects["sconce_rosette"].rotation_euler = (0, math.pi / 2, 0)
    tube("sconce_gooseneck", area, [(x + 0.01, y, z), (x + 0.08, y, z + 0.02), (x + 0.17, y, z + 0.015), (x + 0.21, y, z - 0.025)], 0.008, m["brass"], sides=8)
    shade = [(0.019, 0.0), (0.025, -0.012), (0.052, -0.075), (0.071, -0.094), (0.073, -0.103), (0.067, -0.104), (0.046, -0.08), (0.019, -0.02)]
    turned("sconce_shade", shade, x + 0.21, y, z - 0.005, m["porcelain"], segments=24)
    cylinder("sconce_bulb", area, x + 0.21, y, z - 0.085, z - 0.045, 0.012, m["bulb"], verts=10)
    empty("marker_writing_sconce", area, (x + 0.21, y, z - 0.07))


def flame_point(lamp):
    """Centre of a library oil lamp's own flame mesh (its flame material), for the light."""
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in lamp.children_recursive if o.type == "MESH"
           and any(s.material and "flame" in s.material.name for s in o.material_slots) for v in o.data.vertices]
    if not pts:
        top = top_of(lamp)
        return (lamp.location.x, lamp.location.y, top - 0.12)
    return tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))


def tea_tray(x, y, z):
    """A red lacquer tray with a Chinese teapot and four small cups, one poured."""
    lacquer = plain("M_studio_red_lacquer", (0.32, 0.06, 0.04), rough=0.3)
    celadon = plain("M_studio_celadon", (0.62, 0.7, 0.6), rough=0.15)
    tray = box("tea_tray", area, x - 0.2, x + 0.2, y - 0.14, y + 0.14, z, z + 0.012, lacquer, edge=0.004)
    for nm, a in (("n", (x - 0.2, x + 0.2, y + 0.13, y + 0.14)), ("s", (x - 0.2, x + 0.2, y - 0.14, y - 0.13)),
                  ("w", (x - 0.2, x - 0.19, y - 0.14, y + 0.14)), ("e", (x + 0.19, x + 0.2, y - 0.14, y + 0.14))):
        box(f"tea_tray_rim_{nm}", area, a[0], a[1], a[2], a[3], z + 0.012, z + 0.03, lacquer, edge=0.003)
    pot = [(0.0, 0.0), (0.04, 0.0), (0.06, 0.02), (0.068, 0.05), (0.06, 0.085), (0.035, 0.1), (0.028, 0.104), (0.0, 0.104)]
    turned("tea_pot", pot, x - 0.07, y + 0.02, z + 0.012, celadon, segments=28)
    turned("tea_pot_lid_knob", [(0.0, 0.0), (0.01, 0.0), (0.008, 0.016), (0.0, 0.02)], x - 0.07, y + 0.02, z + 0.115, celadon, segments=12)
    tube("tea_pot_spout", area, [(x - 0.015, y + 0.02, z + 0.04), (x + 0.02, y + 0.02, z + 0.07), (x + 0.035, y + 0.02, z + 0.095)], 0.008, celadon, sides=8, radius_end=0.005)
    tube("tea_pot_handle", area, [(x - 0.13, y + 0.02, z + 0.03), (x - 0.155, y + 0.02, z + 0.06), (x - 0.13, y + 0.02, z + 0.09)], 0.005, celadon, sides=6)
    cup = [(0.0, 0.0), (0.016, 0.0), (0.02, 0.004), (0.028, 0.035), (0.027, 0.036), (0.022, 0.006), (0.0, 0.006)]
    for k, (cx, cy) in enumerate(((x + 0.06, y - 0.06), (x + 0.12, y + 0.05), (x + 0.12, y - 0.05), (x + 0.03, y + 0.07))):
        turned(f"tea_cup_{k}", cup, cx, cy, z + 0.012, celadon, segments=20)
    box("tea_cup_tea", area, x + 0.04, x + 0.08, y - 0.08, y - 0.04, z + 0.036, z + 0.037, plain("M_studio_tea", (0.18, 0.08, 0.02), rough=0.05))
    return tray


def plan_chest(x0, y0):
    """A flat-file plan chest for drawings: ten shallow drawers with brass label holders."""
    x1, y1, top = x0 + 0.72, y0 + 1.05, 0.95
    box("plan_chest_body", area, x0 + 0.01, x1, y0, y1, 0.08, top, m["rosewood"], edge=0.006)
    box("plan_chest_top", area, x0, x1 + 0.02, y0 - 0.02, y1 + 0.02, top, top + 0.035, m["rosewood"], edge=0.008)
    box("plan_chest_plinth", area, x0 + 0.02, x1 - 0.01, y0 + 0.01, y1 - 0.01, 0, 0.08, m["wood"])
    for i in range(10):
        z0 = 0.1 + i * 0.083
        box(f"plan_chest_drawer_{i}", area, x1 - 0.004, x1 + 0.006, y0 + 0.03, y1 - 0.03, z0, z0 + 0.075, m["rosewood"], edge=0.003)
        for s in (0.3, 0.7):
            box(f"plan_chest_pull_{i}_{s}", area, x1 + 0.006, x1 + 0.02, y0 + (y1 - y0) * s - 0.035, y0 + (y1 - y0) * s + 0.035, z0 + 0.03, z0 + 0.045, m["brass"], edge=0.003)
        box(f"plan_chest_label_{i}", area, x1 + 0.006, x1 + 0.009, y0 + (y1 - y0) / 2 - 0.03, y0 + (y1 - y0) / 2 + 0.03, z0 + 0.04, z0 + 0.06, m["brass"])
    collider("plan_chest", area, x0, x1 + 0.03, y0, y1, 0, top + 0.04)
    # On top: a portfolio, rolled drawings, a jar of brushes.
    t = top + 0.035
    box("plan_chest_portfolio", area, x0 + 0.08, x0 + 0.6, y0 + 0.08, y0 + 0.62, t, t + 0.022, m["leather"], tilt=(0, 0, 0.04), edge=0.006)
    # Its cotton tapes: from under the fore-edge, over the top, tied in a flat bow.
    tape = plain("M_studio_cotton_tape", (0.55, 0.48, 0.36), rough=0.95)
    for k in range(3):
        ty_ = y0 + 0.21 + k * 0.17
        box(f"plan_chest_portfolio_tape_{k}", area, x0 + 0.53, x0 + 0.611, ty_ - 0.006, ty_ + 0.006, t + 0.022, t + 0.0232, tape)
        box(f"plan_chest_portfolio_tape_edge_{k}", area, x0 + 0.609, x0 + 0.6115, ty_ - 0.006, ty_ + 0.006, t, t + 0.0232, tape)
        for side in (-1, 1):
            loop = [(x0 + 0.535 + 0.022 * math.cos(a) * 0.9, ty_ + side * (0.012 + 0.012 * math.sin(a)), t + 0.0245) for a in np.linspace(-math.pi / 2, math.pi / 2, 9)]
            tube(f"plan_chest_portfolio_bow_{k}_{side}", area, loop, 0.0018, tape, sides=5)
    # Rolled drawings lying along the chest, each tied with string, the paper's spiral
    # showing at the ends.
    aged = plain("M_studio_rolled_paper", (0.78, 0.7, 0.54), rough=0.95)
    edge_line = plain("M_studio_roll_layers", (0.5, 0.44, 0.32), rough=0.95)
    hollow = plain("M_studio_roll_hollow", (0.12, 0.1, 0.07), rough=1.0)
    for k, (length, r) in enumerate(((0.62, 0.028), (0.55, 0.024), (0.66, 0.03))):
        y = y0 + 0.72 + k * 0.062
        z = t + r
        x_mid = x0 + 0.36 + (k - 1) * 0.02
        # Lying along the chest: a paper cylinder, its ends open on the spiral of the sheet.
        roll = cylinder(f"plan_chest_roll_{k}", area, 0, 0, -length / 2, length / 2, r, aged, verts=20)
        roll.location = (x_mid, y, z)
        roll.rotation_euler = (0, math.pi / 2, 0)
        for e in (-1, 1):
            core = cylinder(f"plan_chest_roll_hollow_{k}_{e}", area, 0, 0, -0.0012, 0.0012, r * 0.32, hollow, verts=12)
            core.location = (x_mid + e * (length / 2 + 0.0002), y, z)
            core.rotation_euler = (0, math.pi / 2, 0)
            spiral = [(x_mid + e * (length / 2 + 0.0014), y + math.cos(a) * (0.32 * r + 0.68 * r * a / 16), z + math.sin(a) * (0.32 * r + 0.68 * r * a / 16)) for a in np.linspace(0, 16, 48)]
            tube(f"plan_chest_roll_end_{k}_{e}", area, spiral, 0.0004, edge_line, sides=4)
        for sx in (-0.15, 0.15):
            tie = [(x_mid + sx, y + math.cos(a) * (r + 0.0009), z + math.sin(a) * (r + 0.0009)) for a in np.linspace(0, math.tau, 25)]
            tube(f"plan_chest_roll_tie_{k}_{sx}", area, tie, 0.0011, m["cord"], sides=5)


def shelf_books_on_bookcase(case):
    """Books, portfolios and boxes on each shelf of the bookcase: shelf heights are found
    by casting rays down through the imported model."""
    bpy.context.view_layer.update()
    verts, polys = [], []
    for o in case.children_recursive:
        if o.type != "MESH":
            continue
        base = len(verts)
        verts += [o.matrix_world @ v.co for v in o.data.vertices]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    tree = mathutils.bvhtree.BVHTree.FromPolygons(verts, polys)
    xs, ys = [v.x for v in verts], [v.y for v in verts]
    x_mid, y_lo, y_hi = (min(xs) + max(xs)) / 2, min(ys) + 0.06, max(ys) - 0.06
    shelves, z = [], max(v.z for v in verts) + 0.1
    while True:
        hit = tree.ray_cast(mathutils.Vector((x_mid, (y_lo + y_hi) / 2, z)), mathutils.Vector((0, 0, -1)))
        if hit[0] is None:
            break
        # hit = (location, normal, index, distance): an upward face is a shelf's top.
        if hit[1].z > 0.5 and hit[0].z > 0.05 and (not shelves or shelves[-1] - hit[0].z > 0.18):
            shelves.append(hit[0].z)
        z = hit[0].z - 0.01
    depth = min(0.24, max(xs) - min(xs) - 0.08)
    # Deterministic order cycling through all 32 distinct vintage covers with no adjacent repeats.
    order = [bid for _, bid, _ in BOOK_CATALOG]
    pick_i = 0
    tops = sorted(shelves)
    for s_i, z in enumerate(tops[1:5]):
        y = y_lo
        k = 0
        # Up to the underside of the board above (boards are about 4.5 cm thick).
        room = min(0.31, tops[tops.index(z) + 1] - 0.045 - z - 0.012) if z != tops[-1] else 0.30
        # On shelves 1 & 2, reserve a horizontal showcase stack near the north end so real covers shine!
        stack_start = y_hi - 0.27 if s_i in (1, 2) else y_hi
        while y < stack_start - 0.04:
            w = float(rng.uniform(0.028, 0.054))
            h = min(room, float(rng.uniform(0.21, 0.295)))
            if rng.random() < 0.08:  # a gap where books have been taken out
                y += float(rng.uniform(0.045, 0.095))
                continue
            bid = order[pick_i % len(order)]
            pick_i += 1
            # Standing, spine out to the room (+x), leaning a hair now and then.
            lean = float(rng.uniform(-0.02, 0.02))
            # One featured book on shelf 2 slides out in Phase 1; one on shelf 3 drops onto the floor in Phase 2/3!
            is_slide = (s_i == 2 and k == 3)
            is_drop = (s_i == 3 and k == 2)
            bname = "haunt_slide_book" if is_slide else ("haunt_drop_book" if is_drop else f"bookcase_book_{s_i}_{k}")
            book(bname, frame((-1, 0, 0), (0, math.sin(lean), math.cos(lean)), (x_mid, y + w / 2, z + h / 2)), depth, h, w,
                 cover="BK18_KING_YELLOW" if is_slide else ("BK16_GHOST_ANTIQ" if is_drop else bid))
            y += w + 0.003
            k += 1
        # Flat cover-up stacks at the north end of shelves 1 & 2 (real illustrated covers clearly visible!)
        if s_i in (1, 2):
            stack_books = (
                (("BK28_TOUR_MONDE", 0.18, 0.24, 0.036), ("BK27_DOCTEUR_OX", 0.17, 0.23, 0.032), ("BK07_TEXTILE", 0.16, 0.22, 0.028))
                if s_i == 1 else
                (("BK31_NAUFRAGES", 0.18, 0.24, 0.036), ("BK29_VILLE_FLOT", 0.17, 0.23, 0.032), ("BK11_OROCHI", 0.16, 0.21, 0.026))
            )
            zz = z
            for sk_i, (sbid, sw, sh, st) in enumerate(stack_books):
                tw = float((-0.05, 0.08, -0.06)[sk_i])
                book(f"bookcase_flat_{s_i}_{sk_i}",
                     frame((-math.cos(tw), -math.sin(tw), 0), (math.sin(tw), -math.cos(tw), 0), (x_mid + 0.01, y_hi - 0.13, zz)),
                     sw, sh, st, cover=sbid)
                zz += st
    # Uppermost visible shelf (below the top roof board): three leaned face-out showcase
    # volumes displaying full real vintage covers into the room!
    if len(tops) >= 6:
        top_z = tops[-2]
        for k, (bid, dy, lean_x) in enumerate((("BK02_CAMBODGE", -0.26, 0.16), ("BK18_KING_YELLOW", 0.0, 0.14), ("BK27_DOCTEUR_OX", 0.26, 0.18))):
            y_at = (y_lo + y_hi) / 2 + dy
            bh, bw, bt = 0.25, 0.175, 0.026
            book(f"bookcase_display_{k}",
                 frame((0, 1, 0), (-math.sin(lean_x), 0, math.cos(lean_x)), (x_mid - 0.02, y_at, top_z + bh * math.cos(lean_x) / 2)),
                 bw, bh, bt, cover=bid)


def khmer_incense_stick(name, base, dir_v, body_len=0.115):
    """Single multi-material photorealistic Khmer incense stick (red bamboo splint,
    dark sandalwood paste body, burnt grey ash collar, and glowing red-orange ember tip).
    Returned as one mesh so Havok physics detaches the entire stick cleanly."""
    import bmesh
    dv = mathutils.Vector(dir_v).normalized()
    up = mathutils.Vector((0, 0, 1)) if abs(dv.z) < 0.99 else mathutils.Vector((1, 0, 0))
    u = dv.cross(up).normalized()
    v = dv.cross(u).normalized()
    b0 = mathutils.Vector(base)
    # Segments: (start_dist, end_dist, radius_start, radius_end, mat_index)
    segs = [
        (0.0, 0.052, 0.0011, 0.0011, 0),                             # red bamboo splint
        (0.052, 0.052 + body_len, 0.0018, 0.00175, 1),               # sandalwood paste
        (0.052 + body_len, 0.068 + body_len, 0.00165, 0.00145, 2),   # burnt pale grey ash
        (0.068 + body_len, 0.074 + body_len, 0.00145, 0.0005, 3),    # glowing red-orange ember cone
    ]
    sides = 8
    bm = bmesh.new()
    for d0, d1, r0, r1, mi in segs:
        ring0, ring1 = [], []
        for i in range(sides):
            a = i * math.tau / sides
            off = u * math.cos(a) + v * math.sin(a)
            ring0.append(bm.verts.new(b0 + dv * d0 + off * r0))
            ring1.append(bm.verts.new(b0 + dv * d1 + off * r1))
        for i in range(sides):
            j = (i + 1) % sides
            f = bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
            f.material_index = mi
            f.smooth = True
    tip_pt = b0 + dv * (0.075 + body_len)
    v_tip = bm.verts.new(tip_pt)
    for i in range(sides):
        j = (i + 1) % sides
        f = bm.faces.new((ring1[i], ring1[j], v_tip))
        f.material_index = 3
        f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mk in ("incense_red", "incense", "incense_ash", "incense_ember"):
        me.materials.append(m[mk])
    o = bpy.data.objects.new(name, me)
    area.objects.link(o)
    return o, tuple(tip_pt)


def shelf_and_candle():
    sx0, sx1, z = 2.05, 3.55, 1.32
    y1 = P1[0]
    box("shelf", area, sx0, sx1, y1 - 0.3, y1 - 0.015, z, z + 0.035, m["rosewood"], edge=0.004)
    for x in (sx0 + 0.12, sx1 - 0.12):
        box(f"shelf_bracket_{x:.2f}", area, x - 0.018, x + 0.018, y1 - 0.25, y1 - 0.015, z - 0.18, z, m["rosewood"], edge=0.003)
    collider("shelf", area, sx0, sx1, y1 - 0.3, y1, z - 0.2, z + 0.035)
    stick = lib("wooden_candlestick", (3.38, y1 - 0.16, z + 0.035), 0, collide=False, budget=2500)
    top = top_of(stick)
    cx_c, cy_c = 3.38, y1 - 0.16
    # Sculpted melted-wax candle with cratered dish pool, 4 wax drips & curved charred wick (matches desk candle realism!)
    wax_prof = [(0.0, -0.006), (0.0145, -0.006), (0.0142, 0.068), (0.0138, 0.072), (0.0128, 0.075),
                (0.0108, 0.0735), (0.0045, 0.070), (0.0, 0.069)]
    turned("shelf_candle_wax", wax_prof, cx_c, cy_c, top, m["candle"], segments=28)
    for dk, (ang, dlen) in enumerate(((0.4, 0.028), (1.9, 0.042), (3.5, 0.022), (5.1, 0.035))):
        rings = []
        for i in range(7):
            t_ = i / 6
            c_ = mathutils.Vector((cx_c + 0.014 * math.cos(ang), cy_c + 0.014 * math.sin(ang), top + 0.073 - dlen * t_))
            out_ = mathutils.Vector((math.cos(ang), math.sin(ang), 0))
            rings.append((c_, out_, out_.cross(mathutils.Vector((0, 0, 1))), (lambda a_, t_=t_: 0.0014 + 0.0013 * t_ * t_), t_))
        swept(f"shelf_candle_drip_{dk}", rings, m["candle"], sides=8)
    turned("shelf_candle_wax_pool", [(0.0, 0.0), (0.022, 0.0), (0.020, 0.003), (0.014, 0.004), (0.0, 0.004)], cx_c, cy_c, top - 0.002, m["candle"], segments=18)
    tube("shelf_candle_wick", area, [(cx_c, cy_c, top + 0.069), (cx_c + 0.0008, cy_c - 0.0005, top + 0.076), (cx_c + 0.0022, cy_c - 0.0012, top + 0.081)],
         0.0009, m["iron"], sides=5)
    empty("light_flame_candle", area, (cx_c + 0.0015, cy_c - 0.0008, top + 0.089), radius=3.0, intensity=0.85)

    # Small antique brass incense ash dish & 2 smoldering Khmer incense sticks beside the shelf candle!
    ix0, iy0, iz0 = 3.22, y1 - 0.16, z + 0.035
    dish_prof = [(0.0, 0.0), (0.028, 0.0), (0.042, 0.010), (0.045, 0.022), (0.042, 0.023), (0.036, 0.010), (0.0, 0.006)]
    turned("studio_incense_dish", dish_prof, ix0, iy0, iz0, m["brass"], segments=24)
    ash_prof = [(0.0, 0.006), (0.034, 0.006), (0.028, 0.014), (0.016, 0.022), (0.0, 0.025)]
    turned("studio_incense_ash", ash_prof, ix0, iy0, iz0, m["incense_ash"], segments=20)
    for k, (dx_, dy_, tx_, ty_) in enumerate(((-0.006, 0.002, 0.14, -0.06), (0.006, -0.003, -0.10, 0.09))):
        _, tip = khmer_incense_stick(f"studio_incense_{k}", (ix0 + dx_, iy0 + dy_, iz0 + 0.020), (tx_, ty_, 1.0), body_len=0.105)
        empty(f"marker_studio_incense_{k}", area, tip)
    # Where the satchel used to sit (it is on the bed in the back room now): real vintage books laid flat.
    flat_specs = (
        ("BK03_LAROUSSE", 0.24, 0.18, 0.035, 0.05),
        ("BK16_GHOST_ANTIQ", 0.22, 0.16, 0.030, -0.08),
        ("BK15_POE_MYSTERY", 0.21, 0.15, 0.028, 0.11),
    )
    for k, (bid, h_b, w_b, t_b, tw) in enumerate(flat_specs):
        zz = z + 0.035 + sum(s[3] for s in flat_specs[:k])
        # Lying flat, spines to the room (-y), Poe's Tales of Mystery face-up by the candle!
        book(f"shelf_flat_book_{k}", frame((-math.sin(tw), math.cos(tw), 0), (-math.cos(tw), -math.sin(tw), 0), (2.33, y1 - 0.17, zz)),
             w_b, h_b, t_b, cover=bid)
    stand_specs = (
        ("BK19_RICKSHAW", 2.62, 0.048, 0.26),
        ("BK25_BUG_JARGAL", 2.675, 0.045, 0.24),
        ("BK04_DICTIONNAIRE", 2.73, 0.058, 0.28),
        ("BK35_CONRAD", 2.792, 0.040, 0.22),
        ("BK37_LORD_WORLD", 2.845, 0.052, 0.27),
    )
    for k, (bid, x, w, h) in enumerate(stand_specs):
        # Standing, spine out to the room (-y).
        book(f"shelf_book_{k}", frame((0, 1, 0), (0, 0, 1), (x, y1 - 0.15, z + 0.035 + h / 2)), 0.22, h, w - 0.003,
             cover=bid)
    lib("ceramic_vase_02", (3.05, y1 - 0.15, z + 0.035), 0, collide=False, scale=0.6, budget=2000)


def build_satchel(satchel):
    """Sora's satchel: a brown leather artist's bag, worn soft at the corners, the flap
    buckled down with two straps, a folded shoulder strap; built round its own origin
    (base centre), front facing the room (-y)."""
    leather = m["satchel_leather"]
    dark = m["leather"]
    w, d, h = 0.36, 0.11, 0.26
    parts = []
    body = box("satchel_body", area, -w / 2, w / 2, -d / 2, d / 2, 0.0, h, leather, edge=0.028)
    body.modifiers["bevel"].segments = 4
    parts.append(body)
    # Gussets: a darker seam strip round each end.
    for s in (-1, 1):
        parts.append(box(f"satchel_gusset_{s}", area, s * w / 2 - 0.004, s * w / 2 + 0.004, -d / 2 + 0.012, d / 2 - 0.012, 0.015, h - 0.01, dark, edge=0.003))
    # The flap: over the top and down the front, rounded at the bottom corners.
    top = box("satchel_flap_top", area, -w / 2 - 0.004, w / 2 + 0.004, -d / 2 - 0.006, d / 2 + 0.004, h - 0.004, h + 0.006, leather, edge=0.004)
    front = box("satchel_flap_front", area, -w / 2 - 0.004, w / 2 + 0.004, -d / 2 - 0.012, -d / 2 - 0.004, h * 0.38, h + 0.004, leather, edge=0.02)
    front.modifiers["bevel"].segments = 4
    parts += [top, front]
    # Two straps down the flap to buckles on the body, with brass frames and tongues.
    for s in (-1, 1):
        x = s * 0.095
        parts.append(box(f"satchel_strap_{s}", area, x - 0.012, x + 0.012, -d / 2 - 0.015, -d / 2 - 0.011, h * 0.3, h + 0.006, dark, edge=0.002))
        parts.append(box(f"satchel_keeper_{s}", area, x - 0.016, x + 0.016, -d / 2 - 0.008, -d / 2 - 0.002, 0.05, 0.075, dark, edge=0.002))
        buckle = [(x - 0.017, -d / 2 - 0.016, 0.09), (x + 0.017, -d / 2 - 0.016, 0.09), (x + 0.017, -d / 2 - 0.016, 0.125), (x - 0.017, -d / 2 - 0.016, 0.125), (x - 0.017, -d / 2 - 0.016, 0.09)]
        parts.append(tube(f"satchel_buckle_{s}", area, buckle, 0.0022, m["brass"], sides=6))
        parts.append(tube(f"satchel_tongue_{s}", area, [(x, -d / 2 - 0.016, 0.107), (x, -d / 2 - 0.02, 0.125)], 0.0014, m["brass"], sides=5))
    # Stitching along the flap edge: a row of small dashes.
    for i in range(30):
        u = -w / 2 + 0.02 + i * (w - 0.04) / 29
        parts.append(box(f"satchel_stitch_{i}", area, u - 0.0035, u + 0.0035, -d / 2 - 0.0125, -d / 2 - 0.011, h * 0.38 + 0.012, h * 0.38 + 0.014, m["string"]))
    # Shoulder strap: D-rings at the ends, the strap folded over the top.
    for s in (-1, 1):
        ring = [(s * (w / 2 + 0.004), math.cos(a) * 0.012, h - 0.03 + math.sin(a) * 0.016) for a in np.linspace(-math.pi / 2, math.pi / 2, 9)]
        parts.append(tube(f"satchel_dring_{s}", area, ring, 0.0022, m["brass"], sides=6))
    strap = [(-w / 2 - 0.006, 0.0, h - 0.03), (-w / 2 - 0.02, 0.01, h + 0.05), (-0.1, 0.03, h + 0.075), (0.1, 0.035, h + 0.07), (w / 2 + 0.02, 0.01, h + 0.04), (w / 2 + 0.006, 0.0, h - 0.03)]
    parts.append(tube("satchel_shoulder_strap", area, strap, 0.006, dark, sides=6))
    for part in parts:
        part.parent = satchel


def ceiling_fan(cx, cy):
    """A 1930s ceiling fan, brass motor and four wooden blades, still tonight; its canopy
    screwed to the underside of a joist, its wire run along the joist to the west wall.
    Blades & arms live under `haunt_fan_rotor` so the Haunting Director can eerily drift
    them off-camera and freeze them dead the instant Sora looks up."""
    wire = [(cx - 0.06, cy, H - 0.172), (0.03, cy, H - 0.172), (0.0135, cy, H - 0.172), (0.0135, 2.15, H - 0.172)]
    tube("fan_wiring", area, wire, 0.0035, m["cord"], sides=5)
    cylinder("fan_rod", area, cx, cy, H - 0.6, H - 0.17, 0.012, m["brass"], verts=8)
    turned("fan_canopy", [(0.0, 0.0), (0.07, 0.0), (0.05, 0.06), (0.0, 0.07)], cx, cy, H - 0.24, m["brass"], segments=20)
    turned("fan_motor", [(0.0, 0.0), (0.09, 0.0), (0.12, 0.04), (0.12, 0.09), (0.09, 0.12), (0.0, 0.13)], cx, cy, H - 0.73, m["brass"], segments=24)
    rotor = empty("haunt_fan_rotor", area, (cx, cy, H - 0.68))
    bpy.context.view_layer.update()
    for k in range(4):
        a = k * math.pi / 2 + 0.3
        blade = box(f"fan_blade_{k}", area, -0.3, 0.3, -0.06, 0.06, -0.006, 0.006, m["rosewood"], edge=0.004)
        blade.location = (cx + math.cos(a) * 0.42, cy + math.sin(a) * 0.42, H - 0.68)
        blade.rotation_euler = (0.12, 0, a)
        attach(blade, rotor)
        arm = box(f"fan_arm_{k}", area, -0.1, 0.1, -0.012, 0.012, -0.006, 0.006, m["brass"])
        arm.location = (cx + math.cos(a) * 0.17, cy + math.sin(a) * 0.17, H - 0.676)
        arm.rotation_euler = (0, 0, a)
        attach(arm, rotor)


def dress_working_studio(tx, ty):
    """An illustrator works here every day: a drying line with sheets, canvases against
    the wall, rolled paper, a tied stack of fresh paper, yesterday's newspapers."""
    a, b = (0.022, 0.6, 2.35), (2.3, 0.022, 2.35)  # at the screw eyes
    line = sag(a, b, 0.06, n=12)
    tube("drying_line", area, line, 0.002, m["string"], sides=4)
    screw_eye("drying_line_eye_w", a, (1, 0, 0))
    screw_eye("drying_line_eye_s", b, (0, 1, 0))
    along = np.array((b[0] - a[0], b[1] - a[1])); along /= np.linalg.norm(along)
    normal = (-along[1], along[0], 0)
    # Sora's ink studies (tools/drawings/ep1.mjs) pegged up to dry, facing into the room.
    for k, (t, study) in enumerate(((0.3, "boats"), (0.55, "palms"), (0.8, "house"))):
        p = line[round(t * (len(line) - 1))]
        ink = drawing(f"M_studio_study_{study}", f"T_studio_study_{study}_BC")
        pegged_sheet(f"drying_sheet_{k}", (p[0], p[1], p[2] - 0.006), (along[0], along[1], 0), normal, 0.3, ink, m["paper"], seed=k)
        for s in (-1, 1):
            box(f"drying_peg_{k}_{s}", area, p[0] + s * 0.1 * along[0] - 0.006, p[0] + s * 0.1 * along[0] + 0.006, p[1] + s * 0.1 * along[1] - 0.004, p[1] + s * 0.1 * along[1] + 0.004, p[2] - 0.035, p[2] + 0.01, m["worn"])
    canvas_back = library_material("rough_linen", "M_canvas_back", colour=(0.56, 0.48, 0.36), tile=0.28)
    for k, (y, w, h) in enumerate(((0.55, 0.5, 0.7), (0.95, 0.45, 0.6))):
        lean = -0.13
        cx = 0.03 + 0.016 * k + h / 2 * math.sin(-lean)
        box(f"canvas_board_{k}", area, cx - 0.004, cx + 0.004, y - w / 2, y + w / 2, 0.0, h, canvas_back, tilt=(0, lean, 0))
        # Wooden stretcher frame bars on the visible back face (+X) so canvases never read as flat slabs
        sb = 0.032
        sx_off = cx + 0.009
        for tag, y0_, y1_, z0_, z1_ in (
            ("bot", y - w / 2, y + w / 2, 0.0, sb),
            ("top", y - w / 2, y + w / 2, h - sb, h),
            ("l", y - w / 2, y - w / 2 + sb, sb, h - sb),
            ("r", y + w / 2 - sb, y + w / 2, sb, h - sb),
            ("mid", y - w / 2 + sb, y + w / 2 - sb, h * 0.5 - 0.014, h * 0.5 + 0.014),
        ):
            # Offset X along the lean angle for each bar's center Z (top leans against west wall x=0)
            zc = (z0_ + z1_) / 2
            bx = 0.03 + 0.016 * k + (h - zc) * math.sin(-lean) + 0.011
            box(f"canvas_stretcher_{k}_{tag}", area, bx - 0.007, bx + 0.007, y0_, y1_, z0_, z1_, m["worn"], tilt=(0, lean, 0), edge=0.002)
    for k in range(6):
        ang = k * math.tau / 6 + rng.uniform(-0.3, 0.3)
        r = 0.05 + 0.02 * (k % 2)
        x, y = 0.35 + r * math.cos(ang), 1.45 + r * math.sin(ang)
        roll = cylinder(f"paper_roll_{k}", area, x, y, 0.04, 0.04 + rng.uniform(0.6, 0.85), rng.uniform(0.018, 0.028), m["paper"] if k % 3 else m["newsprint"], verts=10)
        roll.rotation_euler = (rng.uniform(-0.12, 0.12) + 0.1 * math.sin(ang), rng.uniform(-0.12, 0.12) - 0.1 * math.cos(ang), 0)
    px, py = tx + 0.25, ty - 0.1
    for k in range(14):
        j = rng.uniform(-0.008, 0.008)
        box(f"paper_stack_{k}", area, px - 0.21 + j, px + 0.21 + j, py - 0.15, py + 0.15, k * 0.0035, k * 0.0035 + 0.0025, m["paper"], tilt=(0, 0, rng.uniform(-0.03, 0.03)))
    box("paper_stack_string_a", area, px - 0.215, px + 0.215, py - 0.006, py + 0.006, 0.0, 0.051, m["string"])
    box("paper_stack_string_b", area, px - 0.006, px + 0.006, py - 0.155, py + 0.155, 0.0, 0.052, m["string"])
    for k in range(7):
        box(f"newspaper_{k}", area, 4.0, 4.35, 1.2, 1.45, k * 0.004, k * 0.004 + 0.003, m["newsprint"], tilt=(0, 0, rng.uniform(-0.2, 0.2)))
    # The umbrella stood on its ferrule, leant against the partition: tip on the floor,
    # the folded canopy, the shaft, the crook resting on the boards.
    umbrella = plain("M_umbrella_cloth", (0.03, 0.03, 0.035), rough=0.75)
    tip = np.array((1.25, P1[0] - 0.2, 0.0))
    top = np.array((1.27, P1[0] - 0.03, 0.84))
    at = lambda f: tuple(tip + (top - tip) * f)
    tube("umbrella_ferrule", area, [at(0.0), at(0.09)], 0.004, m["iron"], sides=6, radius_end=0.006)
    tube("umbrella_folded", area, [at(0.09), at(0.3), at(0.78)], 0.035, umbrella, sides=10, radius_end=0.011)
    tube("umbrella_shaft", area, [at(0.78), at(1.0)], 0.0065, m["wood"], sides=8)
    crook = [at(1.0), (top[0], top[1] - 0.01, top[2] + 0.05), (top[0], top[1] - 0.05, top[2] + 0.075), (top[0], top[1] - 0.085, top[2] + 0.05)]
    tube("umbrella_handle", area, crook, 0.0085, m["wood"], sides=8)


# =============================================================== telephone and lantern


def telephone(at):
    """A French magneto wall telephone of the 1920s: walnut backboard, the bell box with
    two nickel gongs, the crank, the transmitter on its arm, the sloped writing shelf and
    battery box, and the earpiece hanging on the switch hook (P06). It faces into the
    airwell (+y). The earpiece matches the one in Sora's hand (src/player/telephoneReceiver.ts)."""
    ax, ay, az = at
    root = empty("interact_telephone", area, (ax, ay, az), action="use", beat="P06")
    def P(u, v, w):
        """Local (u right as seen from the front, v up, w out of the wall) to world."""
        return (ax - u, ay + w, az + v)
    def pbox(name, u0, u1, v0, v1, w0, w1, mat, edge=0.0):
        xa, xb = sorted((ax - u0, ax - u1))
        obj = box(name, area, xa, xb, ay + w0, ay + w1, az + v0, az + v1, mat, edge=edge)
        return attach(obj, root)
    def parent(obj):
        return attach(obj, root)
    walnut = m["rosewood"]
    # Backboard with a shaped crest and foot.
    pbox("telephone_backboard", -0.15, 0.15, -0.42, 0.34, 0.0, 0.022, walnut, edge=0.006)
    pbox("telephone_backboard_crest", -0.11, 0.11, 0.34, 0.4, 0.0, 0.022, walnut, edge=0.01)
    pbox("telephone_backboard_foot", -0.1, 0.1, -0.47, -0.42, 0.0, 0.022, walnut, edge=0.01)
    # Bell box with a raised panel door, hinge and the maker's plate.
    pbox("telephone_bell_box", -0.115, 0.115, 0.04, 0.3, 0.022, 0.13, walnut, edge=0.008)
    pbox("telephone_bell_box_door", -0.09, 0.09, 0.065, 0.275, 0.13, 0.142, walnut, edge=0.006)
    pbox("telephone_bell_box_hinge", -0.115, -0.105, 0.09, 0.25, 0.128, 0.138, m["brass"])
    pbox("telephone_makers_plate", -0.04, 0.04, 0.2, 0.225, 0.142, 0.145, m["brass"], edge=0.001)
    # Two nickel gongs on the box top's front, a striker between them.
    for k, u in enumerate((-0.055, 0.055)):
        g = turned(f"telephone_gong_{k}", [(0.0, 0.0), (0.042, 0.0), (0.045, 0.004), (0.04, 0.02), (0.022, 0.032), (0.0, 0.035)], 0, 0, 0, m["nickel"], segments=24)
        g.location = P(u, 0.31, 0.1)
        g.rotation_euler = (-math.pi / 2, 0, 0)
        parent(g)
    pbox("telephone_striker_rod", -0.003, 0.003, 0.3, 0.355, 0.12, 0.126, m["nickel"])
    s = turned("telephone_striker_ball", [(0.0, 0.0), (0.008, 0.002), (0.009, 0.008), (0.006, 0.014), (0.0, 0.016)], 0, 0, 0, m["nickel"], segments=10)
    s.location = P(0, 0.35, 0.123)
    parent(s)
    # Crank on the right side of the box: shaft, arm and wooden knob.
    shaft = cylinder("telephone_crank_shaft", area, 0, 0, 0, 0.03, 0.006, m["nickel"], verts=8)
    shaft.location = P(-0.13, 0.18, 0.08)
    shaft.rotation_euler = (0, math.pi / 2, 0)
    parent(shaft)
    pbox("telephone_crank_arm", -0.148, -0.14, 0.12, 0.19, 0.072, 0.088, m["nickel"], edge=0.002)
    k = turned("telephone_crank_knob", [(0.0, 0.0), (0.009, 0.0), (0.011, 0.02), (0.008, 0.04), (0.0, 0.042)], 0, 0, 0, m["ebonite"], segments=10)
    k.location = P(-0.148, 0.125, 0.088)
    k.rotation_euler = (-math.pi / 2, 0, 0)
    parent(k)
    # Transmitter: a nickel body on a swan-neck arm, black mouthpiece facing out.
    arm = tube("telephone_transmitter_arm", area, [P(0, 0.08, 0.13), P(0, 0.06, 0.17), P(0, 0.035, 0.19)], 0.007, m["nickel"], sides=8)
    parent(arm)
    body = turned("telephone_transmitter_body", [(0.0, 0.0), (0.04, 0.0), (0.042, 0.01), (0.042, 0.03), (0.036, 0.04), (0.0, 0.04)], 0, 0, 0, m["nickel"], segments=24)
    body.location = P(0, 0.03, 0.19)
    body.rotation_euler = (-math.pi / 2, 0, 0)
    parent(body)
    mouth = turned("telephone_mouthpiece", [(0.0, 0.0), (0.016, 0.0), (0.016, 0.01), (0.022, 0.03), (0.032, 0.045), (0.034, 0.05), (0.026, 0.05), (0.014, 0.012), (0.0, 0.012)], 0, 0, 0, m["ebonite"], segments=24)
    mouth.location = P(0, 0.03, 0.23)
    mouth.rotation_euler = (-math.pi / 2, 0, 0)
    parent(mouth)
    # Sloped writing shelf and the battery box below it.
    pbox("telephone_battery_box", -0.1, 0.1, -0.38, -0.12, 0.022, 0.12, walnut, edge=0.008)
    pbox("telephone_battery_door", -0.08, 0.08, -0.355, -0.15, 0.12, 0.13, walnut, edge=0.006)
    shelf = pbox("telephone_writing_shelf", -0.14, 0.14, -0.12, -0.1, 0.02, 0.2, walnut, edge=0.006)
    shelf.rotation_euler = (math.radians(-12), 0, 0)
    # Binding posts and the line wires leaving the top.
    for kk, u in enumerate((-0.06, 0.06)):
        t = cylinder(f"telephone_terminal_{kk}", area, 0, 0, 0, 0.018, 0.006, m["brass"], verts=10)
        t.location = P(u, 0.385, 0.02)
        parent(t)
        wire = tube(f"telephone_line_wire_{kk}", area, [P(u, 0.4, 0.02), P(u * 0.6, 0.6, 0.012), P(u * 0.4, H - az - 0.25, 0.012)], 0.002, m["cord"], sides=4)
        parent(wire)
    # Switch hook on the left: a nickel lever with a fork; the earpiece hangs in it.
    hook = tube("telephone_switch_hook", area, [P(0.115, 0.22, 0.07), P(0.16, 0.23, 0.07), P(0.175, 0.235, 0.07)], 0.005, m["nickel"], sides=8)
    parent(hook)
    for side in (-1, 1):
        f = tube(f"telephone_hook_fork_{side}", area, [P(0.175, 0.235, 0.07 + side * 0.006), P(0.19, 0.25, 0.07 + side * 0.016), P(0.2, 0.265, 0.07 + side * 0.016)], 0.0035, m["nickel"], sides=6)
        parent(f)
    # The earpiece: a turned ebonite grip with the ear shell at the top, hung by its neck.
    ear = attach(empty("telephone_earpiece", area, P(0.19, 0.14, 0.07)), root)
    E = mathutils.Vector(P(0.19, 0.14, 0.07))
    grip = [(0.0, -0.102), (0.009, -0.102), (0.015, -0.094), (0.018, -0.079), (0.016, -0.063), (0.013, -0.044), (0.013, 0.034), (0.017, 0.056), (0.021, 0.069), (0.021, 0.089), (0.0, 0.094)]
    g = turned("telephone_earpiece_grip", [(r, z + 0.102) for r, z in grip], 0, 0, 0, m["ebonite"], segments=24)
    g.location = (E.x, E.y, E.z - 0.102)
    attach(g, ear)
    shell = [(0.0, -0.012), (0.023, -0.012), (0.039, 0.0), (0.048, 0.016), (0.051, 0.033), (0.05, 0.043), (0.044, 0.046), (0.04, 0.036), (0.0, 0.032)]
    sh = turned("telephone_earpiece_shell", [(r * 0.8, z * 0.8) for r, z in shell], 0, 0, 0, m["ebonite"], segments=28)
    sh.location = (E.x, E.y + 0.01, E.z + 0.092)
    sh.rotation_euler = (-math.pi / 2, 0, 0)
    attach(sh, ear)
    for kk, z in enumerate((-0.087, -0.061, 0.058)):
        band = turned(f"telephone_earpiece_band_{kk}", [(0.0, 0.0), (0.0185, 0.0), (0.0185, 0.004), (0.0, 0.004)], 0, 0, 0, m["nickel"], segments=20)
        band.location = (E.x, E.y, E.z + z)
        attach(band, ear)
    rest = empty("telephone_cord_rest", area, (E.x, E.y, E.z - 0.116))
    attach(rest, ear)
    attach(empty("telephone_cord_terminal", area, P(0.105, 0.06, 0.06)), root)
    collider("telephone", area, ax - 0.2, ax + 0.16, ay, ay + 0.15, az - 0.47, az + 0.4)


def lantern_hook(at):
    """The hurricane lamp hanging on a brass hook (interact_lamp, P04)."""
    hx, hy, hz = at
    lantern = lib("Lantern_01", (hx, hy + 0.12, hz - 0.33), 0, name="interact_lamp", collide=False, action="pickup", item="lamp", budget=5000)
    bpy.context.view_layer.update()
    pts = np.array([tuple(o.matrix_world @ v.co) for o in lantern.children_recursive if o.type == "MESH" for v in o.data.vertices])
    top = float(pts[:, 2].max())
    contact = pts[pts[:, 2] > top - 0.003].mean(axis=0)
    cx, cy = float(contact[0]), float(contact[1])
    box("coat_hook_backplate", area, cx - 0.032, cx + 0.032, hy, hy + 0.016, top - 0.035, top + 0.115, m["brass"], edge=0.009)
    path = [(cx, hy + 0.018, top + 0.064), (cx, hy + 0.085, top + 0.064), (cx, cy - 0.022, top + 0.049)]
    path += [(cx, cy + math.cos(a) * 0.022, top + 0.016 + math.sin(a) * 0.022) for a in np.linspace(math.pi, 2 * math.pi, 13)]
    path.append((cx, cy + 0.022, top + 0.042))
    tube("coat_hook_curved_arm", area, path, 0.006, m["brass"], sides=12)


# =============================================================== back room


def back_room():
    y0, y1 = P2[1], BACK
    # The bed, head against the north wall, under its mosquito net.
    lib("old_bed_frame", (3.85, y1 - 1.05, 0), 0, budget=6000)
    box("mattress", area, 3.42, 4.28, y1 - 1.98, y1 - 0.12, 0.42, 0.56, m["linen"], edge=0.05)
    box("pillow", area, 3.5, 4.2, y1 - 0.55, y1 - 0.16, 0.56, 0.66, m["linen"], edge=0.04)
    box("krama_folded", area, 3.45, 4.25, y1 - 1.9, y1 - 1.45, 0.56, 0.58, m["krama"], edge=0.008)
    gathered_net(3.85, y1 - 1.05)
    # Vintage suitcase set cleanly beside the south doorway (leaves bathroom entrance clear!)
    # with Bram Stoker's Dracula (1897 yellow cloth) resting on top of it.
    lib("vintage_suitcase", (1.62, y0 + 0.26, 0), 180, collide=True, scale=0.45, budget=3000)
    suit_top = surface_z(1.62, y0 + 0.26, 1.0)
    book("bedside_book", frame((math.cos(0.18), math.sin(0.18), 0), (-math.sin(0.18), math.cos(0.18), 0), (1.62, y0 + 0.26, suit_top)),
         0.16, 0.23, 0.032, cover="BK17_DRACULA")
    for k, x in enumerate((3.2, 3.36)):
        box(f"slipper_{k}", area, x - 0.05, x + 0.05, y1 - 2.35, y1 - 2.11, 0.0, 0.025, m["leather"], tilt=(0, 0, rng.uniform(-0.2, 0.2)), edge=0.01)
    framed_picture(2, "POSTER90_8", (W - 0.013, y1 - 2.6, 1.7), (0, -1, 0), 0.5)
    pinned_poster(5, "POSTER90_6", (2.7, y0 + 0.014, 1.7), (-1, 0, 0), 0.42, tilt=0.015)
    # Cracks: from the shutters' corner up to the ceiling, over the wardrobe, and up from
    # the doorway's head.
    crack_decal("back_crack_window", (1.84, y1 - 0.012, 2.86), (0, -1, 0), (-0.32, 0, 1), (0.5, 1.0), 6)
    crack_decal("back_crack_wardrobe", (0.012, y0 + 2.25, 2.78), (1, 0, 0), (0, 0.18, 1), (0.45, 0.9), 7)
    crack_decal("back_crack_door_head", (1.38, y0 + 0.012, 2.8), (0, 1, 0), (0.38, 0, 1), (0.5, 1.0), 0, flip=True)
    # Sora's satchel, left on the foot of the bed (P04: the one thing to fetch in here).
    # Built standing (front -y), laid on its back on the folded krama: the flap faces up.
    satchel = empty("interact_satchel", area, (3.8, y1 - 1.68, 0.58 + 0.054), (-math.pi / 2, 0, math.radians(-14)), action="pickup", item="satchel")
    build_satchel(satchel)
    frame_print("framed_princess", "colour", "A36107", (W - 0.013, y0 + 0.95, 1.7), (0, -1, 0), (0, 0, 1), 0.34)
    # A wardrobe on the west wall: teak, two panelled doors, a cornice.
    wardrobe(0.0, y0 + 1.6)
    # Washstand with a brass basin and a jug; the towel over a rail on its front; the
    # mirror above it.
    ws_y = y0 + 3.3
    cab = lib("painted_wooden_cabinet", (0.33, ws_y, 0), 90, scale=0.75, budget=2500)
    bpy.context.view_layer.update()
    corners = [o.matrix_world @ mathutils.Vector(c) for o in cab.children_recursive if o.type == "MESH" for c in o.bound_box]
    front = max(c.x for c in corners)
    cy0, cy1 = min(c.y for c in corners), max(c.y for c in corners)
    ws_top = surface_z(0.3, ws_y, 1.2)
    lib("brass_pot_02", (0.3, ws_y + 0.07, ws_top), 0, name="washstand_basin", collide=False, scale=0.9, budget=1500)
    lib("jug_01", (0.28, ws_y - 0.2, ws_top), 70, name="washstand_jug", collide=False, budget=2500)
    lib("ornate_mirror_01", (0.013, ws_y, 1.62), 90, collide=False, budget=4000)
    rail_x, rail_z = front + 0.09, ws_top - 0.08   # far enough out that the towel's back fall clears the doors
    for k, yy in enumerate((cy0 + 0.07, cy1 - 0.07)):
        box(f"washstand_rail_bracket_{k}", area, front - 0.005, rail_x + 0.012, yy - 0.012, yy + 0.012, rail_z - 0.012, rail_z + 0.016, m["wood"], edge=0.003)
    tube("washstand_towel_rail", area, [(rail_x, cy0 + 0.05, rail_z), (rail_x, cy1 - 0.05, rail_z)], 0.009, m["wood"], sides=10)
    towel = draped("washstand_towel", -0.17, 0.17, 0.0, 0.0, 0.42, m["linen"], segments=(20, 18))
    towel.location = (rail_x, ws_y - 0.02, rail_z + 0.004)
    towel.rotation_euler = (0, 0, math.pi / 2)
    # The family altar: a high shelf on the north wall with the Emerald Buddha print,
    # candles, an incense bowl and an oil lamp burning low.
    ax0, ax1, az = 0.5, 1.75, 1.72
    box("altar_shelf", area, ax0, ax1, y1 - 0.34, y1 - 0.015, az, az + 0.04, m["rosewood"], edge=0.006)
    box("altar_shelf_valance", area, ax0, ax1, y1 - 0.345, y1 - 0.33, az - 0.08, az + 0.04, m["rosewood"], edge=0.003)
    for x in (ax0 + 0.1, ax1 - 0.1):
        box(f"altar_bracket_{x:.2f}", area, x - 0.02, x + 0.02, y1 - 0.28, y1 - 0.015, az - 0.25, az, m["rosewood"], edge=0.004)
    frame_print("altar_buddha_print", "posters", "A35913", ((ax0 + ax1) / 2, y1 - 0.013, az + 0.42), (1, 0, 0), (0, 0, 1), 0.3)
    ALTAR["candles"] = lib("brass_candleholders", (ax0 + 0.25, y1 - 0.17, az + 0.04), 0, collide=False, scale=0.3, budget=3000)
    ALTAR["bowl"] = lib("wooden_bowl_01", ((ax0 + ax1) / 2, y1 - 0.18, az + 0.04), 0, collide=False, scale=0.6, budget=1500)
    # Sculpted mounded grey incense ash bed inside the altar bowl + 5 realistic multi-part Khmer incense sticks!
    bowl_cx, bowl_cy = (ax0 + ax1) / 2, y1 - 0.18
    ash_bed = turned("altar_incense_ash_bed", [(0.0, 0.0), (0.048, 0.0), (0.042, 0.015), (0.025, 0.028), (0.0, 0.034)], bowl_cx, bowl_cy, az + 0.065, m["incense_ash"], segments=22)
    ALTAR["incense"] = [ash_bed]
    ALTAR["incense_markers"] = []
    for k in range(5):
        bx = bowl_cx + (k - 2) * 0.011
        by = bowl_cy + (k % 2 - 0.5) * 0.012
        bz = az + 0.088
        stick, tip = khmer_incense_stick(
            f"altar_incense_{k}",
            (bx, by, bz),
            ((k - 2) * 0.065, (k % 3 - 1) * 0.055, 1.0),
            body_len=0.112 + (k % 2) * 0.016,
        )
        ALTAR["incense"].append(stick)
        ALTAR["incense_markers"].append(empty(f"marker_altar_incense_{k}", area, tip))
    lamp = ALTAR["lamp"] = lib("vintage_oil_lamp", (ax1 - 0.22, y1 - 0.17, az + 0.04), 0, collide=False, scale=0.45, budget=3000)
    empty("marker_altar_lamp", area, flame_point(lamp))
    ALTAR["vase"] = lib("ceramic_vase_02", (ax0 + 0.08, y1 - 0.15, az + 0.04), 0, collide=False, scale=0.5, budget=1500)
    # A lacquered folding screen half-open beside the bed.
    lib("chinese_screen_panels", (2.7, y0 + 1.2, 0), 205, budget=2500)
    # 1930s bedroom light switch by the doorway wired cleanly up cleats to the unlit ceiling pendant!
    vintage_wall_switch(area, m, turned, "bedroom_switch", (1.36, y0, 1.30), (math.pi / 2, 0, math.pi), toggle_angle_deg=-26)
    tube("bedroom_wiring", area, [(1.36, y0 + 0.008, 1.348), (1.36, y0 + 0.008, H - 0.02), (2.3, (y0 + y1) / 2, H - 0.02)], 0.0035, m["cord"], sides=5)
    for k, z_ in enumerate((1.95, 2.65)):
        cl = turned(f"bedroom_cleat_{k}", [(0.0, 0.0), (0.012, 0.0), (0.012, 0.02), (0.008, 0.024), (0.0, 0.024)], 0, 0, 0, m["porcelain"], segments=10)
        cl.location = (1.36, y0, z_)
        cl.rotation_euler = (-math.pi / 2, 0, 0)
    # A bare bulb with an enamel shade hanging from the ceiling (off).
    tube("back_room_pendant_flex", area, [(2.3, (y0 + y1) / 2, H), (2.3, (y0 + y1) / 2, H - 0.7)], 0.003, m["cord"], sides=5)
    turned("back_room_pendant_shade", [(0.012, 0.0), (0.018, -0.02), (0.12, -0.09), (0.14, -0.1), (0.13, -0.102), (0.11, -0.09), (0.016, -0.025)], 2.3, (y0 + y1) / 2, H - 0.7, m["porcelain"], segments=24)
    # The bakelite lampholder inside the shade, the bulb screwed into it.
    cylinder("back_room_pendant_holder", area, 2.3, (y0 + y1) / 2, H - 0.765, H - 0.7, 0.017, m["ebonite"], verts=14)
    cylinder("back_room_pendant_bulb", area, 2.3, (y0 + y1) / 2, H - 0.82, H - 0.765, 0.026, m["glass"], verts=12)


def wardrobe(x0, y0):
    x1, y1, top = x0 + 0.62, y0 + 1.15, 2.05
    box("wardrobe_body", area, x0 + 0.01, x1, y0, y1, 0.1, top, m["teak"], edge=0.006)
    box("wardrobe_cornice", area, x0, x1 + 0.04, y0 - 0.04, y1 + 0.04, top, top + 0.09, m["teak"], edge=0.012)
    box("wardrobe_plinth", area, x0, x1 + 0.02, y0 - 0.02, y1 + 0.02, 0, 0.1, m["wood"], edge=0.006)
    for s, (a, b) in enumerate(((y0 + 0.03, (y0 + y1) / 2 - 0.004), ((y0 + y1) / 2 + 0.004, y1 - 0.03))):
        box(f"wardrobe_door_{s}", area, x1, x1 + 0.018, a, b, 0.14, top - 0.04, m["teak"], edge=0.004)
        for k, (z0, z1) in enumerate(((0.22, 0.95), (1.05, top - 0.12))):
            box(f"wardrobe_door_{s}_panel_{k}", area, x1 + 0.018, x1 + 0.026, a + 0.07, b - 0.07, z0, z1, m["teak"], edge=0.01)
        box(f"wardrobe_handle_{s}", area, x1 + 0.018, x1 + 0.035, (b if s == 0 else a) - 0.02 * (1 if s == 0 else -1) - 0.006,
            (b if s == 0 else a) - 0.02 * (1 if s == 0 else -1) + 0.006, 1.0, 1.1, m["brass"], edge=0.004)
    collider("wardrobe", area, x0, x1 + 0.04, y0, y1, 0, top + 0.09)


def gathered_net(cx, cy):
    """The mosquito net gathered and tied above the bed, an open gauze bundle."""
    n = 512
    yy, xx = np.mgrid[:n, :n]
    thread = ((xx % 8) < 1) | ((yy % 8) < 1)
    rgba = np.empty((n, n, 4), dtype=np.float32)
    rgba[:, :, :3] = (0.80, 0.77, 0.66)
    rgba[:, :, 3] = np.where(thread, 0.70, 0.045)
    img = bpy.data.images.new("T_studio_net_weave_BC", width=n, height=n, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(TEXTURES, "T_studio_net_weave_BC.png")
    img.file_format = "PNG"
    img.save()
    mat = m["net"]
    mat.use_backface_culling = False
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    tex = nodes.new("ShaderNodeTexImage"); tex.image = img
    bsdf = nodes.get("Principled BSDF")
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    rows, sides = 40, 72
    top = H - 0.14
    vertices, faces, uvs = [], [], []
    for j in range(rows + 1):
        t = j / rows
        radius = float(np.interp(t, [0, .10, .46, .66, .76, 1], [.018, .10, .16, .055, .10, .23]))
        for i in range(sides + 1):
            a = i / sides * math.tau
            pleat = 1 + .19 * math.sin(a * 13 + t * 2) + .07 * math.sin(a * 23 - t * 3)
            r = radius * pleat
            vertices.append((cx + .055 * math.sin(t * 2.5) + math.cos(a) * r, cy + .045 * t + math.sin(a) * r * .72, top - t * 1.11 + .028 * t ** 5 * math.sin(a * 7)))
    for j in range(rows):
        for i in range(sides):
            a = j * (sides + 1) + i
            faces.append((a, a + sides + 1, a + sides + 2, a + 1))
            uvs += [(i / sides * 4, j / rows * 8), (i / sides * 4, (j + 1) / rows * 8), ((i + 1) / sides * 4, (j + 1) / rows * 8), ((i + 1) / sides * 4, j / rows * 8)]
    mesh_object("mosquito_net_folded_gauze", area, vertices, faces, mat, uvs=uvs, smooth=True)
    tie_z = top - .66 * 1.11
    tie_x = cx + .055 * math.sin(.66 * 2.5)
    for dz in (-.008, .008):
        tube("mosquito_net_cotton_tie", area, [(tie_x + math.cos(a) * .063, cy + .03 + math.sin(a) * .046, tie_z + dz) for a in np.linspace(0, math.tau, 33)], .005, m["krama"], sides=6)
    tube("mosquito_net_ceiling_hook", area, [(cx, cy, H), (cx, cy, top - 0.01)], .004, m["brass"], sides=8)


# =============================================================== the scares


def gather(name, objs, at):
    """Parents `objs` under a new empty `name` at `at`, each staying where it is. The game
    keeps whatever is under a `fall_` empty apart (not merged) and moves it as one
    (src/episodes/ep1/prologue/StudioScares.ts); the bake leaves it out
    (tools/areas/bake_studio_lightmap.py)."""
    parent = empty(name, area, at)
    bpy.context.view_layer.update()
    for o in objs:
        world = o.matrix_world.copy()
        o.parent = parent
        o.matrix_world = world
    return parent


def world_bounds(objs):
    """World-space corners (lo, hi) round every mesh in `objs` and under them."""
    bpy.context.view_layer.update()
    corners = [d.matrix_world @ mathutils.Vector(c) for o in objs for d in [o, *o.children_recursive] if d.type == "MESH" for c in d.bound_box]
    lo =mathutils.Vector([min(c[i] for c in corners) for i in range(3)])
    hi = mathutils.Vector([max(c[i] for c in corners) for i in range(3)])
    return lo, hi


def shatter(obj, name, cells, seed, thickness=0.0035):
    """Breaks a thin glazed vessel (one mesh, `obj`) into about `cells` shards: patches of
    its outer skin cut along straight breaks (Voronoi cells round random points, each
    cut leaning a little), each thickened inward, the broken edges the bare body
    (M_studio_biscuit). The shards sit where the vessel is, in one piece; the game shows
    them when it breaks. Returns them."""
    import bmesh
    src = bmesh.new()
    src.from_mesh(obj.data)
    src.transform(obj.matrix_world)
    # The importer splits vertices at UV seams: joined again, a shard is one piece of skin.
    bmesh.ops.remove_doubles(src, verts=src.verts, dist=1e-5)
    src.normal_update()
    lo = [min(v.co[i] for v in src.verts) for i in range(3)]
    hi = [max(v.co[i] for v in src.verts) for i in range(3)]
    cx, cy, top = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, hi[2]
    # Only the outer skin: the walls facing out, the foot, the lip (the inside is the
    # shards' thickness).
    inner = []
    for f in src.faces:
        c, n = f.calc_center_median(), f.normal
        radial = mathutils.Vector((c.x - cx, c.y - cy, 0))
        outside = n.z < -0.6 or (n.z > 0.6 and c.z > top - 0.004) or (
            abs(n.z) <= 0.6 and radial.length > 1e-6 and n.dot(radial.normalized()) > 0)
        if not outside:
            inner.append(f)
    bmesh.ops.delete(src, geom=inner, context="FACES")
    bmesh.ops.delete(src, geom=[v for v in src.verts if not v.link_faces], context="VERTS")
    rgen = np.random.default_rng(seed)
    faces = list(src.faces)
    areas = np.array([f.calc_area() for f in faces])
    seeds = [mathutils.Vector(faces[i].calc_center_median()) for i in rgen.choice(len(faces), size=cells, replace=False, p=areas / areas.sum())]
    glaze = obj.material_slots[0].material
    shards = []
    for k, s_k in enumerate(seeds):
        bm = src.copy()
        for j, s_j in enumerate(seeds):
            if j == k:
                continue
            normal = (s_j - s_k)
            # Pottery breaks more round the throwing rings than up them.
            normal.z *= 1.4
            normal = normal.normalized()
            # Each break leans a little, so the edges are not a perfect cell pattern.
            normal = (normal + mathutils.Vector(rgen.normal(0, 0.12, 3))).normalized()
            mid = (s_k + s_j) / 2
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=mid, plane_no=normal, clear_outer=True)
            if not bm.faces:
                break
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        if len(bm.faces) < 4:
            bm.free()
            continue
        centre = sum((v.co for v in bm.verts), mathutils.Vector()) / len(bm.verts)
        bmesh.ops.translate(bm, verts=bm.verts, vec=-centre)
        mesh = bpy.data.meshes.new(f"{name}_{k}")
        bm.to_mesh(mesh)
        bm.free()
        shard = bpy.data.objects.new(f"{name}_{k}", mesh)
        shard.location = centre
        area.objects.link(shard)
        mesh.materials.append(glaze)
        mesh.materials.append(m["biscuit"])
        solid = shard.modifiers.new("thickness", "SOLIDIFY")
        solid.thickness = thickness
        solid.offset = -1.0          # inward: the glaze stays where it was
        solid.use_rim = True
        solid.material_offset_rim = 1
        solid.use_even_offset = True
        bpy.context.view_layer.update()
        evaluated = shard.evaluated_get(bpy.context.evaluated_depsgraph_get())
        baked = bpy.data.meshes.new_from_object(evaluated)
        shard.modifiers.clear()
        shard.data = baked
        bpy.data.meshes.remove(mesh)
        for poly in baked.polygons:
            poly.use_smooth = poly.material_index == 0
        shards.append(shard)
    src.free()
    return shards


def scare_props():
    """What the studio's scares move (StudioScares.ts, the user's picks on November 24, 2026:
    the picture that falls, the altar that crashes; the shadow needs nothing here).

    - fall_picture: the framed picture on the east wall by the balcony doors, now behind
      glass with a backing board, hanging on a nail that stays in the wall when it falls.
    - fall_altar_*: the family altar in the back room. Its west bracket tears out of the
      wall (fall_altar_bracket), the shelf swings down on the east one (fall_altar_shelf,
      empty at the hinge) and the offerings slide off: the vase (fall_altar_vase, its
      shards inside it, hidden), the three brass candleholders, the incense bowl with its
      sticks, the oil lamp; the Buddha print above is knocked crooked on its nail
      (fall_altar_print, empty at the nail).
    """
    m["biscuit"] = plain("M_studio_biscuit", (0.8, 0.75, 0.66), rough=0.95)
    m["picture_glass"] = plain("M_studio_picture_glass", (0.9, 0.92, 0.92), rough=0.04, alpha=0.1)
    m["picture_glass"].surface_render_method = "BLENDED"
    m["backing"] = plain("M_studio_backing_board", (0.2, 0.13, 0.08), rough=0.9)

    # ---- the picture: frame_print's sheet and mouldings, glass and backing added.
    sheet = bpy.data.objects["poster90_l_1"]
    bars = [bpy.data.objects[f"poster90_l_1_frame_{k}"] for k in ("bottom", "left", "right", "top")]
    lo, hi = world_bounds(bars)
    slo, shi = world_bounds([sheet])
    glass = box("fall_picture_glass", area, slo.x - 0.012, slo.x - 0.0105, slo.y - 0.005, shi.y + 0.005, slo.z - 0.005, shi.z + 0.005, m["picture_glass"])
    # Inside the moulding, so a picture lying on its face still shows its frame round it.
    backing = box("fall_picture_backing", area, shi.x + 0.0004, shi.x + 0.0016, lo.y + 0.03, hi.y - 0.03, lo.z + 0.03, hi.z - 0.03, m["backing"])
    gather("fall_picture", [sheet, *bars, glass, backing], ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, (lo.z + hi.z) / 2))
    # The nail it hung on, hidden by the frame until the frame is gone.
    ny, nz = (lo.y + hi.y) / 2, hi.z - 0.025
    tube("picture_nail", area, [(W - 0.004, ny, nz - 0.004), (hi.x - 0.008, ny, nz)], 0.0016, m["iron"], sides=6)
    turned("picture_nail_head", [(0.0, 0.0), (0.0045, 0.0), (0.0045, 0.0015), (0.0, 0.0015)], 0, 0, 0, m["iron"], segments=10)
    head = bpy.data.objects["picture_nail_head"]
    head.location = (hi.x - 0.008, ny, nz)
    head.rotation_euler = (0, -math.pi / 2, 0)

    # ---- the altar.
    shelf = [bpy.data.objects["altar_shelf"], bpy.data.objects["altar_shelf_valance"]]
    lo, hi = world_bounds(shelf)
    east = bpy.data.objects["altar_bracket_1.65"]
    elo, ehi = world_bounds([east])
    gather("fall_altar_shelf", shelf, ((elo.x + ehi.x) / 2, (lo.y + hi.y) / 2, ehi.z))
    west = bpy.data.objects["altar_bracket_0.60"]
    wlo, whi = world_bounds([west])
    gather("fall_altar_bracket", [west], (wlo + whi) / 2)
    vase = ALTAR["vase"]
    vlo, vhi = world_bounds([vase])
    body = next(o for o in vase.children_recursive if o.type == "MESH")
    shards = shatter(body, "fall_altar_vase_shard", 16, seed=1932)
    gather("fall_altar_vase", [vase, *shards], ((vlo.x + vhi.x) / 2, (vlo.y + vhi.y) / 2, vlo.z))
    holders = sorted((o for o in ALTAR["candles"].children_recursive if o.type == "MESH"), key=lambda o: o.name)
    for k, holder in enumerate(holders):
        hlo, hhi = world_bounds([holder])
        cx_, cy_, cz_ = (hlo.x + hhi.x) / 2, (hlo.y + hhi.y) / 2, hhi.z
        # Sculpt a real melted-wax taper candle & charred wick seated inside each brass candleholder!
        c_h = 0.068 - 0.009 * (k % 3)
        wax_p = [(0.0, -0.008), (0.0095, -0.008), (0.009, c_h - 0.004), (0.0084, c_h), (0.0068, c_h - 0.0015), (0.003, c_h - 0.0045), (0.0, c_h - 0.005)]
        wax_obj = turned(f"altar_candle_wax_{k}", wax_p, cx_, cy_, cz_, m["candle"], segments=20)
        wick_obj = tube(f"altar_candle_wick_{k}", area, [(cx_, cy_, cz_ + c_h - 0.005), (cx_ + 0.001, cy_, cz_ + c_h + 0.005)], 0.0008, m["iron"], sides=5)
        flame_mk = empty(f"marker_altar_candle_{k}", area, (cx_ + 0.001, cy_, cz_ + c_h + 0.012))
        gather(f"fall_altar_candle_{k}", [holder, wax_obj, wick_obj, flame_mk], (cx_, cy_, hlo.z))
    bowl = ALTAR["bowl"]
    blo, bhi = world_bounds([bowl])
    gather("fall_altar_bowl", [bowl, *ALTAR["incense"], *ALTAR["incense_markers"]], ((blo.x + bhi.x) / 2, (blo.y + bhi.y) / 2, blo.z))
    lamp = ALTAR["lamp"]
    llo, lhi = world_bounds([lamp])
    gather("fall_altar_lamp", [lamp], ((llo.x + lhi.x) / 2, (llo.y + lhi.y) / 2, llo.z))
    prints = [bpy.data.objects["altar_buddha_print"], *(bpy.data.objects[f"altar_buddha_print_frame_{k}"] for k in ("bottom", "left", "right", "top"))]
    plo, phi = world_bounds(prints)
    gather("fall_altar_print", prints, ((plo.x + phi.x) / 2, (plo.y + phi.y) / 2, phi.z - 0.012))


# =============================================================== build


def build():
    global area
    bpy.ops.wm.read_factory_settings(use_empty=True)
    area = bpy.data.collections.new("ep1_area_studio")
    bpy.context.scene.collection.children.link(area)
    layer = bpy.context.view_layer.layer_collection.children[area.name]
    bpy.context.view_layer.active_layer_collection = layer
    os.makedirs(TEXTURES, exist_ok=True)
    # The glTF importer reuses an existing "glTF Material Output" group and expects all of
    # its sockets (Iridescence and the rest); kit.gltf_output_group() makes one with only
    # Occlusion, which breaks importing scans that carry occlusion maps. Make the full one first.
    from io_scene_gltf2.blender.com.material_helpers import create_settings_group, get_gltf_node_name
    if get_gltf_node_name() not in bpy.data.node_groups:
        create_settings_group(get_gltf_node_name())
    materials()
    shell()
    front_studio()
    back_room()
    scare_props()
    empty("marker_save_studio", area, (0.42, 2.62, 0.8))
    shrink_prop_textures()
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    faces = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
    print(f"Saved {BLEND}: {len(bpy.data.objects)} objects, {faces} faces before decimation")


build()
