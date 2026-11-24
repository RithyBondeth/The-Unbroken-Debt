"""Spreads each card texture's colour out into its transparent pixels (alpha left as it
is), so mip levels and a low alpha cut-off show the plant's own colour at the edges, not
the black around it (the game's rice read as dark blotches at a distance, Nov 24, 2026).

    blender -b --factory-startup -P tools/areas/bleed-alpha.py -- TEXTURE.png [...]
"""
import sys

import bpy
import numpy as np

for path in sys.argv[sys.argv.index("--") + 1:]:
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    rgb, alpha = px[..., :3].copy(), px[..., 3].copy()
    filled = alpha > 0.5
    for _ in range(64):
        if filled.all():
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros((h, w), np.float32)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            f = np.roll(np.roll(filled, dy, 0), dx, 1)
            c = np.roll(np.roll(rgb, dy, 0), dx, 1)
            acc += c * f[..., None]
            cnt += f
        grow = (~filled) & (cnt > 0)
        rgb[grow] = acc[grow] / cnt[grow][:, None]
        filled |= grow
    if not filled.all():
        rgb[~filled] = rgb[filled].mean(axis=0)
    out = np.concatenate([rgb, alpha[..., None]], axis=-1)
    img.pixels.foreach_set(out.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    print("bled", path, w, h)
