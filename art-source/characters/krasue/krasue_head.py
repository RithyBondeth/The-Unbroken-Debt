"""The Krasue's head from CC0 MakeHuman anatomy (the female base Sora's source uses).

A real skull, face, ears, lids, lips and teeth, made gaunt and severed at the
neck, in the Krasue rig's frame (metres, +Y facing, +Z up, twice life size as
the old sculpt was). Sources: art-source/library/makehuman-sora (base mesh,
female targets, skin), makehuman-sok (the mouth-open expression target) and
makehuman-driver (the eye texture); see tools/characters/fetch-sora-source.py.
"""
import gzip
import math
from pathlib import Path

import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / 'art-source/library'
SORA, SOK, DRIVER = LIB / 'makehuman-sora', LIB / 'makehuman-sok', LIB / 'makehuman-driver'
SKIN_TEXTURE = SORA / 'young_lightskinned_female_diffuse3.png'
EYE_TEXTURE = DRIVER / 'brown_eye.png'

# MakeHuman decimetres (Y up, face +Z) → the rig's frame: the eyes at the old
# sculpt's eye height and depth, the scale of its chin-to-crown.
EYE_Y, EYE_Z = 5.7939, 1.1016
SCALE = .263
NECK_CUT = 4.47  # just under the jaw: the head came away here


def to_rig(v):
    return Vector((v.x * SCALE, (v.z - EYE_Z) * SCALE + .113, (v.y - EYE_Y) * SCALE + .027))


def _read():
    verts, uvs, faces = [], [], {}
    group = ''
    for line in (SORA / 'base.obj').read_text().splitlines():
        a = line.split()
        if not a:
            continue
        if a[0] == 'v':
            verts.append(Vector(map(float, a[1:4])))
        elif a[0] == 'vt':
            uvs.append(tuple(map(float, a[1:3])))
        elif a[0] == 'g':
            group = a[1]
        elif a[0] == 'f':
            p = [x.split('/') for x in a[1:]]
            faces.setdefault(group, []).append(([int(x[0]) - 1 for x in p], [int(x[1]) - 1 for x in p]))
    return verts, uvs, faces


def _target(path):
    text = gzip.decompress(path.read_bytes()).decode() if path.name.endswith('.gz') else path.read_text()
    out = {}
    for line in text.splitlines():
        if line and not line.startswith('#'):
            a = line.split()
            out[int(a[0])] = Vector(map(float, a[1:4]))
    return out


def _bump(p, centre, radius):
    d = (p - centre).length / radius
    return math.exp(-d * d)


def _gaunt(verts, used):
    """Starved and dead a long time: hollow cheeks and temples, a sharper jaw, a
    longer chin, cheekbones standing out, the nose thinned, the eyes sunk."""
    for i in used:
        p = verts[i]
        if p.y < 4.2:
            continue
        side = 1 if p.x >= 0 else -1
        # Hollow below the cheekbone, between it and the jaw.
        w = _bump(p, Vector((side * .43, 5.33, .82)), .27)
        p.x -= side * .07 * w
        p.z -= .025 * w
        # Temples sink.
        w = _bump(p, Vector((side * .62, 5.95, .55)), .24)
        p.x -= side * .045 * w
        # Cheekbones stand proud of the hollows.
        w = _bump(p, Vector((side * .5, 5.6, .92)), .14)
        p.x += side * .018 * w
        p.z += .012 * w
        # A longer, narrower chin (below the lip, which stays closed at rest).
        if p.y < 5.0:
            w = _bump(p, Vector((0, 4.8, 1.0)), .18) * min(1, (5.0 - p.y) / .12)
            p.y -= .04 * w
            p.x *= 1 - .08 * w
        # The ears lie flat under the hair, where the scalp can cover them.
        if abs(p.x) > .6 and 5.15 < p.y < 6.05 and -.35 < p.z < .65:
            p.x = side * (.6 + (abs(p.x) - .6) * .12)
        # Sunken orbits round the eyes (the lids follow, the eyeballs do not).
        w = _bump(p, Vector((side * .28, 5.82, 1.02)), .2)
        p.z -= .035 * w


def build_head():
    """Returns the closed head (verts, faces, per-loop uvs, slots, scream deltas)
    and the eye, teeth and tongue parts with their own scream deltas."""
    verts, uvs, groups = _read()
    female = [_target(SORA / 'asian-female-young.target'),
              _target(SORA / 'universal-female-young-averagemuscle-averageweight.target')]
    for t in female:
        for i, d in t.items():
            verts[i] += d
    body = groups['body']
    used = sorted({i for f, _ in body for i in f})
    _gaunt(verts, used)
    gape = _target(SOK / 'mouth-open.target.gz')
    head = [(f, uv) for f, uv in body if min(verts[i].y for i in f) > NECK_CUT]
    keep = sorted({i for f, _ in head for i in f})
    index = {v: k for k, v in enumerate(keep)}

    bm = bmesh.new()
    layer = bm.loops.layers.uv.new('UVMap')
    gaped = bm.verts.layers.float_vector.new('scream')
    for v in keep:
        bv = bm.verts.new(to_rig(verts[v]))
        bv[gaped] = to_rig(verts[v] + gape.get(v, Vector()) * 1.15) - bv.co
    bm.verts.ensure_lookup_table()
    for f, uv in head:
        try:
            face = bm.faces.new([bm.verts[index[i]] for i in f])
        except ValueError:
            continue
        face.material_index = 0
        for loop, u in zip(face.loops, uv):
            loop[layer].uv = uvs[u]
    # Close every opening: the eyes and the mouth become deep sockets, the neck
    # a raw, ragged stump pushed up into the head.
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    edges = [e for e in bm.edges if e.is_boundary]
    filled = bmesh.ops.holes_fill(bm, edges=edges, sides=0)['faces']
    stump_z = None
    for face in filled:
        centre = face.calc_center_median()
        poked = bmesh.ops.poke(bm, faces=[face])
        hub = poked['verts'][0]
        neck = centre.z < -.2
        if neck:
            stump_z = centre.z
            hub.co.z += .05
            hub[gaped] = Vector()
        else:
            # Back into the skull, behind the eyeballs and the teeth.
            hub.co.y -= .07
            ring = [e.other_vert(hub) for e in hub.link_edges]
            hub[gaped] = sum((v[gaped] for v in ring), Vector()) / len(ring)
        for f in poked['faces']:
            f.material_index = 2 if neck else 1
            for loop in f.loops:
                loop[layer].uv = (.02, .02)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # The neck below the jaw, torn: the rim's skin pulled ragged.
    for v in bm.verts:
        if v.co.z < -.28 and any(f.material_index == 0 for f in v.link_faces):
            a = math.atan2(v.co.x, v.co.y)
            v.co.z -= .018 * (.5 + .5 * math.sin(a * 7 + 1.3)) * (.6 + .4 * math.sin(a * 17))

    parts = {}
    for name, group in (('eye_l', 'helper-l-eye'), ('eye_r', 'helper-r-eye'),
                        ('upper_teeth', 'helper-upper-teeth'), ('lower_teeth', 'helper-lower-teeth'),
                        ('tongue', 'helper-tongue')):
        faces = groups[group]
        ids = sorted({i for f, _ in faces for i in f})
        local = {v: k for k, v in enumerate(ids)}
        pv = [to_rig(verts[i]) for i in ids]
        pd = [to_rig(verts[i] + gape.get(i, Vector()) * 1.15) - to_rig(verts[i]) for i in ids]
        if name.endswith('teeth'):
            # Teeth are rigid: the whole arch moves with the jaw as one piece.
            mean = sum(pd, Vector()) / len(pd)
            pd = [mean.copy() for _ in pd]
        parts[name] = (pv, [[local[i] for i in f] for f, _ in faces],
                       [[uvs[u] for u in uv] for _, uv in faces], pd)
    return bm, gaped, parts, stump_z


def measure(bm):
    """The head's half-width, front depth and back depth by height, for the scalp
    and the roots of the hair."""
    bins = {}
    for v in bm.verts:
        k = round(v.co.z * 50)
        w, f, b = bins.get(k, (0, 0, 0))
        bins[k] = (max(w, abs(v.co.x)), max(f, v.co.y), max(b, -v.co.y))
    keys = sorted(bins)

    def at(z):
        k = z * 50
        if k <= keys[0]:
            return bins[keys[0]]
        if k >= keys[-1]:
            return bins[keys[-1]]
        lo = max(key for key in keys if key <= k)
        hi = min(key for key in keys if key >= k)
        t = 0 if hi == lo else (k - lo) / (hi - lo)
        return tuple(a + (b - a) * t for a, b in zip(bins[lo], bins[hi]))
    return at
