"""Building parts for Episode 1's colonial-era family house (1932): lapped
weatherboards, louvred shutters with iron window bars, carved fretwork vents,
scalloped eave valances, chamfered posts on plastered brick plinths and real
Marseille roof tiles. Every part is solid geometry with true thickness, and
every piece rests on or is fixed into the piece that carries it.

Blender axes: X east, Y north, Z up; metres. Run inside Blender.
"""
import math

import bpy
import numpy as np

from kit import box, mesh_object
from khmer import join

BOARD = 0.2  # weatherboard height; colonial_materials paints 10 boards per 2 m tile


def _uv_box(obj, mat, tile, u_axis, v_axis, v_offset=0.0, u_offset=0.0):
    """UVs for a mesh on two world axes at a real-world tile size."""
    mesh = obj.data
    uv = mesh.uv_layers.new(name="UVMap") if not mesh.uv_layers else mesh.uv_layers[0]
    mw = obj.matrix_world
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            c = mw @ mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv = ((c[u_axis] + u_offset) / tile, (c[v_axis] + v_offset) / tile)


def _quad_box(name, coll, corners, mat):
    """A hexahedron from eight corners: bottom four then top four, each counter-clockwise."""
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return mesh_object(name, coll, corners, faces, mat)


def weatherboards(name, coll, along_x, fixed, a0, a1, z0, z1, out, mat, openings=()):
    """Lapped boards on a wall's outer face. `fixed` is the face's position on the
    other axis, `out` (+1/-1) the outward direction. Each board's lower edge stands
    proud of the one beneath (the lap), so lamplight rakes a shadow under every board.
    `openings`: [(a, b, top, sill)] cut through the boards."""
    rows = int(round((z1 - z0) / BOARD))
    parts = []
    for k in range(rows):
        zb, zt = z0 + k * BOARD, min(z1, z0 + (k + 1) * BOARD + 0.025)
        spans, at = [], a0
        for (g0, g1, top, sill) in sorted(openings):
            if zt > sill and zb < top:
                spans.append((at, g0))
                at = g1
        spans.append((at, a1))
        for j, (p0, p1) in enumerate(spans):
            if p1 - p0 < 0.01:
                continue
            thick_b, thick_t = 0.032, 0.012
            def at_(a, z, t):
                return (a, fixed + out * t, z) if along_x else (fixed + out * t, a, z)
            corners = [at_(p0, zb, 0), at_(p1, zb, 0), at_(p1, zb, thick_b), at_(p0, zb, thick_b),
                       at_(p0, zt, 0), at_(p1, zt, 0), at_(p1, zt, thick_t), at_(p0, zt, thick_t)]
            if (out > 0) != along_x:
                corners = [corners[i] for i in (1, 0, 3, 2, 5, 4, 7, 6)]
            b = _quad_box(f"{name}_{k}_{j}", coll, corners, mat)
            # Every board weathers on its own: each samples a different stretch of the
            # painted texture (rows stay aligned with the modelled board edges).
            bpy.context.view_layer.update()
            b.data.uv_layers.remove(b.data.uv_layers[0])
            _uv_box(b, mat, 2.0, 0 if along_x else 1, 2, v_offset=-z0, u_offset=_hash01(name, k, j) * 2.0)
            parts.append(b)
    return join(parts, name)


def _hash01(*key):
    """A repeatable number in [0, 1) from a key."""
    import zlib
    return (zlib.crc32(repr(key).encode()) % 100000) / 100000.0


def tongue_groove(name, coll, along_x, fixed, a0, a1, z0, z1, inward, mat, openings=(), vertical=True):
    """Flush tongue-and-groove lining on a room's face: one slab whose texture
    carries the V-joints (colonial_materials paints 20 boards per 2 m)."""
    parts, at = [], a0
    pieces = []
    for (g0, g1, top, sill) in sorted(openings):
        pieces += [(at, g0, z0, z1), (g0, g1, top, z1), (g0, g1, z0, sill)]
        at = g1
    pieces.append((at, a1, z0, z1))
    for k, (p0, p1, zz0, zz1) in enumerate(pieces):
        if p1 - p0 < 1e-3 or zz1 - zz0 < 1e-3:
            continue
        t0, t1 = sorted((fixed, fixed + inward * 0.015))
        bx = (p0, p1, t0, t1) if along_x else (t0, t1, p0, p1)
        piece = box(f"{name}_{k}", coll, *bx, zz0, zz1, mat)
        bpy.context.view_layer.update()
        piece.data.uv_layers.remove(piece.data.uv_layers[0])
        # Each wall piece starts at its own place in the texture (whole boards, so the
        # V-joints stay where the boards are).
        du, dv = _hash01(name, k) * 2.0, round(_hash01(name, k, "v") * 20) * 0.1
        if vertical:
            _uv_box(piece, mat, 2.0, 2, 0 if along_x else 1, u_offset=du, v_offset=dv)
        else:
            _uv_box(piece, mat, 2.0, 0 if along_x else 1, 2, u_offset=du, v_offset=dv)
        parts.append(piece)
    return join(parts, name)


def _pivot_at_origin(obj):
    """After a join the object's origin is the first part's centre; put it back at
    the world origin (the hinge the leaf was built around) without moving the mesh."""
    bpy.context.view_layer.update()
    obj.data.transform(obj.matrix_world)
    obj.matrix_world.identity()
    return obj


def louvred_leaf(name, coll, width, height, mat, iron=None, slat_pitch=0.05, outward=1):
    """A louvred shutter leaf built at the origin, hinge edge on the Z axis, closed
    along +X, outside facing -Y: stiles, three rails and angled slats housed in
    the stiles, two strap hinges. The slats slope down to the outside; pass
    `outward=-1` when the leaf will be turned so its -Y face looks indoors.
    The caller moves and swings it."""
    t = 0.05
    parts = [
        box(f"{name}_stile_h", coll, 0.0, 0.055, -t / 2, t / 2, 0, height, mat),
        box(f"{name}_stile_f", coll, width - 0.055, width, -t / 2, t / 2, 0, height, mat),
    ]
    rails = [(0, 0.09), (height * 0.48, height * 0.48 + 0.07), (height - 0.07, height)]
    for k, (r0, r1) in enumerate(rails):
        parts.append(box(f"{name}_rail_{k}", coll, 0.05, width - 0.05, -t / 2, t / 2, r0, r1, mat))
    # Deep, steep slats overlap: no sky shows between them at eye level.
    tilt = -math.radians(50) * outward
    for (lo, hi) in ((rails[0][1], rails[1][0]), (rails[1][1], rails[2][0])):
        n = max(1, int((hi - lo) / slat_pitch))
        for k in range(n):
            zc = lo + (k + 0.5) * (hi - lo) / n
            slat = box(f"{name}_slat", coll, 0.05, width - 0.05, -0.03, 0.03, zc - 0.004, zc + 0.004, mat,
                       tilt=(tilt, 0, 0))
            parts.append(slat)
    leaf = _pivot_at_origin(join(parts, name))
    if iron is not None:
        for k, z in enumerate((0.12, height - 0.14)):
            strap = box(f"{name}_hinge_{k}", coll, -0.03, 0.22, -t / 2 - 0.004, -t / 2, z - 0.016, z + 0.016, iron)
            strap.parent = leaf
    return leaf


def hang(leaf, hinge, angle):
    """Puts a leaf built by louvred_leaf on its hinge (x, y, z) swung `angle` radians."""
    leaf.location = hinge
    leaf.rotation_euler = (0, 0, angle)


def window_bars(name, coll, along_x, fixed, a, b, sill, top, iron, count=5):
    """Round iron bars set into the sill and head, as on every 1920s town house."""
    bars = []
    for k in range(count):
        p = a + (b - a) * (k + 1) / (count + 1)
        x, y = (p, fixed) if along_x else (fixed, p)
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.009, depth=top - sill + 0.04,
                                            location=(x, y, (sill + top) / 2))
        bar = bpy.context.active_object
        bar.name = f"{name}_{k}"
        for c in bar.users_collection:
            c.objects.unlink(bar)
        coll.objects.link(bar)
        bar.data.materials.append(iron)
        bars.append(bar)
    obj = join(bars, name)
    _uv_box(obj, iron, 0.5, 0 if along_x else 1, 2)
    return obj


def fretwork(name, coll, along_x, fixed, a, b, z0, z1, mat, depth=0.03, rays=9):
    """A fanlight vent over a door or window: a frame filled with a sunburst of
    rays from a half-round hub on the sill, crossed by an arc, cut from teak."""
    parts = []
    d = depth / 2

    def bx(n, p0, p1, q0, q1, zz0, zz1):
        if along_x:
            return box(n, coll, p0, p1, fixed + q0, fixed + q1, zz0, zz1, mat)
        return box(n, coll, fixed + q0, fixed + q1, p0, p1, zz0, zz1, mat)

    def bar(n, cu, cz, length, angle, w=0.022, t=d * .8):
        if along_x:
            o = box(n, coll, cu - length / 2, cu + length / 2, fixed - t, fixed + t, cz - w / 2, cz + w / 2, mat)
            o.rotation_euler = (0, -angle, 0)
        else:
            o = box(n, coll, fixed - t, fixed + t, cu - length / 2, cu + length / 2, cz - w / 2, cz + w / 2, mat)
            o.rotation_euler = (angle, 0, 0)
        return o

    parts.append(bx(f"{name}_head", a, b, -d, d, z1 - 0.035, z1))
    parts.append(bx(f"{name}_foot", a, b, -d, d, z0, z0 + 0.04))
    parts.append(bx(f"{name}_l", a, a + 0.035, -d, d, z0, z1))
    parts.append(bx(f"{name}_r", b - 0.035, b, -d, d, z0, z1))
    cu, cz = (a + b) / 2, z0 + 0.04
    half_w, high = (b - a) / 2 - 0.035, z1 - 0.035 - cz
    for k in range(rays):
        ang = math.radians(10 + 160 * k / (rays - 1))
        c, s_ = math.cos(ang), math.sin(ang)
        reach = min(half_w / max(abs(c), 1e-6), high / max(s_, 1e-6)) + 0.01
        parts.append(bar(f"{name}_ray", cu + c * reach / 2, cz + s_ * reach / 2, reach, ang))
    # The arc across the rays, in short straight segments.
    r = high * 0.62
    seg = 10
    for k in range(seg):
        a0, a1 = math.pi * k / seg, math.pi * (k + 1) / seg
        p0 = (cu + math.cos(a0) * r, cz + math.sin(a0) * r)
        p1 = (cu + math.cos(a1) * r, cz + math.sin(a1) * r)
        length = math.dist(p0, p1) + 0.01
        ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        parts.append(bar(f"{name}_arc", (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, length, ang, w=0.02))
    # The hub: a half-round boss on the sill rail.
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=high * 0.2, depth=depth,
                                        location=(cu, fixed, cz) if along_x else (fixed, cu, cz),
                                        rotation=(math.pi / 2, 0, 0) if along_x else (0, math.pi / 2, 0))
    hub = bpy.context.active_object
    for c_ in hub.users_collection:
        c_.objects.unlink(hub)
    coll.objects.link(hub)
    hub.data.materials.append(mat)
    parts.append(hub)
    bpy.context.view_layer.update()
    obj = join(parts, name)
    _uv_box(obj, mat, 0.8, 0 if along_x else 1, 2)
    return obj


def valance(name, coll, along_x, fixed, a0, a1, z_top, mat, drop=0.22, scallop=0.16, thick=0.022):
    """The eave's fretwork valance: one board with a scalloped lower edge and a
    pierced drop-hole in each scallop, nailed to the fascia."""
    verts, faces = [], []
    n = max(1, int((a1 - a0) / scallop))
    step = (a1 - a0) / n
    prof = []
    for k in range(n):
        for j in range(7):
            s = j / 6
            p = a0 + step * (k + s)
            depth = drop - 0.07 * math.sin(math.pi * s)
            prof.append((p, z_top - depth))
    prof.append((a1, z_top - drop))
    top = [(p, z_top) for p, _ in prof]
    for i, ((p, zb), (_, zt)) in enumerate(zip(prof, top)):
        for t in (0, thick):
            q = fixed + t
            verts.append((p, q, zb) if along_x else (q, p, zb))
            verts.append((p, q, zt) if along_x else (q, p, zt))
    m = len(prof)
    for i in range(m - 1):
        a, b = i * 4, (i + 1) * 4
        faces += [(a, b, b + 1, a + 1), (a + 2, a + 3, b + 3, b + 2), (a, a + 2, b + 2, b), (a + 1, b + 1, b + 3, a + 3)]
    faces += [(0, 1, 3, 2), ((m - 1) * 4, (m - 1) * 4 + 2, (m - 1) * 4 + 3, (m - 1) * 4 + 1)]
    if not along_x:
        # Swapping the axes mirrors the board: turn its faces back outwards.
        faces = [tuple(reversed(f)) for f in faces]
    obj = mesh_object(name, coll, verts, faces, mat)
    _uv_box(obj, mat, 0.8, 0 if along_x else 1, 2)
    return obj


def plinth_post(name, coll, x, y, z_top, post_mat, plinth_mat, size=0.24, plinth=0.52, plinth_h=0.5):
    """A square chamfered teak post standing on a lime-plastered brick plinth."""
    pl = box(f"{name}_plinth", coll, x - plinth / 2, x + plinth / 2, y - plinth / 2, y + plinth / 2, -0.12, plinth_h,
             plinth_mat, edge=0.02)
    cap = box(f"{name}_cap", coll, x - plinth / 2 - 0.03, x + plinth / 2 + 0.03, y - plinth / 2 - 0.03,
              y + plinth / 2 + 0.03, plinth_h, plinth_h + 0.05, plinth_mat, edge=0.012)
    post = box(name, coll, x - size / 2, x + size / 2, y - size / 2, y + size / 2, plinth_h + 0.05, z_top, post_mat,
               edge=0.025)
    _grain_up(post, 1.0)
    return post, pl, cap


def _grain_up(obj, tile):
    """UVs with the grain (texture u) running up every side face of a post, and across
    its end grain at top and bottom."""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv = mesh.uv_layers[0]
    mw = obj.matrix_world
    for poly in mesh.polygons:
        n = poly.normal
        for li in poly.loop_indices:
            c = mw @ mesh.vertices[mesh.loops[li].vertex_index].co
            if abs(n.z) > 0.7:
                uv.data[li].uv = (c.x / tile, c.y / tile)
            elif abs(n.x) >= abs(n.y):
                uv.data[li].uv = (c.z / tile, c.y / tile)
            else:
                uv.data[li].uv = (c.z / tile, c.x / tile)


def _marseille_mesh(underside=True):
    """One Marseille tile (0.25 x 0.42 m): two channels and a roll, true thickness.
    The head end lies under the next course and is left open; `underside=False`
    keeps only the top and the lower lip (for courses never seen from below)."""
    w, length, t = 0.25, 0.42, 0.014
    xs = np.linspace(0, w, 9)

    def z_of(x):
        s = x / w
        return 0.018 * np.cos(s * 2 * np.pi * 2) * (1 - 0.3 * s) + 0.012 * (s > .86) * np.sin((s - .86) / .14 * np.pi)
    verts, faces = [], []
    for y in (0.0, length):
        for x in xs:
            verts.append((x, y, z_of(x)))
            verts.append((x, y, z_of(x) - t))
    nx = len(xs)

    def vi(row, i, bottom):
        return row * nx * 2 + i * 2 + bottom
    for i in range(nx - 1):
        faces.append((vi(0, i, 0), vi(0, i + 1, 0), vi(1, i + 1, 0), vi(1, i, 0)))
        faces.append((vi(0, i, 0), vi(0, i, 1), vi(0, i + 1, 1), vi(0, i + 1, 0)))
        if underside:
            faces.append((vi(0, i, 1), vi(1, i, 1), vi(1, i + 1, 1), vi(0, i + 1, 1)))
    if underside:
        faces.append((vi(0, 0, 0), vi(1, 0, 0), vi(1, 0, 1), vi(0, 0, 1)))
        faces.append((vi(0, nx - 1, 0), vi(0, nx - 1, 1), vi(1, nx - 1, 1), vi(1, nx - 1, 0)))
    return verts, faces


def tiled_slope(name, coll, x0, x1, eave, ridge, mat, rng, missing=0.015, cover=0.21, courses_from=0, seen_below=None):
    """Marseille tiles laid in courses up a slope from `eave` (y, z) to `ridge`
    (y, z), across x0..x1, each tile lapping the one below and lying on it.
    A few have slipped or are missing; each samples its own patch of the texture."""
    full = _marseille_mesh(True)
    slim = _marseille_mesh(False)
    (ye, ze), (yr, zr) = eave, ridge
    slope = math.hypot(yr - ye, zr - ze)
    uy, uz = (yr - ye) / slope, (zr - ze) / slope
    ny, nz = -uz, uy
    # Keep the frame right-handed: on a north slope the tiles are laid from the east.
    mirror = nz < 0
    if mirror:
        ny, nz = -ny, -nz
    exposed = 0.34
    courses = int(slope / exposed)
    cols = int((x1 - x0) / cover)
    centre = (x0 + x1) / 2
    x0 = x0 + ((x1 - x0) - cols * cover) / 2
    verts, faces, uvs = [], [], []
    for c in range(courses_from, courses):
        for k in range(cols):
            if rng.random() < missing:
                continue
            slip = rng.normal(0, 0.006)
            lift = 0.032 + rng.normal(0, 0.003)
            twist = rng.normal(0, 0.012)
            ox, ov = rng.random(), rng.random()
            s0 = c * exposed + slip
            base_v, base_f = full if seen_below is None or c < seen_below else slim
            base = len(verts)
            for (bx_, by_, bz_) in base_v:
                x = x0 + k * cover + bx_ + twist * by_
                if mirror:
                    x = 2 * centre - x
                s = s0 + by_
                # Each tile's head rests on the course above's tail: it tilts up slightly.
                h = bz_ + lift * (1 - by_ / 0.42) + 0.03
                verts.append((x, ye + uy * s + ny * h, ze + uz * s + nz * h))
                uvs.append((ox + bx_ / 1.0, ov + by_ / 1.0))
            for f in base_f:
                faces.append(tuple(base + i for i in f))
    loop_uvs = [uvs[i] for f in faces for i in f]
    return mesh_object(name, coll, verts, faces, mat, uvs=loop_uvs)


def panelled_door(name, coll, width, height, mat, iron=None, thickness=0.044):
    """A four-panel door leaf built at the origin, hinge edge on the Z axis, closed
    along +X: stiles and rails with raised panels set back between them, and
    two strap hinges. The caller moves and swings it with hang()."""
    t = thickness
    two = width >= 0.6
    parts = [
        box(f"{name}_stile_h", coll, 0.0, 0.11, -t / 2, t / 2, 0, height, mat),
        box(f"{name}_stile_f", coll, width - 0.11, width, -t / 2, t / 2, 0, height, mat),
    ]
    if two:
        parts.append(box(f"{name}_muntin", coll, width / 2 - 0.045, width / 2 + 0.045, -t / 2, t / 2, 0.2, height - 0.12, mat))
    rails = [(0, 0.2), (height * 0.42, height * 0.42 + 0.16), (height - 0.12, height)]
    for k, (r0, r1) in enumerate(rails):
        parts.append(box(f"{name}_rail_{k}", coll, 0.1, width - 0.1, -t / 2, t / 2, r0, r1, mat))
    for (lo, hi) in ((rails[0][1], rails[1][0]), (rails[1][1], rails[2][0])):
        cols = ((0.11, width / 2 - 0.045), (width / 2 + 0.045, width - 0.11)) if two else ((0.11, width - 0.11),)
        for (a, b) in cols:
            # The raised field and its bevelled margin, thinner than the frame.
            parts.append(box(f"{name}_panel", coll, a, b, -t * 0.27, t * 0.27, lo, hi, mat))
            parts.append(box(f"{name}_field", coll, a + 0.04, b - 0.04, -t * 0.38, t * 0.38, lo + 0.04, hi - 0.04, mat, edge=0.008))
    leaf = _pivot_at_origin(join(parts, name))
    if iron is not None:
        for k, z in enumerate((0.25, height - 0.3)):
            strap = box(f"{name}_hinge_{k}", coll, -0.02, 0.3, -t / 2 - 0.004, -t / 2, z - 0.02, z + 0.02, iron)
            strap.parent = leaf
    return leaf


def against(parent, wall_axis, wall_at, toward, floor_z=0.0):
    """Moves an imported model (its empty `parent`) so it stands on `floor_z` with
    its back flush to a wall at `wall_at` on axis 0 (x) or 1 (y); `toward` is the
    room side (+1/-1). Nothing ends up floating or sunk."""
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in parent.children_recursive if o.type == "MESH" for v in o.data.vertices]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    loc = list(parent.location)
    loc[2] += floor_z - lo[2]
    if wall_axis is not None:
        back = lo[wall_axis] if toward > 0 else hi[wall_axis]
        loc[wall_axis] += wall_at - back
    parent.location = loc
    bpy.context.view_layer.update()
    return parent


def wall_print(name, coll, atlas, item, mat, centre, right, up, width, curl=0.015, pins=None, seed=0):
    """A colour print pasted or pinned to a wall: `atlas` is a studio_prints.json
    atlas spec, `item` its key; `right`/`up` are the directions across the face as
    a viewer sees it. The paper hangs from its top edge, flat to the wall there,
    and its lower edge has curled `curl` metres away from the boards with the damp.
    `pins`: a material for brass pins at the two top corners."""
    S = atlas["size"][0]
    x, y, w, h = atlas["items"][item]["rect"]
    height = width * h / w
    r = np.array(right, float); r /= np.linalg.norm(r)
    u = np.array(up, float); u /= np.linalg.norm(u)
    n = np.cross(r, u)
    c = np.array(centre, float)
    rng = np.random.default_rng(seed)
    nu, nv = 8, 10
    verts, faces, uvs = [], [], []
    u0, u1 = x / S, (x + w) / S
    v0, v1 = 1 - (y + h) / S, 1 - y / S
    side = rng.choice([-1, 1])
    for j in range(nv + 1):
        t = j / nv  # 0 at the bottom, 1 at the top
        for i in range(nu + 1):
            s = i / nu
            lift = curl * (1 - t) ** 2.2 * (0.55 + 0.45 * (s if side > 0 else 1 - s)) + 0.0006
            p = c + r * (s - .5) * width + u * (t - .5) * height + n * lift
            verts.append(tuple(p))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + 1, a + nu + 2, a + nu + 1))
            for (ii, jj) in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                uvs.append((u0 + (u1 - u0) * ii / nu, v0 + (v1 - v0) * jj / nv))
    sheet = mesh_object(name, coll, verts, faces, mat, uvs=uvs)
    sheet.data.materials[0].use_backface_culling = False
    if pins is not None:
        for k, s in enumerate((0.04, 0.96)):
            p = c + r * (s - .5) * width + u * (.5 * height - 0.03)
            bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.0055, depth=0.003, location=tuple(p + n * 0.0015))
            pin = bpy.context.active_object
            pin.name = f"{name}_pin_{k}"
            for c_ in pin.users_collection:
                c_.objects.unlink(pin)
            coll.objects.link(pin)
            pin.rotation_euler = (np.array(n) @ np.array([0, 1, 0]) * math.pi / 2, np.array(n) @ np.array([1, 0, 0]) * math.pi / 2, 0)
            pin.data.materials.append(pins)
    return sheet
