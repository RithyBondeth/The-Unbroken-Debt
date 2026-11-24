"""Episode 1's house after the user's review of November 24, 2026 (five game screenshots):
"so many floating things and bugs ... look at my screenshots carefully", the rooms
"clean but scary, darker", every item "very very detailed and realistic, not cartoon".

What it does, after the rooms are dressed (rebuild-farmstead.py calls `refine()`):
- The cross corridor's oil lamp stood on a 2 cm iron plate (it read as floating): it hangs
  on a cast-iron wall bracket now, a tin reflector behind its flame, soot over its chimney,
  and lower, so the chimney is not 8 cm under the ceiling.
- Sok's gramophone stand stood 8 cm into the bedroom wall: it comes away from the wall.
  The loose wall board where Sok's journal hides (Act II, built by the game: SokRoomModels)
  was placed by offsets from the old house and stood in the middle of the bedroom; it gets
  a marker on the study wall beside the desk (`marker_sok_wall_plank`).
- The store room: a 66 cm cooking pot sat on a 38 cm shelf, a water jar was wedged under
  the bottom board, a jar straddled two uprights. One sturdy teak shelf unit now, and
  every pot, jar and basket scaled to fit the board it stands on.
- The parlour's tea table held a teapot, a sugar pot, two plates and two cups in a line,
  the teapot off the table's edge: a teapot and two cups on a lacquered tray in its middle.
- The bathroom (back block, east), redesigned: a teak duckboard over the wet corner, a big
  glazed water jar under a plank lid with its coconut dipper, a second jar, a bucket and a
  low stool, an enamel basin on its stand, a shelf with soap, comb and a lamp, the mirror
  over it half under a white cloth, towels on a cord; and wet bare footprints going from
  the jar to the door, long black hair over the jar's rim.
- The hall altar: Sok's photograph framed on the altar with a black ribbon and jasmine,
  three fresh joss sticks burning in front of it, a bowl of rice with chopsticks standing
  in it, water, bananas; a low table of fruit, a coconut and lotus beside the altar.
- A rocking chair left facing the corner in Kanha's room.

Blender metres, X east, Y north, Z up.
"""
import math
import os
import re

import bpy
import numpy as np
from mathutils import Matrix, Vector

import house_props as HP
import offerings_kit as ok
import stilt_house as SH
from kit import ROOT, collider, empty, image_material, import_model, library_material, mesh_object, plain
from shrine_craft import Batch, place

F, ZW, T = SH.FLOOR, SH.ZW, SH.T
TEX = os.path.join(ROOT, "art-source", "textures", "ep1")


# ------------------------------------------------------------------ helpers


def _vl():
    bpy.context.view_layer.update()


def _tree(o):
    return [o] + list(o.children_recursive)


def _box(objs):
    pts = []
    for o in objs:
        if o.type == "MESH" and len(o.data.vertices):
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    if not pts:
        return None
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def _delete(objs):
    gone = set()
    for o in list(objs):
        if o is None or o.name not in bpy.data.objects:
            continue
        for c in _tree(o):
            gone.add(c.name)
    for name in gone:
        o = bpy.data.objects.get(name)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    return len(gone)


def _get(*names):
    return [o for o in (bpy.data.objects.get(n) for n in names) if o is not None]


def _roots(pattern):
    rx = re.compile(pattern)
    return [o for o in bpy.data.objects if o.parent is None and rx.search(o.name)]


def _transform(objs, M):
    """Applies M (world space) to the top-most of `objs` (children follow their parents)."""
    names = {o.name for o in objs}
    for o in objs:
        if o.parent is not None and o.parent.name in names:
            continue
        o.matrix_world = M @ o.matrix_world
    _vl()


def _fit(root, x, y, z, w, d, h, turn=None, grow=False):
    """Scales an imported model (its root empty) so it fits a w x d x h space (never larger
    than it is unless `grow`), turns it `turn` degrees, and stands its lowest point on z
    with its middle over (x, y). Returns its new box."""
    if turn is not None:
        root.rotation_euler = (0, 0, math.radians(turn))
    _vl()
    bb = _box(_tree(root))
    if bb is None:
        return None
    size = bb[1] - bb[0]
    k = min(w / max(size.x, 1e-3), d / max(size.y, 1e-3), h / max(size.z, 1e-3))
    if not grow:
        k = min(1.0, k)
    root.scale = tuple(s * k for s in root.scale)
    _vl()
    bb = _box(_tree(root))
    c = (bb[0] + bb[1]) / 2
    root.location += Vector((x - c.x, y - c.y, z - bb[0].z))
    _vl()
    return _box(_tree(root))


def _group_to(objs, x, y, z, turn=0.0):
    """Turns a group of meshes about its own middle and stands it on z at (x, y)."""
    bb = _box(objs)
    c = (bb[0] + bb[1]) / 2
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(turn), 4, "Z") @ Matrix.Translation((-c.x, -c.y, -bb[0].z))
    _transform(objs, M)


def _ray_down(x, y, z_from, ignore=()):
    sc = bpy.context.scene
    deps = bpy.context.evaluated_depsgraph_get()
    o = Vector((x, y, z_from))
    for _ in range(8):
        hit, loc, nrm, idx, obj, mat = sc.ray_cast(deps, o, Vector((0, 0, -1)), distance=4.0)
        if not hit:
            return None
        if obj.name.startswith(("col_", "light_", "marker_")) or obj in ignore or obj.hide_render:
            o = loc - Vector((0, 0, 0.002))
            continue
        return loc.z
    return None


_MATS = {}


def materials(m):
    """The pass's materials on top of the rooms' (made once per run)."""
    if _MATS:
        r = dict(m)
        r.update(_MATS)
        return r
    r = dict(m)
    r["cast_iron"] = plain("M_hr_cast_iron", (0.03, 0.028, 0.026), rough=0.5, metal=0.75)
    r["tin_bright"] = plain("M_hr_tin_reflector", (0.5, 0.48, 0.43), rough=0.3, metal=1.0)
    r["shelf_wood"] = library_material("wood_table_worn", "M_hr_shelf_wood", tint=(0.62, 0.5, 0.4), tile=0.9)
    r["dark_teak"] = library_material("dark_wood", "M_hr_dark_teak", tint=(0.6, 0.48, 0.4), tile=0.6)
    r["duck_wood"] = library_material("weathered_brown_planks", "M_hr_wet_slats", tint=(0.36, 0.3, 0.25), tile=0.9)
    r["jar_glaze"] = plain("M_hr_jar_glaze", (0.085, 0.05, 0.028), rough=0.22)
    r["jar_glaze_ochre"] = plain("M_hr_jar_glaze_ochre", (0.14, 0.09, 0.035), rough=0.32)
    r["jar_foot"] = library_material("clay_plaster", "M_hr_jar_foot", tint=(0.42, 0.3, 0.22), tile=0.3)
    r["dark_water"] = plain("M_hr_jar_water", (0.012, 0.014, 0.012), rough=0.03)
    r["enamel"] = plain("M_hr_enamel", (0.78, 0.77, 0.72), rough=0.22)
    r["enamel_rim"] = plain("M_hr_enamel_rim", (0.05, 0.08, 0.2), rough=0.25)
    r["chip"] = plain("M_hr_enamel_chip", (0.03, 0.025, 0.022), rough=0.6)
    r["soap"] = plain("M_hr_soap", (0.6, 0.52, 0.36), rough=0.45)
    r["lacquer"] = plain("M_hr_red_lacquer", (0.26, 0.03, 0.018), rough=0.28)
    r["gilt"] = plain("M_hr_gilt", (0.42, 0.29, 0.09), rough=0.35, metal=1.0)
    r["porcelain"] = plain("M_hr_porcelain", (0.8, 0.8, 0.76), rough=0.18)
    r["porcelain_blue"] = plain("M_hr_porcelain_blue", (0.08, 0.14, 0.38), rough=0.2)
    r["chopstick"] = plain("M_offering_chopstick", (0.16, 0.085, 0.04), rough=0.55)
    r["ribbon"] = plain("M_hr_mourning_ribbon", (0.014, 0.013, 0.013), rough=0.3)
    r["photo"] = image_material("M_hr_photo_sok", sepia_photo(), rough=0.32)
    r["photo_back"] = library_material("weathered_brown_planks", "M_hr_frame_back", tint=(0.3, 0.24, 0.2), tile=0.4)
    r["hair"] = plain("M_hr_wet_hair", (0.008, 0.007, 0.006), rough=0.28)
    r["cord"] = plain("M_hr_cord", (0.4, 0.36, 0.28), rough=0.9)
    r["lime"] = plain("M_offering_lime", (0.3, 0.42, 0.08), rough=0.45)
    r["orange"] = plain("M_offering_orange", (0.6, 0.27, 0.03), rough=0.5)
    import funeral_under as FU
    r["foot"] = image_material("M_hr_wet_foot", FU.footprint_texture(), rough=0.12, cutout=True, tint=(0.32, 0.3, 0.3))
    r["soot"] = image_material("M_hr_soot", FU.stain_texture("T_ep1_fu_soot_BC", (0.022, 0.021, 0.02), 616), rough=0.95, cutout=True)
    r["hand"] = image_material("M_hr_handprint", FU.handprint_texture(), rough=0.9, cutout=True)
    for key in ("foot", "soot", "hand"):
        r[key].use_backface_culling = False
    krama = bpy.data.materials.get("M_krama")
    r["krama"] = krama or m.get("cotton")
    _MATS.update({k: v for k, v in r.items() if m.get(k) is not v})
    return r


def sepia_photo():
    """Sok's portrait (the funeral's photograph, T_ep1_photo_sok_BC) as a 1930s studio print
    on the home altar: toned sepia, faded to the edges, foxed, the paper border kept."""
    path = os.path.join(TEX, "T_ep1_photo_sok_sepia_BC.png")
    if os.path.exists(path):
        return path
    src = bpy.data.images.load(os.path.join(TEX, "T_ep1_photo_sok_BC.png"), check_existing=True)
    w, h = src.size
    px = np.array(src.pixels[:], dtype=np.float32).reshape(h, w, 4)
    lum = px[..., 0] * 0.3 + px[..., 1] * 0.59 + px[..., 2] * 0.11
    # Contrast up a little in the face and coat, the blue sky gone to a pale studio wall.
    lum = np.clip((lum - 0.5) * 1.18 + 0.52, 0, 1)
    tone = np.stack([lum * 0.98 + 0.03, lum * 0.82 + 0.03, lum * 0.6 + 0.02], axis=-1)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h * 0.52
    r = np.sqrt(((xx - cx) / (w * 0.62)) ** 2 + ((yy - cy) / (h * 0.62)) ** 2)
    fade = np.clip((r - 0.55) / 0.5, 0, 1)[..., None]
    paper = np.array((0.78, 0.7, 0.55), np.float32)
    tone = tone * (1 - fade * 0.75) + paper * fade * 0.75
    rng = np.random.default_rng(1932)
    tone *= (0.94 + 0.06 * rng.random((h, w)))[..., None]
    for k in range(40):     # foxing
        fx, fy, fr = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(2, 9)
        d = np.sqrt((xx - fx) ** 2 + (yy - fy) ** 2)
        tone *= (1 - 0.25 * np.clip(1 - d / fr, 0, 1))[..., None]
    out = np.concatenate([np.clip(tone, 0, 1), np.ones((h, w, 1), np.float32)], axis=-1)
    img = bpy.data.images.new("T_ep1_photo_sok_sepia_BC", w, h)
    img.pixels.foreach_set(out.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return path


def _plane(b, mat, corners, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    b.add(mat, [tuple(c) for c in corners], [(0, 1, 2, 3)], list(uv), smooth=False)


def _footprints(coll, m, name, path, z, rng, stride=0.33, size=(0.11, 0.25)):
    """Wet bare footprints along `path` [(x, y), ...], left and right in turn; `z` is the
    floor's height, or a function of (x, y) giving it."""
    b = Batch(name)
    pts = [Vector((x, y, 0)) for x, y in path]
    total = sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))
    n = max(2, int(total / stride))
    seg, acc = 0, 0.0
    for k in range(n):
        t = (k + 0.5) * total / n
        while seg < len(pts) - 2 and acc + (pts[seg + 1] - pts[seg]).length < t:
            acc += (pts[seg + 1] - pts[seg]).length
            seg += 1
        a, c = pts[seg], pts[seg + 1]
        d = (c - a).normalized()
        p = a + d * (t - acc)
        side = Vector((-d.y, d.x, 0)) * (0.075 if k % 2 else -0.075)
        p = p + side
        ang = math.atan2(d.y, d.x) - math.pi / 2 + rng.normal(0, 0.08)
        w, h = size[0] * rng.uniform(0.95, 1.05), size[1] * rng.uniform(0.95, 1.05)
        cs, sn = math.cos(ang), math.sin(ang)
        zz = z(p.x, p.y) if callable(z) else z
        quad = [(p.x + cs * dx - sn * dy, p.y + sn * dx + cs * dy, zz + 0.0015 + 0.0002 * k)
                for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
        flip = k % 2 == 1
        uv = ((1, 0), (0, 0), (0, 1), (1, 1)) if flip else ((0, 0), (1, 0), (1, 1), (0, 1))
        _plane(b, m["foot"], quad, uv)
    b.build(coll)


def _hair(b, m, root, down, rng, strands=40, length=0.6, spread=0.06):
    """Long black hair from `root`, falling along `down` (a list of offsets the strands
    follow), each strand a thin tube with a little wander."""
    root = Vector(root)
    for k in range(strands):
        off = Vector((rng.normal(0, spread), rng.normal(0, spread), 0))
        pts = [root + off * 0.4]
        L = length * rng.uniform(0.6, 1.1)
        for j, d in enumerate(down):
            f = (j + 1) / len(down)
            wob = Vector((rng.normal(0, 0.008), rng.normal(0, 0.008), 0))
            pts.append(root + off * (0.4 + f) + Vector(d) * (L / length) + wob)
        b.tube(m["hair"], [tuple(p) for p in pts], [0.0012] * (len(pts) - 1) + [0.0006], sides=3)


# ------------------------------------------------------------------ 1. the corridor lamp


def corridor_lamp(coll, m):
    """Image 1: the oil lamp on its wall bracket (it stood on a 2 cm plate)."""
    _delete(_get("corridor_lamp_bracket"))
    lamp = bpy.data.objects.get("house_vintage_oil_lamp_1")
    if lamp is None:
        print("[refine] corridor lamp missing", flush=True)
        return
    face = SH.CORR - T / 2
    bb = _box(_tree(lamp))
    c = (bb[0] + bb[1]) / 2
    # 17 cm out from the boards, its foot at 1.5 m: the chimney clears the ceiling by 25 cm.
    _transform(_tree(lamp), Matrix.Translation((0, face - 0.17 - c.y, F + 1.5 - bb[0].z)))
    bb = _box(_tree(lamp))
    x, y, z = (bb[0].x + bb[1].x) / 2, (bb[0].y + bb[1].y) / 2, bb[0].z
    flame = next((o for o in lamp.children_recursive if "flame" in o.name), None)
    fb = _box([flame]) if flame else None
    fz = (fb[0].z + fb[1].z) / 2 if fb else z + 0.42
    iron, b = m["cast_iron"], Batch("corridor_lamp_bracket")
    # The backplate, screwed to the boards, with a cast boss at either end.
    b.box(iron, (0.07, 0.012, 0.26), (x, face - 0.006, z - 0.05), chamfer=0.004)
    for zz in (z - 0.165, z + 0.065):
        b.lathe(iron, [(0, 0), (0.016, 0), (0.016, 0.004), (0.01, 0.009), (0.004, 0.011), (0, 0.011)],
                xf=place(x, face - 0.012, zz, rx=math.pi / 2), segments=16, tile=0.05)
    # The arm out to the cup, the brace under it curling into a scroll at the plate.
    b.tube(iron, [(x, face - 0.012, z - 0.004), (x, y + 0.05, z - 0.006), (x, y, z - 0.01)], 0.0075, sides=8)
    brace = []
    for t in np.linspace(0, 1, 9):
        brace.append((x, face - 0.012 - (face - 0.012 - (y + 0.035)) * t, z - 0.15 + 0.14 * t ** 0.7))
    b.tube(iron, brace, 0.0065, sides=8)
    scroll = []
    for t in np.linspace(0, 1.35 * math.tau, 26):
        r = 0.032 * (1 - t / (1.6 * math.tau))
        scroll.append((x, face - 0.05 - r * math.sin(t), z - 0.075 + r * math.cos(t)))
    b.tube(iron, scroll, 0.0045, sides=6)
    # The cup the lamp's foot stands in.
    b.lathe(iron, [(0, -0.012), (0.05, -0.012), (0.064, -0.006), (0.068, 0.014), (0.063, 0.016), (0.058, 0.002), (0, 0.002)],
            xf=place(x, y, z), segments=28, tile=0.1)
    # A polished tin reflector behind the flame.
    b.lathe(m["tin_bright"], [(0, 0), (0.09, 0.0), (0.105, 0.014), (0.11, 0.016), (0.108, 0.018), (0.09, 0.006), (0, 0.003)],
            xf=place(x, face - 0.002, fz, rx=math.pi / 2), segments=32, tile=0.2)
    b.build(coll)
    # Soot up the boards and onto the ceiling over the chimney.
    top = bb[1].z
    mesh_object("corridor_lamp_soot", coll, [(x - 0.1, face - 0.001, top - 0.05), (x + 0.1, face - 0.001, top - 0.05),
                                             (x + 0.13, face - 0.001, ZW - 0.004), (x - 0.13, face - 0.001, ZW - 0.004)],
                [(0, 1, 2, 3)], m["soot"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    print("[refine] corridor lamp on its bracket at", round(x, 2), round(y, 2), round(z, 2), flush=True)


# ------------------------------------------------------------------ 2. Sok's study


def study_fixes(coll):
    """Image 2: the gramophone off the bedroom wall; the journal's wall board on a wall."""
    g = bpy.data.objects.get("interact_gramophone")
    if g is not None:
        _transform(_tree(g), Matrix.Translation((0, -0.25, 0)))
        p = g.matrix_world.translation
        _delete(_get("col_gramophone"))
        collider("gramophone", coll, p.x - 0.36, p.x + 0.36, p.y - 0.36, p.y + 0.36, F, F + 1.3)
        print("[refine] gramophone at", round(p.x, 2), round(p.y, 2), flush=True)
    # The study's east wall (the long corridor's west wall), between the desk and the door.
    empty("marker_sok_wall_plank", coll, (-SH.LC - T / 2, 24.05, F + 1.15))


# ------------------------------------------------------------------ 3. the store room


def store_room(coll, m, rng):
    """Image 4: one teak shelf unit on the north wall, everything fitted to its boards."""
    _delete(_roots(r"^store_shelf_(n|s)"))
    face = SH.ROW2 - T / 2
    x0, x1, depth = 0.98, 3.68, 0.42
    y0 = face - depth
    levels, top = (0.1, 0.52, 0.94, 1.36), 1.74
    wood, b = m["shelf_wood"], Batch("store_shelving")
    mid = (x0 + x1) / 2
    for x in (x0 + 0.025, mid, x1 - 0.025):
        for y in (y0 + 0.025, face - 0.025):
            b.box(wood, (0.048, 0.048, top), (x, y, F + top / 2), chamfer=0.005, jitter=0.0015, rng=rng)
        for lv in levels:
            b.box(wood, (0.04, depth - 0.05, 0.05), (x, (y0 + face) / 2, F + lv - 0.045), chamfer=0.003)
        # A cross-brace on each frame's side.
        b.tube(wood, [(x, y0 + 0.05, F + 0.12), (x, face - 0.05, F + 0.5)], 0.011, sides=5)
    for lv in list(levels) + [top]:
        # Three planks a board, a hand's gap between, and a lip along the front.
        for k in range(3):
            w = (depth - 0.02) / 3
            b.box(wood, (x1 - x0 - 0.01, w - 0.008, 0.022), (mid, y0 + 0.01 + w * (k + 0.5), F + lv - 0.011),
                  chamfer=0.003, jitter=0.001, rng=rng)
        if lv != top:
            b.box(wood, (x1 - x0 - 0.01, 0.018, 0.035), (mid, y0 + 0.009, F + lv + 0.005), chamfer=0.003)
    for zz in (0.3, 0.73, 1.15, 1.55):
        b.box(wood, (x1 - x0, 0.02, 0.06), (mid, face - 0.012, F + zz), chamfer=0.003)
    b.build(coll)
    collider("store_shelving", coll, x0, x1, y0, face, F, F + top + 0.02)
    bays = [(x0 + 0.06, mid - 0.04), (mid + 0.04, x1 - 0.06)]
    yc = y0 + depth / 2 + 0.01

    def on(name, level, bay, frac, w, h=None):
        o = bpy.data.objects.get(name)
        if o is None:
            return None
        a, c = bays[bay]
        gap = (levels[level + 1] if level + 1 < len(levels) else top) - levels[level] - 0.05
        return _fit(o, a + (c - a) * frac, yc, F + levels[level] + 0.001, w, depth - 0.07, h or gap)

    # Bottom: the baskets. Second: the cooking pots. Third: jars and the oil tin. Top: bowls.
    on("house_basket_round_7", 0, 0, 0.27, 0.42)
    on("house_wicker_basket_01_8", 0, 0, 0.75, 0.42)
    on("house_wicker_basket_02_12", 0, 1, 0.25, 0.4)
    on("house_basket_deep_13", 0, 1, 0.72, 0.36)
    on("house_ceramic_pot_10", 1, 0, 0.3, 0.4, 0.3)
    on("house_pot_enamel_01_14", 1, 0, 0.78, 0.3)
    on("house_brass_pot_02_15", 1, 1, 0.35, 0.34)
    on("house_jar_plain_9", 2, 0, 0.25, 0.3, 0.3)
    on("house_oil_tin_11", 2, 0, 0.7, 0.22)
    on("house_wooden_bowl_02_16", 3, 1, 0.3, 0.2)
    sb = Batch("store_shelf_things")
    for k in range(2):
        HP.kerosene_tin(sb, m, bays[1][0] + 0.55 + 0.25 * k, yc + 0.02, F + levels[1], rot=rng.uniform(-0.1, 0.1))
    for k in range(4):
        HP.bottle(sb, m, bays[1][0] + 0.12 + 0.11 * k, yc + rng.normal(0, 0.03), F + levels[2], rng, h=rng.uniform(0.22, 0.28))
    for k in range(3):        # a stack of coconut-shell bowls and a rolled mat on the top board
        sb.lathe(m["coconut"], [(0, 0), (0.05, 0), (0.07, 0.025), (0.075, 0.05), (0.068, 0.05), (0.064, 0.026), (0, 0.006)],
                 xf=place(bays[0][0] + 0.25, yc, F + levels[3] + 0.002 + 0.022 * k, rz=rng.uniform(0, 6)), segments=18, tile=0.1)
    sb.build(coll)
    # The water jar wedged under the bottom board, and the jar across the uprights, to the floor.
    for name, (x, y) in (("house_water_jar_4", (5.95, 30.22)), ("house_jar_handles_5", (2.06, 27.76))):
        o = bpy.data.objects.get(name)
        if o is None:
            continue
        bb = _box(_tree(o))
        c = (bb[0] + bb[1]) / 2
        moved = _tree(o) + _get(f"col_{name}")
        _transform(moved, Matrix.Translation((x - c.x, y - c.y, F - bb[0].z)))
    print("[refine] store room shelving", flush=True)


# ------------------------------------------------------------------ 4. the parlour's tea


def tea_set(coll, m):
    """The user (Nov 24): "so many tea pots on the table ... adjust it to fit the table"."""
    root = bpy.data.objects.get("dress_parlour_tea")
    table = bpy.data.objects.get("house_chinese_tea_table_1")
    if root is None or table is None:
        return
    tb = _box(_tree(table))
    cx, cy, top = (tb[0].x + tb[1].x) / 2, (tb[0].y + tb[1].y) / 2, tb[1].z

    def part(stem):
        return [o for o in root.children_recursive if o.name.split(".")[0] == stem]

    _delete(part("tea_set_01_plate_large_circular_03") + part("tea_set_01_plate_large_square_01")
            + part("tea_set_01_sugar_cup_01") + part("tea_set_01_sugar_cup_01_lid"))
    b = Batch("parlour_tea_tray")
    r = 0.25
    b.lathe(m["lacquer"], [(0, 0), (r - 0.01, 0), (r, 0.004), (r + 0.004, 0.022), (r - 0.004, 0.024), (r - 0.012, 0.009), (0, 0.009)],
            xf=place(cx, cy, top), segments=48, tile=0.3)
    b.lathe(m["gilt"], [(r - 0.003, 0.0235), (r + 0.003, 0.0235), (r + 0.003, 0.0255), (r - 0.003, 0.0255)],
            xf=place(cx, cy, top), segments=48, tile=0.3, cap=False)
    b.build(coll)
    tray = top + 0.009
    _group_to(part("tea_set_01_teapot_01") + part("tea_set_01_teapot_01_lid"), cx - 0.01, cy + 0.075, tray, turn=90)
    _group_to(part("tea_set_01_cup_small_01") + part("tea_set_01_saucer_circular_03"), cx - 0.1, cy - 0.115, tray, turn=20)
    _group_to(part("tea_set_01_cup_small_02") + part("tea_set_01_saucer_circular_04"), cx + 0.1, cy - 0.11, tray, turn=-35)
    bb = _box(list(root.children_recursive))
    print("[refine] tea set", [round(v, 3) for v in bb[0]], [round(v, 3) for v in bb[1]], "table", [round(v, 3) for v in tb[0]],
          [round(v, 3) for v in tb[1]], flush=True)


# ------------------------------------------------------------------ 5. the bathroom


def _jar(b, m, x, y, z, rng, radius, height, lid=True):
    """A big glazed Martaban water jar: rounded shoulder, rolled lip, an ochre glaze band
    round the shoulder with four lug handles, the unglazed foot, dark water near the top."""
    R, H = radius, height
    prof = [(0, 0), (R * 0.52, 0), (R * 0.56, 0.02 * H), (R * 0.78, 0.18 * H), (R * 0.96, 0.42 * H), (R, 0.55 * H),
            (R * 0.93, 0.72 * H), (R * 0.7, 0.88 * H), (R * 0.5, 0.95 * H), (R * 0.47, 0.97 * H), (R * 0.52, 0.985 * H),
            (R * 0.53, H), (R * 0.47, H), (R * 0.44, 0.975 * H), (R * 0.44, 0.9 * H)]
    wob = rng.uniform(0, math.tau)
    rad = lambda a, h: 1 + 0.012 * math.sin(3 * a + wob) * math.sin(math.pi * min(1, h / H))
    b.lathe(m["jar_glaze"], prof[3:], xf=place(x, y, z), segments=48, tile=0.6, radial=rad, cap=False)
    b.lathe(m["jar_foot"], prof[:4], xf=place(x, y, z), segments=48, tile=0.4, radial=rad, cap=False)
    b.lathe(m["jar_glaze_ochre"], [(R * 0.955, 0.66 * H), (R * 0.935, 0.7 * H), (R * 0.9, 0.745 * H)],
            xf=place(x, y, z, s=1.006), segments=48, tile=0.3, radial=rad, cap=False)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        px, py = x + math.cos(a) * R * 0.86, y + math.sin(a) * R * 0.86
        b.tube(m["jar_glaze_ochre"], [(px - math.sin(a) * 0.03, py + math.cos(a) * 0.03, z + 0.74 * H),
                                      (px + math.cos(a) * 0.025, py + math.sin(a) * 0.025, z + 0.76 * H),
                                      (px + math.sin(a) * 0.03, py - math.cos(a) * 0.03, z + 0.74 * H)], 0.012, sides=6)
    b.lathe(m["dark_water"], [(R * 0.44, 0.9 * H), (0, 0.9 * H)], xf=place(x, y, z), segments=32, tile=0.2, cap=False)
    return z + H


def bathroom(coll, m, rng):
    """The washroom off the landing, redesigned (the user: "more detail and realistic")."""
    _delete(_roots(r"^bath_"))
    x0, x1 = SH.LAND_X + T / 2, SH.B["x1"] - T
    y0, y1 = SH.ROW2 + T / 2, SH.B["y1"] - T
    flames = []
    # The duckboard over the wet corner: teak slats with a finger's gap on three bearers,
    # the boards under them dark and wet.
    dx0, dy0 = 5.55, 31.3
    b = Batch("bath_duckboard")
    for yy in np.linspace(dy0 + 0.1, y1 - 0.1, 3):
        b.box(m["duck_wood"], (x1 - dx0 - 0.04, 0.07, 0.045), ((dx0 + x1) / 2, yy, F + 0.0225), chamfer=0.004)
    x = dx0
    while x < x1 - 0.05:
        w = rng.uniform(0.085, 0.095)
        b.box(m["duck_wood"], (w, y1 - dy0 - 0.02, 0.024), (x + w / 2, (dy0 + y1) / 2, F + 0.057), chamfer=0.005, jitter=0.0012, rng=rng)
        x += w + 0.014
    b.build(coll)
    wet = mesh_object("bath_wet_boards", coll, [(dx0 - 0.25, dy0 - 0.2, F + 0.002), (x1, dy0 - 0.2, F + 0.002), (x1, y1, F + 0.002),
                                                (dx0 - 0.25, y1, F + 0.002)], [(0, 1, 2, 3)], m["wet_stain"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    wet.data.materials[0].use_backface_culling = True
    deck = F + 0.069
    b = Batch("bath_things")
    # The big jar in the corner under its plank lid, the dipper on the lid; a smaller one.
    jx, jy = x1 - 0.42, y1 - 0.42
    jt = _jar(b, m, jx, jy, deck, rng, 0.37, 0.84)
    for k, off in enumerate((-0.11, 0.0, 0.11)):
        b.box(m["dark_teak"], (0.56, 0.105, 0.022), (jx - 0.08, jy + off, jt + 0.011), xf=None, chamfer=0.003, jitter=0.001, rng=rng)
    b.box(m["dark_teak"], (0.05, 0.36, 0.025), (jx - 0.2, jy, jt + 0.034), chamfer=0.004)
    b.lathe(m["coconut"], [(0, -0.055), (0.05, -0.05), (0.068, -0.025), (0.072, 0.0), (0.066, 0.0), (0, -0.045)],
            xf=place(jx + 0.06, jy - 0.08, jt + 0.08), segments=18, tile=0.1)
    b.tube(m["bamboo"], [(jx + 0.08, jy - 0.06, jt + 0.075), (jx - 0.2, jy - 0.2, jt + 0.03)], 0.008, sides=6)
    _jar(b, m, x1 - 1.06, y1 - 0.26, deck, rng, 0.22, 0.52)
    # The enamel basin on its stand by the south wall, a jug on the floor beside it.
    sx, sy = 5.05, y0 + 0.32
    for k in range(3):
        a = k * math.tau / 3 + 0.5
        b.tube(m["dark_teak"], [(sx + math.cos(a) * 0.2, sy + math.sin(a) * 0.2, F), (sx + math.cos(a) * 0.15, sy + math.sin(a) * 0.15, F + 0.72)],
               0.016, sides=6)
    b.lathe(m["dark_teak"], [(0.17, 0), (0.19, 0), (0.19, 0.025), (0.17, 0.025)], xf=place(sx, sy, F + 0.7), segments=28, tile=0.3)
    b.lathe(m["dark_teak"], [(0.17, 0), (0.185, 0), (0.185, 0.02), (0.17, 0.02)], xf=place(sx, sy, F + 0.3), segments=28, tile=0.3)
    bp = [(0, 0), (0.09, 0), (0.12, 0.01), (0.19, 0.07), (0.205, 0.095), (0.2, 0.1), (0.185, 0.075), (0.115, 0.015), (0, 0.008)]
    b.lathe(m["enamel"], bp, xf=place(sx, sy, F + 0.72), segments=40, tile=0.3)
    b.lathe(m["enamel_rim"], [(0.198, 0.093), (0.207, 0.097), (0.2, 0.102)], xf=place(sx, sy, F + 0.72), segments=40, tile=0.3, cap=False)
    for k in range(5):        # chips in the enamel, black iron showing
        a = rng.uniform(0, math.tau)
        b.box(m["chip"], (0.012, 0.004, 0.008), (sx + math.cos(a) * 0.197, sy + math.sin(a) * 0.197, F + 0.81),
              xf=None, chamfer=0.001)
    b.lathe(m["dark_water"], [(0.15, 0.04), (0, 0.04)], xf=place(sx, sy, F + 0.72), segments=24, tile=0.1, cap=False)
    # The shelf on the east wall, south of the window: soap, a comb, a bottle, a lamp.
    shy0, shy1, shz = 30.9, 31.7, F + 1.22
    b.box(m["dark_teak"], (0.2, shy1 - shy0, 0.025), (x1 - 0.1, (shy0 + shy1) / 2, shz - 0.0125), chamfer=0.004)
    for yy in (shy0 + 0.08, shy1 - 0.08):
        b.box(m["dark_teak"], (0.16, 0.025, 0.025), (x1 - 0.08, yy, shz - 0.05), chamfer=0.003)
        b.tube(m["dark_teak"], [(x1 - 0.01, yy, shz - 0.16), (x1 - 0.15, yy, shz - 0.03)], 0.01, sides=5)
    b.box(m["soap"], (0.06, 0.09, 0.03), (x1 - 0.1, shy0 + 0.14, shz + 0.015), chamfer=0.01)
    b.lathe(m["coconut"], [(0, 0), (0.045, 0), (0.06, 0.012), (0.058, 0.016), (0, 0.006)], xf=place(x1 - 0.1, shy0 + 0.14, shz), segments=16, tile=0.1)
    b.box(m["dark_teak"], (0.012, 0.13, 0.04), (x1 - 0.1, shy0 + 0.3, shz + 0.006), chamfer=0.002)       # comb
    for k in range(14):
        b.box(m["dark_teak"], (0.004, 0.0025, 0.03), (x1 - 0.1, shy0 + 0.245 + k * 0.0085, shz - 0.002))
    HP.bottle(b, m, x1 - 0.1, shy0 + 0.45, shz, rng, h=0.18)
    b.lathe(m["clay_lamp"], [(0, 0), (0.035, 0), (0.05, 0.012), (0.055, 0.028), (0.045, 0.03), (0, 0.022)],
            xf=place(x1 - 0.1, shy1 - 0.12, shz), segments=18, tile=0.1, radial=lambda a, h: 1 + 0.25 * max(0.0, math.cos(a)) ** 6)
    flames.append(Vector((x1 - 0.1 + 0.052, shy1 - 0.12, shz + 0.04)))
    # Long black hair over the big jar's rim, down into the water and down its side.
    _hair(b, m, (jx - 0.04, jy - 0.2, jt + 0.004), [(0, -0.05, -0.04), (0, -0.1, -0.13), (0, -0.16, -0.27), (0, -0.19, -0.42),
                                                  (0, -0.18, -0.56), (0, -0.13, -0.72)], rng, strands=70, length=0.72, spread=0.03)
    b.build(coll)
    # The mirror over the shelf, a white cloth slipping off it (the house mourns: mirrors are
    # covered after a death).
    mirror = import_model(coll, "ornate_mirror_01", (x1 - 0.02, (shy0 + shy1) / 2, shz + 0.25), rot_deg=-90, name="bath_mirror",
                          collide=False)
    mb = _fit(mirror, x1 - 0.05, (shy0 + shy1) / 2, shz + 0.18, 0.15, 0.5, 0.62)
    if mb:
        _transform(_tree(mirror), Matrix.Translation((x1 - 0.004 - mb[1].x, 0, 0)))
        mb = _box(_tree(mirror))
        cloth = Batch("bath_mirror_cloth")
        my0, my1, mz1 = mb[0].y - 0.02, mb[1].y + 0.02, mb[1].z + 0.02
        ph = rng.uniform(0, 6, 3)

        def pt(u, v):
            yy = my0 + (my1 - my0) * u
            hang = 0.62 * (0.55 + 0.45 * u)       # slipped: one side hangs lower, the other shows the glass
            zz = mz1 - hang * v - 0.04 * math.sin(u * 3 + ph[0]) * v
            out = 0.012 + 0.03 * v ** 1.3 * (0.6 + 0.4 * math.sin(u * 17 + ph[1])) + 0.01 * math.sin(u * 31 + ph[2]) * v
            return (x1 - 0.004 - (mb[1].x - mb[0].x) - out, yy, zz)

        cloth.grid(m["linen"], pt, 20, 18, uv=lambda u, v: (u * 2, v * 2))
        for o in cloth.build(coll).values():
            o.data.materials[0].use_backface_culling = False
    # The bucket and the low stool on the boards.
    bucket = import_model(coll, "wooden_bucket_02", (6.2, 32.55, deck), rot_deg=40, name="bath_bucket", collide=False)
    kb = _fit(bucket, 6.2, 32.55, deck, 0.34, 0.34, 0.34)
    if kb:
        collider("bath_bucket", coll, kb[0].x, kb[1].x, kb[0].y, kb[1].y, F, kb[1].z)
    stool = import_model(coll, "wooden_stool_01", (6.55, 32.0, deck), rot_deg=15, name="bath_stool", collide=False)
    _fit(stool, 6.6, 31.95, deck, 0.38, 0.38, 0.24, grow=False)
    jug = import_model(coll, "jug_01", (sx + 0.32, sy + 0.1, F), rot_deg=-60, name="bath_jug", collide=False)
    _fit(jug, sx + 0.33, sy + 0.08, F, 0.2, 0.2, 0.22)
    # Two krama towels on a cord along the south wall.
    cy = y0 + 0.07
    b = Batch("bath_cord")
    b.tube(m["cord"], [(5.7, cy, F + 1.62), (6.6, cy, F + 1.6), (7.6, cy, F + 1.62)], 0.0025, sides=4)
    for xx in (5.7, 7.6):
        b.tube(m["iron"], [(xx, y0, F + 1.62), (xx, cy + 0.01, F + 1.62)], 0.004, sides=5)
    b.build(coll)
    for k, (a, c) in enumerate(((5.9, 6.35), (6.75, 7.25))):
        HP.hung_cloth(coll, m, m["krama"], f"bath_krama_{k}", (a, cy, F + 1.61), (c, cy, F + 1.61), 0.55 + 0.08 * k, folds=6,
                      rng=np.random.default_rng(90 + k))
    # Wet bare feet from the jar across the boards, out of the door.
    _footprints(coll, m, "bath_wet_feet", [(6.95, 32.95), (6.1, 32.85), (5.4, 32.85), (4.2, 32.85), (3.5, 32.5)],
                lambda x, y: deck if x > dx0 - 0.01 and y > dy0 else F, rng)
    collider("bath_jar", coll, jx - 0.37, jx + 0.37, jy - 0.37, jy + 0.37, F, F + 0.9)
    collider("bath_jar_small", coll, x1 - 1.28, x1 - 0.84, y1 - 0.48, y1, F, F + 0.6)
    collider("bath_basin", coll, sx - 0.22, sx + 0.22, sy - 0.22, sy + 0.22, F, F + 0.82)
    print("[refine] bathroom redesigned", flush=True)
    return flames


# ------------------------------------------------------------------ 6. the hall altar


def _photo_frame(b, m, cx, y, z, w, h, lean, rng):
    """A dark teak frame (moulded bars, a gilt fillet), Sok's print in it, a strut behind,
    standing on the altar leaning back by `lean` radians."""
    M = Matrix.Translation((cx, y, z)) @ Matrix.Rotation(-lean, 4, "X")
    bar, d = 0.032, 0.022
    for (sx, sz, px, pz) in ((w, bar, 0, bar / 2), (w, bar, 0, h - bar / 2), (bar, h - 2 * bar, -w / 2 + bar / 2, h / 2),
                             (bar, h - 2 * bar, w / 2 - bar / 2, h / 2)):
        b.box(m["dark_teak"], (sx, d, sz), (px, 0, pz), xf=M, chamfer=0.006)
    inner_w, inner_h = w - 2 * bar, h - 2 * bar
    for (sx, sz, px, pz) in ((inner_w, 0.006, 0, bar + 0.003), (inner_w, 0.006, 0, h - bar - 0.003),
                             (0.006, inner_h, -inner_w / 2 + 0.003, h / 2), (0.006, inner_h, inner_w / 2 - 0.003, h / 2)):
        b.box(m["gilt"], (sx, d * 0.6, sz), (px, -0.002, pz), xf=M)
    b.box(m["photo_back"], (inner_w, 0.006, inner_h), (0, 0.007, h / 2), xf=M)
    q = [M @ Vector(p) for p in ((-inner_w / 2 + 0.006, -0.0005, bar + 0.006), (inner_w / 2 - 0.006, -0.0005, bar + 0.006),
                                 (inner_w / 2 - 0.006, -0.0005, h - bar - 0.006), (-inner_w / 2 + 0.006, -0.0005, h - bar - 0.006))]
    _plane(b, m["photo"], q)
    # The strut behind, from the back board down to the stand.
    b.tube(m["photo_back"], [tuple(M @ Vector((0, 0.013, h * 0.55))), (cx, y + 0.13, z + 0.004)], 0.007, sides=5)
    # The black mourning ribbon: a band across each top corner, a rosette at the top.
    for s in (-1, 1):
        a = M @ Vector((s * (w / 2 - 0.09), -0.014, h + 0.004))
        c = M @ Vector((s * (w / 2 + 0.004), -0.014, h - 0.09))
        b.sweep(m["ribbon"], [tuple(a), tuple((a + c) / 2 + M.to_3x3() @ Vector((0, -0.004, 0))), tuple(c)],
                tuple(M.to_3x3() @ Vector((0, -1, 0))), [0.032, 0.032, 0.032], 0.002)
    top = M @ Vector((0, -0.016, h - 0.005))
    for k in range(10):
        a = k * math.tau / 10
        tip = top + M.to_3x3() @ Vector((math.cos(a) * 0.035, -0.006, math.sin(a) * 0.03))
        b.tube(m["ribbon"], [tuple(top), tuple(tip)], [0.012, 0.004], sides=4, cap_end=True)
    # Jasmine strung over the frame, sagging down both sides.
    pts = []
    for t in np.linspace(0, 1, 15):
        u = t * 2 - 1
        pts.append(tuple(M @ Vector((u * (w / 2 + 0.012), -0.022 - 0.01 * (1 - u * u), h - 0.02 - 0.17 * abs(u) ** 2.2))))
    ok.jasmine_string(b, m, pts, rng)
    return M


def altar(coll, m, rng):
    """Sok's photograph on the hall altar with incense before it, and more offerings."""
    cab = bpy.data.objects.get("hall_altar_cabinet")
    if cab is None:
        print("[refine] altar missing", flush=True)
        return []
    cb = _box([cab])
    ax0, ax1, ay0, ay1 = cb[0].x, cb[1].x, cb[0].y, cb[1].y
    upper = cb[1].z
    # The step in front of the raised top: where the rays first find the lower top.
    step_z, step_y1 = None, ay0
    for yy in np.linspace(ay0 + 0.02, ay1 - 0.02, 28):
        zz = _ray_down(-0.15, yy, upper + 0.5)
        if zz is None:
            continue
        if zz < upper - 0.1:
            step_z, step_y1 = zz, yy
        else:
            break
    if step_z is None:
        step_z, step_y1 = upper - 0.35, ay0 + 0.25
    print("[refine] altar top", round(upper, 3), "step", round(step_z, 3), "to y", round(step_y1, 3), flush=True)
    b = Batch("hall_altar_offerings")
    # Sok's photograph at the back of the raised top, between the candlesticks.
    wall = SH.ALTAR_Y - T / 2
    pw, ph = 0.3, 0.4
    # On a small lacquered riser, so his face shows over the incense pot.
    py = min(ay1 - 0.08, wall - 0.09)
    # A three-step teak stand, gilt along each step's edge (glossy red lacquer caught the
    # altar lamp and read white in the game).
    z0 = upper
    for k, (wd, hz) in enumerate(((0.38, 0.07), (0.34, 0.07), (0.3, 0.065))):
        b.box(m["dark_teak"], (wd, 0.125 - 0.012 * k, hz), (0.0, py + 0.02, z0 + hz / 2), chamfer=0.006)
        b.box(m["gilt"], (wd + 0.003, 0.004, 0.008), (0.0, py + 0.02 - (0.125 - 0.012 * k) / 2 - 0.001, z0 + hz - 0.008))
        z0 += hz
    _photo_frame(b, m, 0.0, py, z0 + 0.001, pw, ph, 0.12, rng)
    # Three fresh joss sticks burning in the brass pot before it.
    brass = bpy.data.objects.get("hall_altar_brassware")
    rim, pot_y = upper + 0.09, (ay0 + ay1) / 2 + 0.1
    if brass is not None:
        vs = [brass.matrix_world @ v.co for v in brass.data.vertices]
        near = [v for v in vs if abs(v.x) < 0.09 and v.z < upper + 0.16]
        if near:
            rim = max(v.z for v in near)
            pot_y = sum(v.y for v in near) / len(near)
    for k, (dx, lean) in enumerate(((-0.018, -0.08), (0.0, 0.0), (0.018, 0.08))):
        ok.joss_stick(b, m, (dx, pot_y + 0.005 * k, rim - 0.03), (lean, -0.06, 1), 0.23, rng, burnt=0.22 + 0.06 * k, ash_curl=True)
    # On the step: a glass of water, rice with chopsticks standing in it, a cup of tea, bananas.
    sy = (ay0 + step_y1) / 2 + 0.005
    ok.small_cup(b, m, place(ax0 + 0.08, sy, step_z), rng, radius=0.028, height=0.05, liquid="water")
    rx = -0.19
    b.lathe(m["porcelain"], [(0, 0), (0.025, 0), (0.028, 0.006), (0.05, 0.035), (0.052, 0.05), (0.048, 0.05), (0.046, 0.036),
                             (0.024, 0.01), (0, 0.009)], xf=place(rx, sy, step_z), segments=28, tile=0.1)
    b.lathe(m["porcelain_blue"], [(0.05, 0.04), (0.0515, 0.046), (0.0505, 0.047)], xf=place(rx, sy, step_z, s=1.004), segments=28, tile=0.1, cap=False)
    b.lathe(m["rice"], [(0.047, 0.044), (0.03, 0.058), (0, 0.064)], xf=place(rx, sy, step_z), segments=24, tile=0.05)
    for s in (-1, 1):
        b.tube(m["chopstick"], [(rx + s * 0.006, sy, step_z + 0.04), (rx + s * 0.009, sy - 0.004, step_z + 0.23)], [0.0033, 0.0021], sides=6, cap_end=True)
    ok.small_cup(b, m, place(0.14, sy, step_z), rng, radius=0.024, height=0.035, liquid="water")
    b.lathe(m["gilt"], [(0, 0), (0.03, 0), (0.03, 0.02), (0.1, 0.035), (0.105, 0.04), (0, 0.032)], xf=place(ax1 - 0.13, sy, step_z), segments=28, tile=0.1)
    ok.bananas(b, m, place(ax1 - 0.16, sy, step_z + 0.03, rz=0.4), rng, count=5, length=0.1)
    b.build(coll)
    # Beside the altar (west), a low table of offerings where two baskets stood.
    _delete(_get("prop_wicker_basket_02.001", "prop_wicker_basket_02.002"))
    flames = []
    tx, ty = ax0 - 0.5, ay1 - 0.3
    table = import_model(coll, "small_wooden_table_01", (tx, ty, F), rot_deg=0, name="hall_offering_table", collide=False)
    tb = _fit(table, tx, ty, F, 0.6, 0.45, 0.48, grow=True)
    if tb:
        collider("hall_offering_table", coll, tb[0].x, tb[1].x, tb[0].y, tb[1].y, F, tb[1].z)
        tt = tb[1].z
        tb2 = Batch("hall_side_offerings")
        fx, fy = tx + 0.13, ty + 0.06
        tb2.lathe(m["gilt"], [(0, 0), (0.06, 0), (0.06, 0.01), (0.025, 0.03), (0.025, 0.07), (0.14, 0.09), (0.145, 0.1), (0, 0.095)],
                  xf=place(fx, fy, tt), segments=32, tile=0.2)
        ok.coconut(tb2, m, place(tx - 0.16, ty + 0.08, tt, rz=0.2), rng)
        for k in range(5):
            a = k * math.tau / 5
            fr = [(0, -0.034)] + [(0.034 * math.sin(t), -0.034 * math.cos(t)) for t in np.linspace(0.25, math.pi - 0.25, 8)] + [(0, 0.034)]
            tb2.lathe(m["orange"], fr, xf=place(fx + math.cos(a) * 0.075, fy + math.sin(a) * 0.075, tt + 0.13), segments=14, tile=0.1)
        fr = [(0, -0.032)] + [(0.032 * math.sin(t), -0.032 * math.cos(t)) for t in np.linspace(0.25, math.pi - 0.25, 8)] + [(0, 0.032)]
        tb2.lathe(m["orange"], fr, xf=place(fx, fy, tt + 0.18), segments=14, tile=0.1)
        # Lotus buds in a glass, and a lit candle in a dish.
        tb2.lathe(m["glass"], [(0, 0), (0.03, 0), (0.032, 0.14), (0.029, 0.14), (0.027, 0.004), (0, 0.004)], xf=place(tx - 0.05, ty - 0.12, tt),
                  segments=18, tile=0.1, cap=False)
        for k in range(3):
            ok.lotus_bud(tb2, m, (tx - 0.05 + (k - 1) * 0.012, ty - 0.12, tt + 0.13 + 0.12 + 0.02 * k),
                         ((k - 1) * 0.15, 0.05, 1), rng, size=0.07, stem=0.12)
        ok.candle_dish(tb2, m, place(tx - 0.2, ty - 0.14, tt), rng, radius=0.045)
        flames.append(ok.candle(tb2, m, place(tx - 0.2, ty - 0.14, tt + 0.006), rng, height=0.08, radius=0.011, melt=0.6))
        tb2.build(coll)
        bananas = import_model(coll, "bananas", (tx + 0.13, ty - 0.15, tt), rot_deg=10, name="hall_offering_bananas", collide=False)
        _fit(bananas, tx + 0.13, ty - 0.15, tt + 0.001, 0.24, 0.12, 0.1)
    print("[refine] altar: photograph, incense, offerings", flush=True)
    return flames


# ------------------------------------------------------------------ 7. the rocking chair


def rocking_chair(coll):
    """A rocking chair left facing the corner of Kanha's room."""
    chair = import_model(coll, "Rockingchair_01", (7.35, 26.8, F), rot_deg=135, name="kanha_rocking_chair", collide=False)
    bb = _fit(chair, 7.38, 26.78, F, 1.05, 1.05, 1.1, turn=135)
    if bb:
        collider("kanha_rocking_chair", coll, bb[0].x, bb[1].x, bb[0].y, bb[1].y, F, F + 0.6)


def old_pieces(coll, m, rng):
    """The old house's last box-built pieces: the corridor bench (a painted bench now), the
    store's rice bin (a panelled chest with a hasp), the hall clock's shelf (brackets)."""
    old = _get("corridor_bench") + [o for o in bpy.data.objects if o.name.startswith("corridor_bench_leg")]
    if old:
        bb = _box(old)
        _delete(old)
        bench = import_model(coll, "painted_wooden_bench", ((bb[0].x + bb[1].x) / 2, (bb[0].y + bb[1].y) / 2, F), rot_deg=0,
                             name="corridor_bench", collide=False)
        nb = _fit(bench, (bb[0].x + bb[1].x) / 2, (bb[0].y + bb[1].y) / 2 + 0.02, F, bb[1].x - bb[0].x + 0.1, 0.42, 0.5, grow=True)
        print("[refine] corridor bench", nb, flush=True)
    lid, body = bpy.data.objects.get("store_rice_bin_lid"), bpy.data.objects.get("store_rice_bin")
    if lid and body:
        bb = _box([body, lid])
        _delete([lid, body] + [o for o in bpy.data.objects if o.name.startswith("store_rice_bin_foot")])
        x0, x1, y0, y1, z1 = bb[0].x, bb[1].x, bb[0].y, bb[1].y, bb[1].z
        b, wood = Batch("store_rice_bin"), m["dark_teak"]
        for x in (x0 + 0.035, x1 - 0.035):
            for y in (y0 + 0.035, y1 - 0.035):
                b.box(wood, (0.07, 0.07, z1 - F - 0.04), (x, y, (F + z1 - 0.04) / 2), chamfer=0.006)
        for z in (F + 0.1, z1 - 0.1):
            for (sx, sy, cx, cy) in ((x1 - x0 - 0.1, 0.05, (x0 + x1) / 2, y0 + 0.03), (x1 - x0 - 0.1, 0.05, (x0 + x1) / 2, y1 - 0.03),
                                     (0.05, y1 - y0 - 0.1, x0 + 0.03, (y0 + y1) / 2), (0.05, y1 - y0 - 0.1, x1 - 0.03, (y0 + y1) / 2)):
                b.box(wood, (sx, sy, 0.07), (cx, cy, z), chamfer=0.005)
        hz = (F + 0.13, z1 - 0.13)
        for (sx, sy, cx, cy) in ((x1 - x0 - 0.12, 0.02, (x0 + x1) / 2, y0 + 0.045), (x1 - x0 - 0.12, 0.02, (x0 + x1) / 2, y1 - 0.045),
                                 (0.02, y1 - y0 - 0.12, x0 + 0.045, (y0 + y1) / 2), (0.02, y1 - y0 - 0.12, x1 - 0.045, (y0 + y1) / 2)):
            b.box(m["shelf_wood"], (sx, sy, hz[1] - hz[0]), (cx, cy, (hz[0] + hz[1]) / 2), chamfer=0.003)
        b.box(wood, (x1 - x0 + 0.04, y1 - y0 + 0.04, 0.045), ((x0 + x1) / 2, (y0 + y1) / 2, z1 - 0.0225), chamfer=0.008)
        b.box(wood, (x1 - x0 - 0.1, y1 - y0 - 0.1, 0.02), ((x0 + x1) / 2, (y0 + y1) / 2, z1 + 0.008), chamfer=0.005)
        b.box(m["cast_iron"], (0.05, 0.012, 0.11), ((x0 + x1) / 2, y0 - 0.025, z1 - 0.06), chamfer=0.003)
        b.lathe(m["cast_iron"], [(0, 0), (0.018, 0), (0.018, 0.01), (0, 0.01)], xf=place((x0 + x1) / 2, y0 - 0.032, z1 - 0.12, rx=math.pi / 2),
                segments=12, tile=0.05)
        b.build(coll)
    shelf = bpy.data.objects.get("clock_shelf")
    if shelf:
        sb = _box([shelf])
        b = Batch("clock_shelf_brackets")
        for x in (sb[0].x + 0.08, sb[1].x - 0.08):
            b.box(m["dark_teak"], (0.025, sb[1].y - sb[0].y - 0.02, 0.025), (x, (sb[0].y + sb[1].y) / 2 + 0.01, sb[0].z - 0.0125), chamfer=0.003)
            b.tube(m["dark_teak"], [(x, sb[1].y - 0.005, sb[0].z - 0.16), (x, sb[0].y + 0.04, sb[0].z - 0.02)], 0.009, sides=5)
            b.box(m["dark_teak"], (0.025, 0.02, 0.16), (x, sb[1].y - 0.01, sb[0].z - 0.08), chamfer=0.003)
        b.build(coll)
    print("[refine] old pieces remade", flush=True)


def refine(coll, m, rng):
    m = materials(m)
    corridor_lamp(coll, m)
    study_fixes(coll)
    store_room(coll, m, rng)
    tea_set(coll, m)
    flames = bathroom(coll, m, rng)
    flames += altar(coll, m, rng)
    rocking_chair(coll)
    old_pieces(coll, m, rng)
    return flames
