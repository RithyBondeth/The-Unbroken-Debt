"""Geometry for carved and turned shrine work (Episode 1, 2026-11 redesign).

`Batch` gathers many small parts into one mesh per material, so a spirit house
of a thousand pieces stays a dozen draw calls. Every part carries its own UVs,
worked out in its own frame before it is placed, so wood grain runs along each
board, post and baluster. Run inside Blender.
"""
import math

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector


def _v(p):
    return Vector((float(p[0]), float(p[1]), float(p[2])))


class Batch:
    """Parts gathered per material; `build` makes one object per material."""

    def __init__(self, name):
        self.name = name
        self.groups = {}

    def _g(self, mat):
        g = self.groups.get(mat)
        if g is None:
            g = self.groups[mat] = {"v": [], "f": [], "uv": [], "s": []}
        return g

    def add(self, mat, verts, faces, uvs, smooth=True, xf=None):
        """`uvs` is one (u, v) per vertex; `xf` places the part (a Matrix)."""
        g = self._g(mat)
        base = len(g["v"])
        if xf is not None:
            verts = [tuple(xf @ _v(p)) for p in verts]
        g["v"].extend(tuple(map(float, p)) for p in verts)
        g["uv"].extend(uvs)
        for f in faces:
            g["f"].append(tuple(base + i for i in f))
            g["s"].append(smooth)

    def add_mesh(self, mat, mesh, xf, tile=.3):
        """Copy a Blender mesh (a decimated scan) in, box-projecting its UVs."""
        verts = [tuple(xf @ v.co) for v in mesh.vertices]
        tri = []
        for p in mesh.polygons:
            tri.append(tuple(p.vertices))
        # Box UVs per vertex from the averaged normal's dominant axis.
        uvs = []
        for v in mesh.vertices:
            n = v.normal
            axis = max(range(3), key=lambda i: abs(n[i]))
            a, b = ((1, 2), (0, 2), (0, 1))[axis]
            co = xf @ v.co
            uvs.append((co[a] / tile, co[b] / tile))
        self.add(mat, verts, tri, uvs, smooth=True)

    def build(self, coll, sharp=math.radians(38), prefix=None):
        objs = {}
        for mat, g in self.groups.items():
            if not g["f"]:
                continue
            name = f"{prefix or self.name}_{mat.name.replace('M_', '')}"
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(g["v"], [], g["f"])
            mesh.materials.append(mat)
            layer = mesh.uv_layers.new(name="UVMap")
            uv = np.array(g["uv"], dtype=np.float32)
            loops = np.empty(len(mesh.loops), dtype=np.int32)
            mesh.loops.foreach_get("vertex_index", loops)
            layer.data.foreach_set("uv", uv[loops].ravel())
            mesh.polygons.foreach_set("use_smooth", np.array(g["s"], dtype=bool))
            mesh.validate(clean_customdata=False)
            mesh.update()
            if sharp:
                mesh.set_sharp_from_angle(angle=sharp)
            obj = bpy.data.objects.new(name, mesh)
            coll.objects.link(obj)
            objs[mat] = obj
        return objs

    # ------------------------------------------------------------ primitives

    def box(self, mat, size, centre, xf=None, chamfer=0.0, tile=1.0, jitter=0.0, rng=None, smooth=False, rough=None,
            grain=True, max_cuts=None):
        """A board, post or block with grain along its longest side. `chamfer`
        bevels its edges; `jitter` nudges the vertices (hewn, not machined);
        `rough` (amplitude, frequency) dents a stone's faces with coherent noise;
        `grain=False` keeps the texture upright (plaster, brick: runs fall down)."""
        sx, sy, sz = size
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1)
        for v in bm.verts:
            v.co.x *= sx
            v.co.y *= sy
            v.co.z *= sz
        if chamfer:
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(chamfer, min(size) * .45), segments=1,
                            affect="EDGES", profile=.5)
        if rough:
            from mathutils import noise
            amp, freq = rough
            cuts = int(max(size) * freq * 1.2) or 1
            if max_cuts:
                cuts = min(cuts, max_cuts)
            bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=cuts, use_grid_fill=True)
            seed = Vector(rng.uniform(0, 100, 3)) if rng is not None else Vector((3, 7, 11))
            for v in bm.verts:
                direction = Vector((v.co.x / sx, v.co.y / sy, v.co.z / sz)).normalized()
                n = noise.fractal(v.co * freq + seed, .55, 2.0, 4)
                chip = max(0.0, noise.noise(v.co * freq * .5 + seed * 2) - .25) * 2.2
                v.co -= direction * amp * (abs(n) * 1.4 + chip)
        long_axis = max(range(3), key=lambda i: size[i])
        verts, faces, uvs = [], [], []
        for f in bm.faces:
            n = f.normal
            axis = max(range(3), key=lambda i: abs(n[i]))
            a, b = [i for i in range(3) if i != axis]
            if grain and b == long_axis:
                a, b = b, a
            idx = []
            for lv in f.verts:
                co = lv.co.copy()
                if jitter and rng is not None:
                    co += Vector(rng.normal(0, jitter, 3))
                idx.append(len(verts))
                verts.append(tuple(co + _v(centre)))
                uvs.append((lv.co[a] / tile + centre[a] / tile, lv.co[b] / tile + centre[b] / tile))
            faces.append(tuple(idx))
        bm.free()
        self.add(mat, verts, faces, uvs, smooth=smooth, xf=xf)

    def lathe(self, mat, profile, xf=None, segments=24, tile=1.0, radial=None, cap=True, smooth=True, phase=0.0):
        """A turned part from (radius, height) points, bottom to top, about local
        z. `radial(angle, h)` scales the radius (hand turning, shrinkage, cracks).
        Grain runs up the part (u = height)."""
        verts, faces, uvs = [], [], []
        dist = [0.0]
        for (r0, h0), (r1, h1) in zip(profile, profile[1:]):
            dist.append(dist[-1] + math.hypot(r1 - r0, h1 - h0))
        rows = len(profile)
        for i, (r, h) in enumerate(profile):
            for k in range(segments + 1):
                a = phase + math.tau * k / segments
                s = radial(a, h) if radial else 1.0
                verts.append((r * s * math.cos(a), r * s * math.sin(a), h))
                uvs.append((dist[i] / tile, (k / segments) * math.tau * max(r, .01) / tile))
        for i in range(rows - 1):
            for k in range(segments):
                a = i * (segments + 1) + k
                faces.append((a, a + 1, a + segments + 2, a + segments + 1))
        if cap and profile[-1][0] > 1e-4:
            c = len(verts)
            verts.append((0, 0, profile[-1][1]))
            uvs.append((dist[-1] / tile, 0))
            top = (rows - 1) * (segments + 1)
            for k in range(segments):
                faces.append((top + k, top + k + 1, c))
        if cap and profile[0][0] > 1e-4:
            c = len(verts)
            verts.append((0, 0, profile[0][1]))
            uvs.append((0, 0))
            for k in range(segments):
                faces.append((k + 1, k, c))
        self.add(mat, verts, faces, uvs, smooth=smooth, xf=xf)

    def tube(self, mat, points, radii, sides=6, v0=0.0, v1=None, tile=None, cap_end=False, smooth=True,
             flatten=1.0, up=(0, 0, 1)):
        """A round (or `flatten`ed) tube along `points`, radius per point (or one).
        V runs v0..v1 along it (or metres / tile)."""
        pts = [_v(p) for p in points]
        n = len(pts)
        if not isinstance(radii, (list, tuple, np.ndarray)):
            radii = [radii] * n
        dist = [0.0]
        for a, b in zip(pts, pts[1:]):
            dist.append(dist[-1] + (b - a).length)
        total = dist[-1] or 1.0
        tangents = []
        for i in range(n):
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
            tangents.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
        ref = _v(up)
        if abs(tangents[0].dot(ref)) > .95:
            ref = Vector((1, 0, 0))
        nrm = tangents[0].cross(ref).normalized()
        frames = []
        for i in range(n):
            if i:
                # Parallel transport keeps the tube from twisting round its bends.
                rot = tangents[i - 1].rotation_difference(tangents[i])
                nrm = (rot @ nrm).normalized()
            frames.append((nrm.copy(), tangents[i].cross(nrm).normalized()))
        verts, faces, uvs = [], [], []
        for i, p in enumerate(pts):
            a, b = frames[i]
            r = radii[i]
            v = (v0 + (v1 - v0) * dist[i] / total) if v1 is not None else dist[i] / (tile or 1.0)
            for k in range(sides + 1):
                ang = math.tau * k / sides
                verts.append(tuple(p + a * math.cos(ang) * r + b * math.sin(ang) * r * flatten))
                uvs.append((k / sides, v))
        for i in range(n - 1):
            for k in range(sides):
                s = i * (sides + 1) + k
                faces.append((s, s + 1, s + sides + 2, s + sides + 1))
        if cap_end:
            c = len(verts)
            verts.append(tuple(pts[-1]))
            uvs.append((.5, v1 if v1 is not None else total / (tile or 1.0)))
            last = (n - 1) * (sides + 1)
            for k in range(sides):
                faces.append((last + k, last + k + 1, c))
        self.add(mat, verts, faces, uvs, smooth=smooth)

    def sweep(self, mat, points, normal, widths, thick, tile=.5, smooth=False, taper_thick=None):
        """A carved strip: a rectangle (width in the plane, `thick` along the
        plane's `normal`) swept along `points`. Brackets, bargeboards, horns."""
        pts = [_v(p) for p in points]
        nrm = _v(normal).normalized()
        n = len(pts)
        if not isinstance(widths, (list, tuple, np.ndarray)):
            widths = [widths] * n
        if taper_thick is None:
            thicks = [thick] * n
        else:
            thicks = [thick + (taper_thick - thick) * i / max(1, n - 1) for i in range(n)]
        dist = [0.0]
        for a, b in zip(pts, pts[1:]):
            dist.append(dist[-1] + (b - a).length)
        verts, faces, uvs = [], [], []
        for i, p in enumerate(pts):
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
            t = t.normalized() if t.length > 1e-9 else Vector((0, 0, 1))
            side = t.cross(nrm).normalized()
            w, th = widths[i] / 2, thicks[i] / 2
            for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                verts.append(tuple(p + side * w * sx + nrm * th * sz))
                uvs.append((dist[i] / tile, (sx * w + sz * th * .3) / tile))
        for i in range(n - 1):
            for k in range(4):
                a = i * 4 + k
                b = i * 4 + (k + 1) % 4
                faces.append((a, a + 4, b + 4, b))
        faces.append((0, 1, 2, 3))
        last = (n - 1) * 4
        faces.append((last + 3, last + 2, last + 1, last))
        self.add(mat, verts, faces, uvs, smooth=smooth)

    def extrude(self, mat, outline, depth, xf=None, tile=.3, smooth=False):
        """A flat carved cut-out: `outline` (x, y) points (any shape) extruded
        `depth` along local z, centred. Front and back UVs are planar."""
        bm = bmesh.new()
        vs = [bm.verts.new((x, y, -depth / 2)) for x, y in outline]
        face = bm.faces.new(vs)
        bmesh.ops.triangulate(bm, faces=[face], quad_method="BEAUTY", ngon_method="EAR_CLIP")
        geom = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
        moved = [g for g in geom["geom"] if isinstance(g, bmesh.types.BMVert)]
        for v in moved:
            v.co.z += depth
        bm.normal_update()
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        verts, faces, uvs = [], [], []
        for f in bm.faces:
            idx = []
            n = f.normal
            for lv in f.verts:
                idx.append(len(verts))
                verts.append(tuple(lv.co))
                if abs(n.z) > .6:
                    uvs.append((lv.co.x / tile, lv.co.y / tile))
                else:
                    uvs.append(((lv.co.x + lv.co.y) / tile, lv.co.z / tile))
            faces.append(tuple(idx))
        bm.free()
        self.add(mat, verts, faces, uvs, smooth=smooth, xf=xf)

    def grid(self, mat, fn, nu, nv, uv=None, smooth=True, xf=None):
        """A parametric surface: fn(u, v) -> point for u, v in 0..1."""
        verts, faces, uvs = [], [], []
        for j in range(nv + 1):
            for i in range(nu + 1):
                u, v = i / nu, j / nv
                verts.append(tuple(fn(u, v)))
                uvs.append(uv(u, v) if uv else (u, v))
        for j in range(nv):
            for i in range(nu):
                a = j * (nu + 1) + i
                faces.append((a, a + 1, a + nu + 2, a + nu + 1))
        self.add(mat, verts, faces, uvs, smooth=smooth, xf=xf)


# ---------------------------------------------------------------- placement


def place(x=0.0, y=0.0, z=0.0, rz=0.0, rx=0.0, ry=0.0, s=1.0):
    return (Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y")
            @ Matrix.Rotation(rx, 4, "X") @ Matrix.Scale(s, 4))


def frame(origin, x_axis, y_axis, z_axis):
    """A matrix mapping local x, y, z to the given world axes at `origin`."""
    m = Matrix.Identity(4)
    for c, axis in enumerate((x_axis, y_axis, z_axis)):
        for r in range(3):
            m[r][c] = axis[r]
    m.translation = Vector(origin)
    return m


# ------------------------------------------------------------------- relief


def _stamp_stroke(h, pts, widths, size_x, size_y, height=1.0):
    """Raise a rounded stroke through `pts` (pixel coordinates) into `h`."""
    for (x, y), w in zip(pts, widths):
        r = int(w) + 2
        x0, x1 = max(0, int(x) - r), min(size_x, int(x) + r + 1)
        y0, y1 = max(0, int(y) - r), min(size_y, int(y) + r + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = np.hypot(xx - x, yy - y) / max(w, .5)
        dome = np.sqrt(np.clip(1 - d * d, 0, 1)) * height
        h[y0:y1, x0:x1] = np.maximum(h[y0:y1, x0:x1], dome)


def _leaf(h, base, direction, length, width, curl, sx, sy, height=1.0):
    """A kbach leaflet: a teardrop that widens and then flicks to a curled point."""
    d = np.array(direction, float)
    d /= np.linalg.norm(d) or 1
    side = np.array([-d[1], d[0]])
    pts, widths = [], []
    steps = max(6, int(length / 1.5))
    for i in range(steps + 1):
        t = i / steps
        bend = curl * t * t * length
        p = np.array(base) + d * length * t + side * bend
        pts.append(p)
        widths.append(max(.6, width * math.sin(math.pi * min(1, t * 1.15)) ** .8))
    _stamp_stroke(h, pts, widths, sx, sy, height)


def kbach_relief(width_px, height_px, seed, kind="pediment"):
    """A heightmap (rows bottom-to-top) of Khmer flame-and-leaf carving (kbach):
    a central flame stack and mirrored scrolls budding curled leaflets. For a
    `pediment` the motif fills a triangle; `band` repeats scrolls along a strip;
    `crest` is a small door-head flame. Values 0 (ground) to about 1."""
    rng = np.random.default_rng(seed)
    w, hh = width_px, height_px
    h = np.zeros((hh, w))

    def spiral(cx, cy, r0, turns, direction, start_angle, thick):
        pts, widths = [], []
        n = int(60 * turns)
        for i in range(n + 1):
            t = i / n
            a = start_angle + direction * t * turns * math.tau
            r = r0 * (1 - .82 * t)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            widths.append(thick * (1 - .55 * t))
        _stamp_stroke(h, pts, widths, w, hh, .8)
        # Leaflets bud off the outside of the scroll, curling with it.
        for i in range(4, n - 8, 9):
            t = i / n
            a = start_angle + direction * t * turns * math.tau
            r = r0 * (1 - .82 * t)
            px, py = cx + r * math.cos(a), cy + r * math.sin(a)
            out = (math.cos(a), math.sin(a))
            tang = (-math.sin(a) * direction, math.cos(a) * direction)
            dvec = (out[0] * .6 + tang[0] * .8, out[1] * .6 + tang[1] * .8)
            _leaf(h, (px, py), dvec, r0 * rng.uniform(.38, .55), thick * 1.1, direction * .35, w, hh, 1.0)

    if kind == "pediment":
        cx = w / 2
        # Central flame: stacked leaves narrowing to the apex.
        for k in range(7):
            y = hh * (.08 + .12 * k)
            size = hh * .16 * (1 - k * .1)
            _leaf(h, (cx, y), (0, 1), size, size * .35, 0, w, hh, 1.0)
            for s in (-1, 1):
                _leaf(h, (cx, y + size * .2), (s * .9, .55), size * .85, size * .22, -s * .4, w, hh, .9)
        for s in (-1, 1):
            for k, (fx, fy, r) in enumerate(((.27, .26, .17), (.14, .16, .11), (.38, .14, .1))):
                spiral(cx + s * w * fx, hh * fy, hh * r * 1.1, 1.25, s, math.pi / 2 + s * .4, hh * .028)
        # A beaded frame just inside the triangle's sloping sides.
        for s in (-1, 1):
            pts = [(cx + s * (w / 2 - 6) * (1 - t), 4 + (hh - 8) * t) for t in np.linspace(0, 1, 160)]
            _stamp_stroke(h, pts, [3.2] * len(pts), w, hh, .7)
            for t in np.linspace(.02, .95, 34):
                _stamp_stroke(h, [(cx + s * (w / 2 - 15) * (1 - t), 12 + (hh - 22) * t)], [3.5], w, hh, 1.0)
        mask = np.zeros_like(h, bool)
        yy, xx = np.mgrid[:hh, :w]
        mask = np.abs(xx - cx) <= (w / 2) * (1 - yy / hh)
        h *= mask
    elif kind == "band":
        reps = max(1, int(round(w / (hh * 1.6))))
        step = w / reps
        for k in range(reps):
            cx = step * (k + .5)
            d = 1 if k % 2 else -1
            spiral(cx, hh * .5, hh * .36, 1.15, d, (0 if d > 0 else math.pi), hh * .07)
        pts = [(x, 3) for x in np.linspace(0, w, 200)]
        _stamp_stroke(h, pts, [2.5] * len(pts), w, hh, .6)
        pts = [(x, hh - 4) for x in np.linspace(0, w, 200)]
        _stamp_stroke(h, pts, [2.5] * len(pts), w, hh, .6)
    else:  # crest
        cx = w / 2
        _leaf(h, (cx, hh * .05), (0, 1), hh * .9, w * .1, 0, w, hh, 1.0)
        for s in (-1, 1):
            spiral(cx + s * w * .22, hh * .38, hh * .3, 1.2, s, math.pi / 2 + s * .5, hh * .06)
            _leaf(h, (cx, hh * .15), (s, .6), w * .42, hh * .09, -s * .5, w, hh, .9)
    # Chisel facets and wear: high points rubbed flat, a little grain.
    h = np.minimum(h, .92 + .08 * rng.random(h.shape))
    return h


def relief_panel(batch, mat, heights, shape, width, height, depth, xf, nu=None, nv=None, tile=.35, base=.004,
                 ground=None, threshold=.12):
    """Real carved geometry: a grid over a `shape` ('rect' or 'tri', apex up)
    raised by `heights` (rows bottom-to-top) up to `depth` metres. Placed by
    `xf`: local x across, y up, z out of the face."""
    hh, ww = heights.shape
    nu = nu or min(ww - 1, 160)
    nv = nv or min(hh - 1, 90)

    def sample(u, v):
        x = min(ww - 1, max(0, u * (ww - 1)))
        y = min(hh - 1, max(0, v * (hh - 1)))
        x0, y0 = int(x), int(y)
        x1, y1 = min(ww - 1, x0 + 1), min(hh - 1, y0 + 1)
        fx, fy = x - x0, y - y0
        a = heights[y0, x0] * (1 - fx) + heights[y0, x1] * fx
        b = heights[y1, x0] * (1 - fx) + heights[y1, x1] * fx
        return a * (1 - fy) + b * fy

    def point(u, v):
        if shape == "tri":
            half = (1 - v) * .5
            uu = .5 + (u - .5) * (1 - v)
            x = (uu - .5) * width
            z = base + depth * sample(uu, v) if 0 < u < 1 and v < 1 else 0.0
            return (x, v * height, z)
        x = (u - .5) * width
        z = base + depth * sample(u, v) if 0 < u < 1 and 0 < v < 1 else 0.0
        return (x, v * height, z)

    verts, uvs, hs = [], [], []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            p = point(u, v)
            verts.append(p)
            uvs.append((p[0] / tile, p[1] / tile))
            hs.append((p[2] - base) / depth if depth else 0)
    hi, lo = [], []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            f = (a, a + 1, a + nu + 2, a + nu + 1)
            (hi if ground is None or max(hs[k] for k in f) > threshold else lo).append(f)
    # Rubbed carving: the gilded motif stands proud of a lacquered ground.
    batch.add(mat, verts, hi, uvs, smooth=True, xf=xf)
    if ground is not None and lo:
        batch.add(ground, verts, lo, uvs, smooth=True, xf=xf)


def moulding(batch, mat, profile, x0, x1, y0, y1, z, tile=.5):
    """A profile swept round a rectangle (plinths, cornices). `profile` is
    (outward offset, height) pairs, bottom to top, offsets from the rectangle."""
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    outs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    verts, faces, uvs = [], [], []
    n = len(profile)
    perim = 0.0
    for c in range(5):
        (cx, cy), (ox, oy) = corners[c % 4], outs[c % 4]
        if c:
            px, py = corners[(c - 1) % 4]
            perim += math.hypot(cx - px, cy - py)
        for j, (off, hz) in enumerate(profile):
            verts.append((cx + ox * off, cy + oy * off, z + hz))
            uvs.append((perim / tile, (hz + off) / tile))
    for c in range(4):
        for j in range(n - 1):
            a = c * n + j
            faces.append((a, a + n, a + n + 1, a + 1))
    batch.add(mat, verts, faces, uvs, smooth=False)
