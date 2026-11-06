"""Family ash stupas (chedey) as real masonry: each form is modelled in full, fused into one
skin, then sculpted at about a centimetre's detail. Lime plaster has fallen in sheets from
brick laid in courses; corners are knocked off; cracks run down from the ledges; water
has drawn black mould down under every overhang, and green has come up from the ground.
All of that is baked onto a game-ready mesh as colour and relief. A few of these forms
are placed many times, leaning and dressed differently (tools/areas/pagoda_stupa.py).

Proportions follow Cambodian wat chedey: stepped square plinth, carved dado, four-niched
chamber, stepped tiers with corner antefixes, lotus band, then a ringed spire or bell.
"""
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Vector, noise
from mathutils.geometry import barycentric_transform
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
TEXTURES = ROOT / 'art-source/textures/ep2'


class Solid:
    """Closed shapes gathered into one mesh, to be fused by the voxel remesher."""

    def __init__(self):
        self.verts = []
        self.faces = []

    def _add(self, verts, faces):
        base = len(self.verts)
        self.verts += [tuple(v) for v in verts]
        self.faces += [tuple(i + base for i in f) for f in faces]

    def box(self, cx, cy, z0, w, d, h, top=1.0):
        """A block `w` by `d` wide, `h` tall, its top scaled by `top`."""
        v = []
        for z, k in ((z0, 1), (z0 + h, top)):
            v += [(cx - w / 2 * k, cy - d / 2 * k, z), (cx + w / 2 * k, cy - d / 2 * k, z),
                  (cx + w / 2 * k, cy + d / 2 * k, z), (cx - w / 2 * k, cy + d / 2 * k, z)]
        self._add(v, [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])

    def lathe(self, cx, cy, z0, profile, segments=40):
        """A closed turned shape from (radius, height) pairs, bottom to top."""
        n = len(profile)
        v = [(cx, cy, z0 + profile[0][1])]
        for r, h in profile:
            for s in range(segments):
                a = s / segments * math.tau
                v.append((cx + math.cos(a) * r, cy + math.sin(a) * r, z0 + h))
        v.append((cx, cy, z0 + profile[-1][1]))
        faces = []
        last = len(v) - 1
        for s in range(segments):
            t = (s + 1) % segments
            faces.append((0, 1 + t, 1 + s))
            faces.append((last, 1 + (n - 1) * segments + s, 1 + (n - 1) * segments + t))
            for j in range(n - 1):
                a = 1 + j * segments
                faces.append((a + s, a + t, a + segments + t, a + segments + s))
        self._add(v, faces)

    def prism(self, points, origin, u, v, w, depth):
        """A closed plate: `points` are (t, z) in the plane origin + u*t + v*z, and it runs
        `depth` along w."""
        o, u, v, w = Vector(origin), Vector(u), Vector(v), Vector(w)
        n = len(points)
        vs = [tuple(o + u * t + v * z) for t, z in points] + [tuple(o + u * t + v * z + w * depth) for t, z in points]
        faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
        self._add(vs, faces)

    def tube(self, points, radius, end=None, sides=18):
        """A closed tube along `points`, tapering from `radius` to `end`."""
        pts = [Vector(p) for p in points]
        end = radius if end is None else end
        v, f = [], []
        n = len(pts)
        for i, p in enumerate(pts):
            d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
            u = d.cross(Vector((1, 0, 0)))
            if u.length < .01:
                u = d.cross(Vector((0, 1, 0)))
            u.normalize()
            w = d.cross(u)
            r = radius + (end - radius) * i / (n - 1)
            for k in range(sides):
                a = k / sides * math.tau
                v.append(tuple(p + u * math.cos(a) * r + w * math.sin(a) * r))
        for i in range(n - 1):
            for k in range(sides):
                t = (k + 1) % sides
                f.append((i * sides + k, i * sides + t, (i + 1) * sides + t, (i + 1) * sides + k))
        f.append(tuple(range(sides - 1, -1, -1)))
        f.append(tuple((n - 1) * sides + k for k in range(sides)))
        self._add(v, f)

    def add_object(self, obj, keep=None):
        """Takes in a scan's mesh, as it stands in the world. It must stay closed for the
        fusing, so to lose a part use `behead`, not `keep` on anything visible."""
        bpy.context.view_layer.update()  # a freshly placed object's matrix is stale otherwise
        m = obj.matrix_world
        vs = [m @ v.co for v in obj.data.vertices]
        faces = [tuple(p.vertices) for p in obj.data.polygons if keep is None or all(keep(vs[i]) for i in p.vertices)]
        self._add(vs, faces)

    def build(self, name, coll):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        me.update()
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        return o


def _sides():
    """Each face of a square shrine: its outward direction and the direction along it."""
    return [(Vector((0, -1, 0)), Vector((1, 0, 0))), (Vector((1, 0, 0)), Vector((0, 1, 0))),
            (Vector((0, 1, 0)), Vector((-1, 0, 0))), (Vector((-1, 0, 0)), Vector((0, -1, 0)))]


def _moulding(s, z, w, parts):
    """Stacked square courses from (width offset, height) pairs. Returns the top."""
    for dw, h in parts:
        s.box(0, 0, z, w + dw, w + dw, h)
        z += h
    return z


def _antefix(s, x, y, z, height, outward, along):
    """A flame-shaped corner antefix, about as thick as a hand."""
    t = height
    pts = [(-.42 * t, 0), (-.5 * t, .24 * t), (-.32 * t, .36 * t), (-.34 * t, .56 * t), (-.16 * t, .7 * t), (0, t),
           (.16 * t, .7 * t), (.34 * t, .56 * t), (.32 * t, .36 * t), (.5 * t, .24 * t), (.42 * t, 0)]
    s.prism(pts, Vector((x, y, z)) - outward * .035, along, Vector((0, 0, 1)), outward, .07)


def _niche(s, outward, along, half, z0, z1):
    """A pointed-arch niche in one face: stepped arch rings over slim pilasters."""
    centre = outward * half
    for k, (r, depth) in enumerate(((.18, .1), (.215, .07), (.25, .04))):
        rise = z1 - z0
        arch = []
        for a in np.linspace(0, 1, 12):
            # An ogee: straight jambs, then a curve drawing in to a point.
            h = z0 + rise * .55 + rise * .45 * a
            t = r * (1 - a ** 1.7) * (1 + .14 * math.sin(a * math.pi))
            arch.append((t, h))
        outer = [(r, z0)] + arch + [(-t, h) for t, h in reversed(arch[:-1])] + [(-r, z0)]
        inner = [(r - .03, z0)] + [(max(0, t - .03), h - .025) for t, h in arch] + [(-max(0, t - .03), h - .025) for t, h in reversed(arch[:-1])] + [(-(r - .03), z0)]
        # The ring is the band between outer and inner, cut into quads along the arch.
        for i in range(len(outer) - 1):
            pts = [outer[i], outer[i + 1], inner[i + 1], inner[i]]
            s.prism(pts, centre - outward * depth, along, Vector((0, 0, 1)), outward, depth + .012 * k + .01)


def _dado(s, outward, along, half, z0, z1):
    """A carved panel: a proud frame round a sunk field with a false door of balusters."""
    centre = outward * half
    w = half - .07
    for t0, t1, h0, h1 in ((-w, w, z0, z0 + .035), (-w, w, z1 - .035, z1), (-w, -w + .035, z0, z1), (w - .035, w, z0, z1)):
        s.prism([(t0, h0), (t1, h0), (t1, h1), (t0, h1)], centre - outward * .02, along, Vector((0, 0, 1)), outward, .035)
    for k in range(-3, 4):
        t = k * w / 4
        pts = [(t - .016, z0 + .04), (t + .016, z0 + .04), (t + .022, (z0 + z1) / 2), (t + .016, z1 - .04), (t - .016, z1 - .04), (t - .022, (z0 + z1) / 2)]
        s.prism(pts, centre - outward * .02, along, Vector((0, 0, 1)), outward, .028)


FORMS = {
    # Upper shapes as (radius, height) pairs from the lotus band.
    'spire': [(.33, 0), (.36, .06), (.3, .14), (.25, .32), (.16, .46), (.17, .52), (.13, .6)],
    'bell': [(.34, 0), (.36, .04), (.32, .08), (.39, .18), (.4, .3), (.36, .4), (.27, .5), (.16, .56), (.12, .6)],
    'bud': [(.28, 0), (.32, .1), (.24, .18), (.3, .3), (.32, .4), (.26, .5), (.15, .57), (.12, .6)],
    'prang': [(.35, 0), (.35, .1), (.3, .1), (.3, .2), (.25, .2), (.25, .3), (.2, .3), (.2, .4), (.15, .4), (.15, .5), (.11, .6)],
}


def shape(form, coll, name, height=3.4, broken=False):
    """The whole stupa as one closed, fused mass, before any weathering."""
    s = Solid()
    z = _moulding(s, 0, 1.2, [(.2, .1), (.12, .05), (.06, .03), (0, .13), (.05, .04), (-.04, .07)])
    # The carved dado.
    s.box(0, 0, z, .96, .96, .3)
    for outward, along in _sides():
        _dado(s, outward, along, .48, z + .02, z + .28)
    z = _moulding(s, z + .3, .96, [(.06, .04), (.14, .05), (.05, .04)])
    # The chamber: a core with an arched niche in each face, its corners pilasters.
    chamber = z
    s.box(0, 0, z, .62, .62, .6)
    for dx in (-.34, .34):
        for dy in (-.34, .34):
            s.box(dx, dy, z, .19, .19, .6)
    for outward, along in _sides():
        # Infill either side of the arch, a thin wall holding the niche.
        for t in (-.26, .26):
            c = outward * .39 + along * t
            s.box(c.x, c.y, z, .13 if abs(outward.y) > .5 else .08, .13 if abs(outward.x) > .5 else .08, .6)
        c = outward * .39
        s.box(c.x, c.y, z + .46, .5 if abs(outward.y) > .5 else .08, .5 if abs(outward.x) > .5 else .08, .14)
        _niche(s, outward, along, .4, z + .02, z + .58)
    z = _moulding(s, z + .6, .92, [(.08, .05), (.18, .06), (.06, .05), (-.02, .05)])
    # Stepped tiers with a flame at each corner, like the roofs of a tower.
    for k, (w, h, ante) in enumerate(((.82, .13, .16), (.66, .11, .13), (.52, .09, .1))):
        s.box(0, 0, z, w, w, h, top=.96)
        z2 = z + h
        s.box(0, 0, z2, w + .05, w + .05, .03)
        for sx in (-1, 1):
            for sy in (-1, 1):
                outward = Vector((sx, sy, 0)).normalized()
                along = Vector((-sy, sx, 0)).normalized()
                _antefix(s, sx * (w / 2), sy * (w / 2), z2 + .02, ante, outward, along)
        z = z2 + .03
    # The lotus band: a turned course with petals standing round it.
    r = .3
    s.lathe(0, 0, z, [(r * .9, 0), (r * 1.08, .05), (r * 1.1, .1), (r * .86, .17)], 40)
    for j in range(16):
        a = j / 16 * math.tau
        outward = Vector((math.cos(a), math.sin(a), 0))
        along = Vector((-math.sin(a), math.cos(a), 0))
        pts = [(-.052, 0), (.052, 0), (.048, .08), (0, .14), (-.048, .08)]
        s.prism(pts, outward * (r * 1.02) + Vector((0, 0, z + .02)), along, Vector((0, 0, 1)) - outward * .28, outward, .025)
    z += .17
    # The form above: turned shape, rings narrowing, a slim finial.
    scale = max(.7, height - z - .75)
    profile = [(rr, hh * scale) for rr, hh in FORMS[form]]
    if broken:
        # Snapped through the drum, the break jagged by the weathering that follows.
        profile = [p for p in profile if p[1] < .24 * scale] + [(.2, .28 * scale)]
    s.lathe(0, 0, z, profile, 40)
    top = z + profile[-1][1]
    if not broken:
        for k in range(8):
            rr = .125 * (1 - k / 10)
            s.lathe(0, 0, top + k * .05, [(rr * .86, 0), (rr, .018), (rr, .03), (rr * .86, .05)], 24)
        top += .4
        s.lathe(0, 0, top, [(.05, 0), (.038, .12), (.022, .3), (.03, .34), (.012, .42), (.001, .5)], 16)
        top += .5
    o = s.build(name, coll)
    print('Stupa form', form, 'to', round(top, 2), 'm, chamber at', round(chamber, 2), flush=True)
    return o, chamber


# Each octave is sampled through its own rotation: noise lattices line up with the axes,
# and on square masonry that shows as a mosaic of little blocks.
_TURNS = [Euler((.61 + k * .37, 1.13 - k * .29, .47 + k * .53)).to_matrix() for k in range(6)]


def _fbm(p, octaves, scale, seed=0.0):
    """Fractal noise at point `p`, about -1..1, features `scale` metres wide."""
    f, a, total, acc = 1 / scale, 1.0, 0.0, 0.0
    offset = Vector((seed, seed * .7, seed * 1.3))
    for k in range(octaves):
        acc += a * noise.noise(_TURNS[k] @ p * f + offset, noise_basis='PERLIN_NEW')
        total += a
        f *= 2.03
        a *= .52
    return acc / total * 1.9


def remesh(obj, voxel=.0055):
    mod = obj.modifiers.new('fuse', 'REMESH')
    mod.mode = 'VOXEL'
    mod.voxel_size = voxel
    mod.adaptivity = 0
    mod.use_smooth_shade = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    print('Stupa fused', len(obj.data.vertices), 'verts', flush=True)


PALETTES = {
    # Lime plaster falling from brick: the stupas.
    'lime': dict(base=(.47, .445, .37), stain=(.32, .24, .13), edge=(.6, .57, .5), under=None, fall=.3, mould=1.55),
    # Carved sandstone: nothing falls off but flakes, the fresher stone paler under them.
    'sandstone': dict(base=(.4, .365, .285), stain=(.22, .18, .11), edge=(.52, .47, .37), under=(.46, .41, .32), fall=.56, mould=.95),
    # Gold leaf on black-red lacquer, worn through at everything a hand ever touched.
    'gilt': dict(base=(.52, .37, .11), stain=(.2, .13, .04), edge=(.6, .46, .16), under=(.075, .018, .014), fall=.26, mould=.9),
    # Old red paint flaking from grey wood: the spirit houses.
    'red': dict(base=(.25, .06, .04), stain=(.13, .05, .03), edge=(.33, .22, .14), under=(.17, .14, .1), fall=.2, mould=1.1),
    'ochre': dict(base=(.34, .25, .1), stain=(.15, .1, .05), edge=(.4, .32, .18), under=(.17, .14, .1), fall=.22, mould=1.2),
}


def weather(obj, seed, palette='lime', scale=1.0, chamber=True, surface_colours=None, wear=1.0):
    """Sculpts the fused mass in place and works out its colour, per vertex. `scale` sizes
    the damage to the object: a stupa is 1, a statue perhaps .5. `surface_colours` gives
    each vertex its own stone colour (a scan's real one) in place of the palette's. `wear` is
    how much of the carving the damage may take: 1 for masonry, far less for a fine scan."""
    me = obj.data
    pal = PALETTES[palette]
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    normal = np.empty(n * 3)
    me.vertex_normals.foreach_get('vector', normal)
    normal = normal.reshape(-1, 3)
    height = co[:, 2] / scale
    # How exposed each corner is: convex edges get knocked off first.
    edges = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get('vertices', edges)
    edges = edges.reshape(-1, 2)
    mean = np.zeros_like(co)
    count = np.zeros((n, 1))
    np.add.at(mean, edges[:, 0], co[edges[:, 1]])
    np.add.at(mean, edges[:, 1], co[edges[:, 0]])
    np.add.at(count, edges[:, 0], 1)
    np.add.at(count, edges[:, 1], 1)
    lap = mean / np.maximum(count, 1) - co
    convex = np.clip(-(lap * normal).sum(1) / (.004 * scale), 0, 1)
    # Fields of noise, per vertex, at the scales weather works at.
    sheet, fine, grit, crack, crack2, tone, streak, streak2, blot, lichen = (np.zeros(n) for _ in range(10))
    for i in range(n):
        p = Vector(co[i]) / scale
        sheet[i] = _fbm(p, 5, .24, seed)
        fine[i] = _fbm(p, 3, .022, seed + 3)
        grit[i] = _fbm(p, 2, .006, seed + 23)
        tone[i] = _fbm(p, 3, .38, seed + 7)
        # Warped by the larger noise: unwarped peaks of Perlin noise show as little diamonds.
        warped = p + Vector((sheet[i], tone[i], sheet[i] - tone[i])) * .14
        blot[i] = _fbm(warped, 3, .22, seed + 31)
        lichen[i] = _fbm(warped, 2, .05, seed + 41)
        # Long in Z, thin across: the grain of running water and of cracks.
        q = Vector((p.x, p.y, p.z * .1))
        streak[i] = _fbm(q, 3, .045, seed + 11)
        streak2[i] = _fbm(q, 3, .014, seed + 13)
        r = Vector((p.x, p.y, p.z * .28))
        crack[i] = _fbm(r, 3, .13, seed + 17)
        crack2[i] = _fbm(r, 3, .05, seed + 19)
    # The surface falls away in sheets, more readily low down and at corners, raggedly.
    fall = pal['fall'] + (1 - wear) * .35
    bias = .1 * (1 - np.clip(height / 1.5, 0, 1)) + .12 * convex
    field = sheet + bias + fine * .13 + grit * .05
    fallen = field > fall
    rim = np.clip((field - fall + .04) / .04, 0, 1) * (1 - np.clip((field - fall) / .03, 0, 1))
    bare = np.clip((field - fall) / .012, 0, 1)
    brickwork = pal['under'] is None
    push = np.zeros(n)
    depth = .012 if brickwork else .004
    push[fallen] -= depth + (.02 if brickwork else .006) * np.clip(sheet[fallen] - fall, 0, .3) / .3
    if brickwork:
        # Brick under it: courses and staggered joints, mortar raked out, no two alike.
        course = np.floor(height / .068)
        joint_z = np.abs((height / .068) % 1 - .5) * 2
        around = np.where(np.abs(normal[:, 0]) > np.abs(normal[:, 1]), co[:, 1], co[:, 0])
        along = (around + course * .11) / .22
        joint_t = np.abs(along % 1 - .5) * 2
        mortar = np.maximum(_smoothstep(.8, .94, joint_z), _smoothstep(.93, .985, joint_t))
        each = np.sin(course * 12.9898 + np.floor(along) * 78.233) * 43758.5453
        each = each - np.floor(each)
        push -= bare * mortar * .007
        push += bare * (each - .5) * .004 + bare * grit * .0016
    # Corners knocked off, whatever is under them.
    knocked = convex * np.clip(fine * 1.1 + grit * .5 + .22, 0, 1)
    push -= knocked * .016 * wear
    # Cracks: thin dark lines, wandering downwards, the big ones with a family of small.
    line = np.exp(-((crack / .012) ** 2)) * np.clip((tone + .5) * 1.8, 0, 1) * wear
    line2 = np.exp(-((crack2 / .007) ** 2)) * np.clip((blot + .15) * 2.2, 0, 1) * wear
    push -= line * .009 + line2 * .003
    # The skin of old stone: never flat.
    push += grit * .0012 + fine * .0028 + blot * .0016
    # Moss swells on what faces the sky, and low down.
    up = np.clip(normal[:, 2], 0, 1)
    damp = np.clip(1.15 - height / 2.2, 0, 1)
    moss = np.clip((up * .95 + damp * .3 + tone * .55 + blot * .25 - .62) * 3.2, 0, 1) * np.clip(fine * 1.2 + grit * .6 + .62, 0, 1)
    if palette == 'gilt':
        moss *= .15  # kept indoors
    push += moss * .005 * (1 + grit * .9)
    moved = co + normal * (push * scale)[:, None]
    me.vertices.foreach_set('co', moved.ravel())
    me.update()
    # Water stains: how far up the next ledge is, cast upwards from each vertex.
    verts = [Vector(c) for c in moved]
    polys = [tuple(p.vertices) for p in me.polygons]
    tree = BVHTree.FromPolygons(verts, polys)
    under = np.full(n, 99.0)
    up_vec = Vector((0, 0, 1))
    for i in range(n):
        hit = tree.ray_cast(verts[i] + Vector(normal[i]) * .004, up_vec, 3.0)
        if hit[0] is not None:
            under[i] = hit[3] / scale
    runs = np.exp(-under / .75) * np.clip(streak * .35 + streak2 * .2 + .78, 0, 1)
    # Water spreads as it runs: soften it across the mesh, or each voxel's ledge shows.
    for _ in range(6):
        total = runs.copy()
        seen = np.ones(n)
        np.add.at(total, edges[:, 0], runs[edges[:, 1]])
        np.add.at(total, edges[:, 1], runs[edges[:, 0]])
        np.add.at(seen, edges[:, 0], 1)
        np.add.at(seen, edges[:, 1], 1)
        runs = total / seen
    # Colour: the surface gone grey and yellow, what is under it, mould, lichen, moss, earth.
    surface = np.array(pal['base'])
    streak_strength = 1.0
    if surface_colours is None:
        colour = np.tile(surface, (n, 1))
        colour = colour * (1 + tone[:, None] * .3 + fine[:, None] * .14 + grit[:, None] * .1)
        colour += (np.array(pal['stain']) - surface)[None, :] * np.clip(tone + .15 + streak * .18, 0, 1)[:, None] * .55
    else:
        colour = surface_colours * (1 + tone[:, None] * .22 + fine[:, None] * .08)
        colour += (np.array(pal['stain'])[None, :] - colour) * np.clip(tone + .1 + streak * .5, 0, 1)[:, None] * .28
    # Rain runs down fine carving only under its ledges, not as stripes across a face.
    streak_strength = .35 + .65 * wear
    # Blooms of grey-black mould, away from the runs as well.
    # Soft-edged and faint, or the patches read as camouflage.
    bloom = _smoothstep(-.2, 1.0, blot)
    colour *= 1 - bloom[:, None] * .22
    # Pale lichen rosettes.
    rosette = _smoothstep(.35, 1.0, lichen) * np.clip(1 - bloom * 1.2, 0, 1)
    if palette == 'gilt':
        rosette *= 0
    colour = colour * (1 - rosette[:, None] * .16) + np.array([.5, .52, .42])[None, :] * rosette[:, None] * .16
    # The broken edge of the surface shows its thickness, pale and clean.
    colour = colour * (1 - rim[:, None] * .45) + np.array(pal['edge'])[None, :] * rim[:, None] * .45
    if brickwork:
        beneath = np.array([.25, .105, .06])[None, :] * (.55 + .9 * each)[:, None] * (1 + fine[:, None] * .25)
        burnt = _smoothstep(.86, .9, each)[:, None]
        beneath = beneath * (1 - burnt) + np.array([.05, .04, .035])[None, :] * burnt
        beneath = beneath * (1 - mortar[:, None]) + np.array([.17, .155, .125])[None, :] * mortar[:, None]
    else:
        beneath = np.array(pal['under'])[None, :] * (1 + fine[:, None] * .3 + grit[:, None] * .2)
    colour = colour * (1 - bare[:, None]) + beneath * bare[:, None]
    black = np.array([.018, .018, .016])
    low = np.clip(.95 - height / 1.05, 0, .55) * np.clip(streak * streak_strength + .7, 0, 1)
    mould = np.clip(runs * pal['mould'] * (.45 + .55 * wear) + low, 0, 1) ** 1.05
    colour = colour * (1 - mould[:, None] * .72) + black * mould[:, None] * .72
    # Dust and rot lying on every ledge.
    colour *= 1 - (up > .6)[:, None] * np.clip(up * .7, 0, .55)[:, None]
    green = np.array([.052, .085, .022]) * (1 + fine[:, None] * .7 + grit[:, None] * .4)
    colour = colour * (1 - moss[:, None] * .9) + green * moss[:, None] * .9
    splash = np.clip(1 - height / .4, 0, 1) ** 1.3
    colour *= 1 - splash[:, None] * np.array([.55, .6, .7])
    colour *= 1 - np.clip(line + line2 * .7, 0, 1)[:, None] * .88
    if chamber:
        # The chamber's inside is black with old soot and smoke.
        inside = (np.abs(co[:, 0]) < .36) & (np.abs(co[:, 1]) < .36) & (height > .84) & (height < 1.46)
        colour[inside] *= .16
    colour = np.clip(colour, 0, 1)
    attr = me.color_attributes.new('stain', 'FLOAT_COLOR', 'POINT')
    rgba = np.ones((n, 4), np.float32)
    rgba[:, :3] = colour
    attr.data.foreach_set('color', rgba.ravel())
    print('Weathered', obj.name, palette, n, 'verts, bare', round(float(bare.mean()), 2), flush=True)
    return attr


class ScanSurface:
    """What a scan's texture knows that its mesh does not: read back onto a fused sculpt, the
    fine carving as relief and the real colour of its stone."""

    def __init__(self, obj):
        bpy.context.view_layer.update()
        me = obj.data
        m = obj.matrix_world
        self.verts = [m @ v.co for v in me.vertices]
        self.polys = []
        uv = me.uv_layers.active.data
        for p in me.polygons:
            self.polys.append((tuple(p.vertices), tuple(tuple(uv[l].uv) for l in p.loop_indices), p.material_index))
        self.tree = BVHTree.FromPolygons(self.verts, [p[0] for p in self.polys])
        self.images = []
        for mat in me.materials:
            image = None
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            links = bsdf.inputs['Base Color'].links if bsdf else ()
            if links and links[0].from_node.type == 'TEX_IMAGE':
                image = links[0].from_node.image
            if image is None:
                image = next((n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image.colorspace_settings.name == 'sRGB'), None)
            w, h = image.size
            px = np.empty(w * h * 4, np.float32)
            image.pixels.foreach_get(px)
            self.images.append((px.reshape(h, w, 4)[..., :3], w, h))

    def sample(self, co):
        """The scan's colour (encoded sRGB) nearest each point of an (n, 3) array."""
        out = np.zeros((len(co), 3), np.float32)
        for i, c in enumerate(co):
            p = Vector(c)
            hit = self.tree.find_nearest(p)
            if hit[2] is None:
                continue
            ids, uvs, mat = self.polys[hit[2]]
            a, b, d = (self.verts[j] for j in ids[:3])
            uv = barycentric_transform(hit[0], a, b, d, Vector((*uvs[0], 0)), Vector((*uvs[1], 0)), Vector((*uvs[2], 0)))
            px, w, h = self.images[min(mat, len(self.images) - 1)]
            out[i] = px[int(uv.y % 1 * h) % h, int(uv.x % 1 * w) % w]
        return out

    def emboss(self, obj, strength, keep_colour=False, reach=8):
        """Presses the texture's dark crevices into the mesh and raises its bright ridges,
        high-passed so only carving moves. Returns linear colours if `keep_colour`."""
        me = obj.data
        n = len(me.vertices)
        co = np.empty(n * 3)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        normal = np.empty(n * 3)
        me.vertex_normals.foreach_get('vector', normal)
        normal = normal.reshape(-1, 3)
        colours = self.sample(co)
        lum = colours.mean(1).astype(np.float64)
        edges = np.empty(len(me.edges) * 2, np.int32)
        me.edges.foreach_get('vertices', edges)
        edges = edges.reshape(-1, 2)
        soft = lum.copy()
        for _ in range(reach):
            acc = np.zeros(n)
            cnt = np.zeros(n)
            np.add.at(acc, edges[:, 0], soft[edges[:, 1]])
            np.add.at(acc, edges[:, 1], soft[edges[:, 0]])
            np.add.at(cnt, edges[:, 0], 1)
            np.add.at(cnt, edges[:, 1], 1)
            soft = soft * .3 + acc / np.maximum(cnt, 1) * .7
        relief = np.clip((lum - soft) / max(float(np.std(lum - soft)) * 3, 1e-4), -1, 1)
        me.vertices.foreach_set('co', (co + normal * (relief * strength)[:, None]).ravel())
        me.update()
        return np.clip(colours, 0, 1) ** 2.2 if keep_colour else None


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _grain(img, tag, mesh, tile=1.1):
    """The grain of real old plaster, from the library's scanned map, laid over the bake at
    true scale: finer than the sculpt can carry, and what the eye reads at arm's length."""
    size = img.size[0]
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers.active.data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    area3d = sum(p.area for p in mesh.polygons)
    area_uv = 0.0
    for p in mesh.polygons:
        pts = uv[list(p.loop_indices)]
        area_uv += abs(np.dot(pts[:, 0], np.roll(pts[:, 1], 1)) - np.dot(pts[:, 1], np.roll(pts[:, 0], 1))) / 2
    metres = math.sqrt(area3d / max(area_uv, 1e-6))  # one UV unit, in metres
    src = bpy.data.images.load(str(ROOT / f'art-source/library/materials/clay_plaster/clay_plaster_{tag}.jpg'), check_existing=True)
    if tag == 'N':
        src.colorspace_settings.name = 'Non-Color'
    w, h = src.size
    grain = np.empty(w * h * 4, np.float32)
    src.pixels.foreach_get(grain)
    grain = grain.reshape(h, w, 4)
    repeats = metres / tile
    yy, xx = np.mgrid[0:size, 0:size]
    lookup = grain[(yy * repeats / size * h).astype(int) % h, (xx * repeats / size * w).astype(int) % w]
    px = np.empty(size * size * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(size, size, 4)
    if tag == 'BC':
        lum = lookup[..., :3].mean(-1)
        lum = lum / lum.mean()
        px[..., :3] *= np.clip(.25 + .75 * lum, 0, 1.6)[..., None]
    else:
        d = (lookup[..., :2] - .5) * 2 * 1.1
        n = (px[..., :3] - .5) * 2
        n[..., :2] += d
        n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-5)
        px[..., :3] = n * .5 + .5
    img.pixels.foreach_set(px.ravel())
    img.update()
    print('Stupa grain', tag, 'repeats', round(repeats, 1), flush=True)


def bake_down(high, name, coll, faces=16000, size=2048, roughness=.92, metallic=0.0):
    """A game-ready mesh from the sculpt: fewer faces, fresh UVs, and the sculpt's relief,
    occlusion and colour baked onto it. Returns the low object and its material."""
    sc = bpy.context.scene
    # Occlusion first, on the sculpt's own vertices.
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    me = high.data
    occl = me.color_attributes.new('occlusion', 'FLOAT_COLOR', 'POINT')
    me.color_attributes.active_color = occl
    blank = bpy.data.materials.new('blank')
    me.materials.append(blank)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    high.select_set(True)
    bpy.context.view_layer.objects.active = high
    sc.cycles.samples = 48
    sc.render.bake.use_selected_to_active = False
    sc.render.bake.target = 'VERTEX_COLORS'
    bpy.ops.object.bake(type='AO')
    sc.render.bake.target = 'IMAGE_TEXTURES'
    n = len(me.vertices)
    ao = np.empty(n * 4, np.float32)
    occl.data.foreach_get('color', ao)
    stain = me.color_attributes['stain']
    colour = np.empty(n * 4, np.float32)
    stain.data.foreach_get('color', colour)
    # Per-vertex occlusion is noisy, and multiplied into the colour its noise reads as
    # camouflage: smooth it across the mesh first and let it only deepen the crevices.
    shade = ao[0::4].astype(np.float64)
    edges = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get('vertices', edges)
    edges = edges.reshape(-1, 2)
    for _ in range(8):
        total = shade.copy()
        seen = np.ones(n)
        np.add.at(total, edges[:, 0], shade[edges[:, 1]])
        np.add.at(total, edges[:, 1], shade[edges[:, 0]])
        np.add.at(seen, edges[:, 0], 1)
        np.add.at(seen, edges[:, 1], 1)
        shade = total / seen
    shade = (.42 + .58 * shade).astype(np.float32)
    print('Occlusion', name, 'mean', round(float(shade.mean()), 3), 'std', round(float(shade.std()), 3), flush=True)
    colour[0::4] *= shade
    colour[1::4] *= shade
    colour[2::4] *= shade
    stain.data.foreach_set('color', colour)

    # The source material: vertex colour into a diffuse.
    src = bpy.data.materials.new(name + '_source')
    nt = src.node_tree
    at = nt.nodes.new('ShaderNodeVertexColor')
    at.layer_name = 'stain'
    nt.links.new(at.outputs[0], nt.nodes['Principled BSDF'].inputs['Base Color'])
    me.materials.clear()
    me.materials.append(src)

    # The low mesh.
    low = high.copy()
    low.data = me.copy()
    low.name = name
    low.data.name = name
    coll.objects.link(low)
    dec = low.modifiers.new('budget', 'DECIMATE')
    dec.ratio = min(1.0, faces / max(1, sum(len(p.vertices) - 2 for p in me.polygons)))
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.modifier_apply(modifier=dec.name)
    lm = low.data
    for a in [a.name for a in lm.color_attributes]:
        lm.color_attributes.remove(lm.color_attributes[a])
    for o in bpy.context.selected_objects:
        o.select_set(False)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    lm.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=.004)
    # Smart Project leaves much of the sheet empty; every texel saved sharpens the stone.
    bpy.ops.uv.pack_islands(rotate=True, margin=.002, shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')
    for p in lm.polygons:
        p.use_smooth = True

    target = bpy.data.materials.new(name + '_stone')
    lm.materials.clear()
    lm.materials.append(target)
    tnt = target.node_tree
    node = tnt.nodes.new('ShaderNodeTexImage')
    tnt.nodes.active = node
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    sc.render.bake.use_selected_to_active = True
    sc.render.bake.cage_extrusion = .03
    sc.render.bake.max_ray_distance = .06
    sc.render.bake.margin = 6
    sc.cycles.samples = 1
    TEXTURES.mkdir(parents=True, exist_ok=True)
    images = {}
    for kind, tag, extra in (('DIFFUSE', 'BC', {'pass_filter': {'COLOR'}}), ('NORMAL', 'N', {'normal_space': 'TANGENT'})):
        img = bpy.data.images.new(f'T_ep2_{name}_{tag}', size, size, is_data=tag == 'N')
        node.image = img
        bpy.ops.object.bake(type=kind, **extra)
        _grain(img, tag, lm)
        img.filepath_raw = str(TEXTURES / f'T_ep2_{name}_{tag}.png')
        img.file_format = 'PNG'
        img.save()
        img.pack()
        images[tag] = img
    sc.render.bake.use_selected_to_active = False
    tnt.nodes.remove(node)
    bsdf = tnt.nodes['Principled BSDF']
    bc = tnt.nodes.new('ShaderNodeTexImage')
    bc.image = images['BC']
    tnt.links.new(bc.outputs[0], bsdf.inputs['Base Color'])
    nm = tnt.nodes.new('ShaderNodeTexImage')
    nm.image = images['N']
    nmap = tnt.nodes.new('ShaderNodeNormalMap')
    tnt.links.new(nm.outputs[0], nmap.inputs['Color'])
    tnt.links.new(nmap.outputs[0], bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    print('Baked', name, len(lm.polygons), 'faces', flush=True)
    return low, target
