"""Paints the title lettering as wet red brush strokes: bristles, drips and splatter.

No font: each letter is a hand-placed stroke skeleton dragged with a simulated
bristle brush that runs dry. Uses Blender's Python for numpy and image output:
  blender -b -P tools/ui/paint-title.py -- <out.png> [seed] [listen|icon]
The shipped title uses seed 31. `listen` paints the entry screen's "LISTEN CLOSELY."
in ash-white paint instead (shipped with seed 7). `icon` paints a single heavy "U" in
the title's red for the favicon (shipped with seed 17).
"""
import math
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1 :]
OUT = argv[0]
SEED = int(argv[1]) if len(argv) > 1 else 31
LISTEN = "listen" in argv[2:]
ICON = "icon" in argv[2:]
rng = np.random.default_rng(SEED)

W, H = 4700, 2300
classes = {1.6: None, 2.6: None, 3.8: None}
for r in classes:
    classes[r] = np.zeros((H, W), np.float32)

# Letter skeletons in a box (width, 1 high, y down). Each stroke is a list of points.
def ellipse(cx, cy, rx, ry, a0, a1, n=14):
    return [(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in np.linspace(a0, a1, n)]

LETTERS = {
    "T": (0.78, [[(0.0, 0.03), (0.42, -0.01), (0.82, 0.02)], [(0.42, 0.0), (0.4, 0.55), (0.43, 1.0)]]),
    "H": (0.74, [[(0.0, 0.0), (0.02, 1.0)], [(0.72, -0.02), (0.74, 1.0)], [(-0.02, 0.5), (0.4, 0.47), (0.78, 0.52)]]),
    "E": (0.62, [[(0.02, 0.0), (0.0, 1.0)], [(0.0, 0.0), (0.66, 0.02)], [(0.0, 0.5), (0.52, 0.47)], [(0.0, 1.0), (0.7, 0.97)]]),
    "U": (0.74, [[(0.0, -0.02), (0.0, 0.62)] + ellipse(0.37, 0.64, 0.37, 0.36, math.pi, 0, 12)[1:] + [(0.74, -0.02)]]),
    "N": (0.78, [[(0.0, 1.02), (0.01, 0.0)], [(0.0, 0.0), (0.76, 1.0)], [(0.76, 1.02), (0.78, -0.02)]]),
    "B": (0.7, [[(0.02, -0.01), (0.0, 1.0)],
                [(0.0, 0.0), (0.5, -0.01), (0.66, 0.1), (0.66, 0.36), (0.5, 0.48), (0.04, 0.48)],
                [(0.04, 0.48), (0.56, 0.49), (0.74, 0.62), (0.73, 0.86), (0.54, 0.99), (0.0, 1.0)]]),
    "R": (0.72, [[(0.0, 1.02), (0.02, 0.0)],
                 [(0.02, 0.0), (0.52, -0.01), (0.7, 0.12), (0.69, 0.37), (0.5, 0.5), (0.04, 0.5)],
                 [(0.34, 0.5), (0.58, 0.76), (0.78, 1.02)]]),
    "O": (0.8, [ellipse(0.4, 0.5, 0.4, 0.51, -math.pi * 0.62, math.pi * 1.42, 22)]),
    "K": (0.74, [[(0.0, -0.02), (0.02, 1.02)], [(0.74, -0.02), (0.36, 0.34), (0.03, 0.6)], [(0.26, 0.44), (0.52, 0.72), (0.8, 1.02)]]),
    "L": (0.5, [[(0.02, -0.01), (0.0, 1.0)], [(0.0, 1.0), (0.56, 0.97)]]),
    "I": (0.1, [[(0.03, -0.01), (0.0, 1.01)]]),
    "S": (0.66, [[(0.64, 0.12), (0.46, 0.0), (0.16, 0.02), (0.03, 0.2), (0.14, 0.42), (0.5, 0.54), (0.67, 0.74), (0.56, 0.95), (0.26, 1.0), (0.0, 0.86)]]),
    "C": (0.74, [ellipse(0.42, 0.5, 0.42, 0.51, -math.pi * 0.27, -math.pi * 1.73, 22)]),
    "Y": (0.76, [[(0.0, -0.02), (0.38, 0.5)], [(0.78, -0.02), (0.38, 0.5), (0.37, 1.02)]]),
    ".": (0.1, [[(0.03, 0.9), (0.06, 0.98)]]),
    " ": (0.34, []),
    "D": (0.76, [[(0.02, -0.01), (0.0, 1.0)],
                 [(0.0, 0.0), (0.38, -0.01), (0.68, 0.15), (0.78, 0.5), (0.68, 0.84), (0.38, 1.0), (0.0, 1.0)]]),
}


def catmull(points, step=1.0):
    pts = np.array(points, float)
    if len(pts) == 2:
        length = np.linalg.norm(pts[1] - pts[0])
        t = np.linspace(0, 1, max(2, int(length / step)))[:, None]
        return pts[0] * (1 - t) + pts[1] * t
    pts = np.vstack([pts[0] * 2 - pts[1], pts, pts[-1] * 2 - pts[-2]])
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        n = max(2, int(np.linalg.norm(p2 - p1) / step))
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t**2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t**3))
    out.append(pts[-2][None])
    return np.vstack(out)


def smooth_noise(n, scale, octaves=2):
    """1D value noise in [0, 1]."""
    res = np.zeros(n)
    amp = 1.0
    total = 0.0
    for o in range(octaves):
        k = max(2, int(n / (scale / 2**o)) + 2)
        v = rng.random(k)
        x = np.linspace(0, k - 1.001, n)
        i = x.astype(int)
        f = x - i
        f = f * f * (3 - 2 * f)
        res += amp * (v[i] * (1 - f) + v[i + 1] * f)
        total += amp
        amp *= 0.5
    return res / total


drip_seeds = []


def paint_stroke(path, width, load_bias=1.0):
    """Drag a bristle brush along path (N x 2 px)."""
    seg = np.diff(path, axis=0)
    seglen = np.linalg.norm(seg, axis=1)
    length = seglen.sum()
    # Resample at ~0.8 px.
    cum = np.concatenate([[0], np.cumsum(seglen)])
    n = max(4, int(length / 0.8))
    s = np.linspace(0, length, n)
    px = np.interp(s, cum, path[:, 0])
    py = np.interp(s, cum, path[:, 1])
    tx = np.gradient(px)
    ty = np.gradient(py)
    tl = np.hypot(tx, ty) + 1e-9
    nx, ny = -ty / tl, tx / tl
    t = s / length
    # Pressure: quick landing, slight swell, lift off.
    pressure = np.clip(np.minimum(t / 0.06, 1), 0.45, 1) * (1 - 0.3 * np.clip((t - 0.75) / 0.25, 0, 1)) * (0.9 + 0.2 * smooth_noise(n, 400))
    wobble = (smooth_noise(n, 260) - 0.5) * width * 0.25
    bristles = int(width * 1.3)
    for b in range(bristles):
        off = float(np.clip(rng.normal(0, 0.24), -0.56, 0.56))
        r = rng.choice(list(classes.keys()), p=[0.45, 0.35, 0.2])
        load = (0.75 + 0.35 * rng.random()) * load_bias
        decay = rng.uniform(0.1, 1.3) * (1.3 if abs(off) > 0.3 else 0.6)
        paint = load - decay * t**1.6 + (smooth_noise(n, rng.uniform(30, 120), 2) - 0.5) * 0.5
        if abs(off) > 0.45:
            paint -= 0.18
        on = paint > 0.32
        x = px + nx * (off * width * pressure + wobble)
        y = py + ny * (off * width * pressure + wobble)
        a = (np.clip((paint - 0.32) * 2.2, 0, 1) * rng.uniform(0.5, 1.0))[on]
        ix = np.clip(x[on].round().astype(int), 0, W - 1)
        iy = np.clip(y[on].round().astype(int), 0, H - 1)
        np.maximum.at(classes[r], (iy, ix), a.astype(np.float32))
    # Wet ends collect paint: candidate drips where the brush lifts or lands low.
    for idx in (0, n - 1):
        drip_seeds.append((px[idx], py[idx] + width * 0.25, width))
    # Low points of horizontal-ish strokes.
    if abs(path[-1, 1] - path[0, 1]) < width:
        for _ in range(2):
            k = rng.integers(int(n * 0.15), int(n * 0.85))
            drip_seeds.append((px[k], py[k] + width * 0.3, width))


def write(text, x0, y0, h, track=0.13, slant_deg=0.0, weight=0.17):
    x = x0
    for ch in text:
        lw, strokes = LETTERS[ch]
        ang = math.radians(slant_deg + rng.uniform(-2.5, 2.5))
        lift = rng.uniform(-0.03, 0.03) * h
        scale = h * rng.uniform(0.96, 1.04)
        order = list(range(len(strokes)))
        for si in order:
            pts = []
            for (u, v) in strokes[si]:
                u += rng.normal(0, 0.012)
                v += rng.normal(0, 0.012)
                X = u * scale
                Y = v * scale
                # Shear for a hurried hand.
                X += (1 - v) * scale * math.tan(ang)
                pts.append((x + X, y0 + lift + Y))
            path = catmull(pts, 2.0)
            if rng.random() < 0.35:
                path = path[::-1]
            paint_stroke(path, h * weight * rng.uniform(0.85, 1.12), rng.uniform(0.82, 1.12))
        x += (lw + track) * h


if LISTEN:
    write("LISTEN CLOSELY.", 140, 700, 360, track=0.14, slant_deg=3, weight=0.15)
elif ICON:
    write("U", 1700, 300, 1300, slant_deg=3, weight=0.27)
else:
    write("THE", 560, 120, 300, track=0.16, slant_deg=4, weight=0.2)
    write("UNBROKEN", 300, 520, 610, track=0.1, slant_deg=3)
    write("DEBT", 1700, 1270, 610, track=0.12, slant_deg=3)

# Dilate each bristle class into round bristle tips.
cover = np.zeros((H, W), np.float32)
for r, buf in classes.items():
    rr = int(math.ceil(r))
    acc = buf.copy()
    for dy in range(-rr, rr + 1):
        for dx in range(-rr, rr + 1):
            if dx * dx + dy * dy <= r * r and (dx or dy):
                acc = np.maximum(acc, np.roll(np.roll(buf, dy, 0), dx, 1))
    cover = np.maximum(cover, acc)


def box_blur(a, r):
    if r <= 0:
        return a
    k = 2 * r + 1
    c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0)), mode="edge"), axis=0)
    a = (c[k:] - c[:-k]) / k
    c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r)), mode="edge"), axis=1)
    return (c[:, k:] - c[:, :-k]) / k


# Drips: thin runs from the wettest seeds, ending in a bead.
drips = np.zeros((H, W), np.float32)
rng.shuffle(drip_seeds)
yy, xx = np.mgrid[0:H, 0:W]
count = 0
# Only the lower part of a line drips, so runs never cut through a letter.
LOW = [(120 + 0.62 * 300, 120 + 1.1 * 300), (520 + 0.7 * 610, 520 + 1.1 * 610), (1270 + 0.7 * 610, 1270 + 1.2 * 610)]
if LISTEN:
    LOW = [(700 + 0.72 * 360, 700 + 1.1 * 360)]
if ICON:
    LOW = [(300 + 0.75 * 1300, 300 + 1.1 * 1300)]
for sx, sy, w in drip_seeds:
    if count >= (3 if ICON else 7 if LISTEN else 16) or rng.random() < (0.5 if LISTEN else 0.3) or not any(a < sy < b for a, b in LOW):
        continue
    count += 1
    L = rng.uniform(0.15, 1.0) ** 2 * (260 if LISTEN else 520) + (30 if LISTEN else 40)
    if ICON:
        L = rng.uniform(0.4, 1.0) * 380 + 120
    elif not LISTEN and sy < 1270 and 1640 < sx < 3750:
        L = min(L, 1250 - sy)
    w0 = rng.uniform(0.09, 0.16) * w
    ys = np.arange(int(sy - w0), int(min(H - 40, sy + L)))
    if len(ys) < 4:
        continue
    t = (ys - ys[0]) / len(ys)
    xs = sx + (smooth_noise(len(ys), 200) - 0.5) * 8
    widths = w0 * (1 - 0.45 * t)
    x0, x1 = int(sx - w0 * 3), int(sx + w0 * 3)
    x0, x1 = max(0, x0), min(W, x1)
    sub = xx[ys[0] : ys[-1] + 1, x0:x1]
    d = np.abs(sub - xs[:, None]) / widths[:, None]
    drips[ys[0] : ys[-1] + 1, x0:x1] = np.maximum(drips[ys[0] : ys[-1] + 1, x0:x1], np.clip(1.5 - d, 0, 1))
    # Bead.
    br = widths[-1] * 1.35
    by, bx = ys[-1], xs[-1]
    y0b, y1b = int(by - br - 2), int(by + br + 3)
    x0b, x1b = int(bx - br - 2), int(bx + br + 3)
    sub = (yy[y0b:y1b, x0b:x1b] - by) ** 2 + (xx[y0b:y1b, x0b:x1b] - bx) ** 2
    drips[y0b:y1b, x0b:x1b] = np.maximum(drips[y0b:y1b, x0b:x1b], np.clip((br - np.sqrt(sub)) / 2, 0, 1))

# Flicked splatter.
splat = np.zeros((H, W), np.float32)
ys, xs = np.nonzero(cover[::8, ::8] > 0.5)
for _ in range(14 if ICON else 30 if LISTEN else 70):
    k = rng.integers(len(ys))
    cx = xs[k] * 8 + rng.normal(0, 90)
    cy = ys[k] * 8 + rng.normal(0, 90)
    r = rng.uniform(1.5, 9) ** rng.uniform(0.8, 1.1)
    if not (20 < cx < W - 20 and 20 < cy < H - 20):
        continue
    y0b, y1b, x0b, x1b = int(cy - r - 2), int(cy + r + 3), int(cx - r - 2), int(cx + r + 3)
    sub = np.sqrt((yy[y0b:y1b, x0b:x1b] - cy) ** 2 + (xx[y0b:y1b, x0b:x1b] - cx) ** 2)
    splat[y0b:y1b, x0b:x1b] = np.maximum(splat[y0b:y1b, x0b:x1b], np.clip(r - sub, 0, 1))

cover = np.maximum(box_blur(cover, 1), np.maximum(drips, splat))

# Ragged, absorbed edges: displace by smooth noise.
def field(cells):
    g = rng.random((H // cells + 3, W // cells + 3)).astype(np.float32)
    y = np.arange(H) / cells
    x = np.arange(W) / cells
    iy, ix = y.astype(int), x.astype(int)
    fy, fx = (y - iy)[:, None], (x - ix)[None, :]
    a = g[iy][:, ix] * (1 - fx) + g[iy][:, ix + 1] * fx
    b = g[iy + 1][:, ix] * (1 - fx) + g[iy + 1][:, ix + 1] * fx
    return a * (1 - fy) + b * fy

dx = (field(18) - 0.5) * 7 + (field(5) - 0.5) * 3
dy = (field(18) - 0.5) * 7 + (field(5) - 0.5) * 3
sy = np.clip((yy + dy).astype(int), 0, H - 1)
sx = np.clip((xx + dx).astype(int), 0, W - 1)
cover = cover[sy, sx]

# Colour: thick paint is deep wet red, thin drag marks darker and browner.
body = box_blur(cover, 6)
grain = field(3) * 0.5 + field(40) * 0.5
dens = np.clip(cover * 0.6 + body * 0.6, 0, 1)
dark = np.array([84, 5, 6], np.float32) / 255
mid = np.array([132, 9, 9], np.float32) / 255
bright = np.array([182, 18, 14], np.float32) / 255
if LISTEN:
    # Ash-white, chalky paint: it should not compete with the red title.
    dark, mid, bright = (np.array(c, np.float32) / 255 for c in ([96, 92, 84], [168, 162, 148], [222, 216, 202]))
k = dens[..., None]
rgb = np.where(k < 0.5, dark + (mid - dark) * (k / 0.5), mid + (bright - mid) * ((k - 0.5) / 0.5))
rgb *= (0.86 + 0.24 * grain)[..., None]
# Wet sheen on the upper edge of thick strokes.
sheen = np.clip(-(np.roll(body, -3, 0) - np.roll(body, 3, 0)) * 3.5, 0, 1) * np.clip(body * 1.6 - 0.4, 0, 1)
rgb += sheen[..., None] * (np.array([0.08, 0.08, 0.07]) if LISTEN else np.array([0.26, 0.07, 0.05]))
alpha = np.clip((cover - 0.08) * 1.35, 0, 1) * (0.9 + 0.1 * grain)

# Downsample 2x and crop to content.
def half(a):
    return (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) / 4

premul = rgb * alpha[..., None]
A = half(alpha)
C = np.stack([half(premul[..., i]) for i in range(3)], -1) / np.maximum(A[..., None], 1e-5)
ys, xs = np.nonzero(A > 0.02)
pad = 24
y0, y1 = max(0, ys.min() - pad), min(A.shape[0], ys.max() + pad)
x0, x1 = max(0, xs.min() - pad), min(A.shape[1], xs.max() + pad)
A = A[y0:y1, x0:x1]
C = np.clip(C[y0:y1, x0:x1], 0, 1)
h, w = A.shape
print("TITLE SIZE", w, h)

img = bpy.data.images.new("title", w, h, alpha=True)
img.colorspace_settings.name = "sRGB"
px = np.concatenate([C, A[..., None]], -1)[::-1].astype(np.float32)
img.pixels.foreach_set(px.ravel())
img.filepath_raw = OUT
img.file_format = "PNG"
img.save()
