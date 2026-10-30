"""Cold, desaturated grade for the title renders, keeping only lamps, candles and red paint in colour.

  blender -b -P tools/ui/grade-title-scene.py -- <render.png> <graded.png>
  blender -b -P tools/ui/grade-title-scene.py -- <frames folder> <graded folder>
  blender -b -P tools/ui/grade-title-scene.py -- <cords.png> <graded.png> cords

Alpha is kept, so the transparent Neak Ta layers grade exactly like the hall under them.
"""
import os
import sys

import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1 :]
src, out = args[:2]
# The cord layers stay blood red even where moonlight would grey them.
CORDS = "cords" in args[2:]


def grade(path, target):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[::-1]  # display-referred sRGB 0..1, top row first
    rgb, alpha = px[..., :3].copy(), px[..., 3:].copy()
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    # Keep the flame and lamp warm; drain colour everywhere else.
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    warmth = np.clip((r - b) * 2.2, 0, 1) * np.clip((lum - 0.2) * 3.0, 0, 1)
    # Blood-red thread, paint and candle flames survive the grade.
    redness = np.clip((r - np.maximum(g, b)) * 5.0, 0, 1) * np.clip(lum * 12, 0, 1)
    sat = np.maximum(0.2 + 0.65 * warmth, 0.15 + 0.7 * redness)
    rgb = lum[..., None] + (rgb - lum[..., None]) * sat[..., None]
    # Mildewed teal-green shadows and mids, bone-grey highlights.
    shadow = np.clip(1 - lum / 0.45, 0, 1)[..., None]
    rgb = rgb * (1 - shadow * 0.25) + shadow * 0.25 * rgb * np.array([0.78, 1.0, 1.02])
    rgb *= np.array([0.93, 1.0, 1.0])
    # Contrast: crush the blacks, roll the highlights.
    rgb = np.clip((rgb - 0.035) / 0.9, 0, 1)
    rgb = rgb**1.26
    # Darker ceiling and foreground; heavy oval vignette leaves the doorway lit.
    top = np.clip(1 - v / 0.32, 0, 1) ** 1.5 * 0.62
    bottom = np.clip((v - 0.78) / 0.22, 0, 1) ** 1.4 * 0.55
    d = np.sqrt(((u - 0.64) / 0.72) ** 2 + ((v - 0.5) / 0.62) ** 2)
    vig = np.clip((d - 0.42) / 0.6, 0, 1) ** 1.6 * 0.8
    # The menu sits on the left: let that side fall away into the dark.
    left = np.clip((0.5 - u) / 0.5, 0, 1) ** 1.3 * 0.7
    rgb *= (1 - top)[..., None] * (1 - bottom)[..., None] * (1 - vig)[..., None] * (1 - left)[..., None]
    if CORDS:
        glow = (rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
        rgb = rgb * 0.45 + glow * np.array([1.5, 0.16, 0.12]) * 0.55
    # A faint cold lift so blacks never go digital.
    rgb = rgb * 0.97 + np.array([0.012, 0.016, 0.017])
    o = bpy.data.images.new("graded", w, h, alpha=True)
    o.pixels.foreach_set(np.concatenate([np.clip(rgb, 0, 1), alpha], -1)[::-1].astype(np.float32).ravel())
    o.filepath_raw = target
    o.file_format = "PNG"
    o.save()
    bpy.data.images.remove(img)
    bpy.data.images.remove(o)


if os.path.isdir(src):
    os.makedirs(out, exist_ok=True)
    for name in sorted(os.listdir(src)):
        if name.endswith(".png"):
            grade(os.path.join(src, name), os.path.join(out, name))
else:
    grade(src, out)
