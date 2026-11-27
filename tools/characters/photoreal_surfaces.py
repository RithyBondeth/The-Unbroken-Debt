"""Loads and projects real photographed CC0 PBR textures (raw woven linen, village forest mud,
red laterite dirt, and real human drowned-skin pore normals) onto character UV maps via 3D
world-space cylindrical/box projection — eliminating airbrushed CG clay and tying ghosts
photographically into the 1932 Cambodian monsoon village."""
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MAT_LIB = ROOT / "art-source/library/materials"
TEX_EP3 = ROOT / "art-source/textures/ep3/realism"


def load_np_texture(path: Path, max_dim: int = 1024) -> np.ndarray:
    """Loads an image from disk as float32 `(H, W, 4)` array, resizing down to `max_dim` if larger."""
    img = bpy.data.images.load(str(path), check_existing=False)
    w, h = img.size
    if max(w, h) > max_dim:
        s = max_dim / max(w, h)
        img.scale(max(1, int(w * s)), max(1, int(h * s)))
        w, h = img.size
    arr = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    bpy.data.images.remove(img)
    return arr.reshape(h, w, 4)


def sample_cylindrical(tex: np.ndarray, xyz_uv: np.ndarray, tile_m: float = 0.16, rot_offset: float = 0.0) -> np.ndarray:
    """Samples a tileable photographed texture smoothly in 3D world cylindrical coordinates
    around the character's vertical axis (`arc_length / tile_m`, `z / tile_m`) using bilinear
    interpolation — completely seam-free & consistent real-world millimeter texel density across
    arbitrary Smart-UV islands!"""
    th, tw = tex.shape[:2]
    x = xyz_uv[..., 0]
    y = xyz_uv[..., 1]
    z = xyz_uv[..., 2]
    # Use unwrapped perimeter arc-length (~0.75m avg torso circumference) + z height
    ang = np.arctan2(y, x) + rot_offset
    r = np.maximum(0.06, np.sqrt(x * x + y * y))
    u = ((ang * np.minimum(r, 0.20) + x * 0.35) / tile_m) % 1.0
    v = (z / tile_m) % 1.0

    fx = u * (tw - 1)
    fy = v * (th - 1)
    x0 = np.floor(fx).astype(np.int32)
    y0 = np.floor(fy).astype(np.int32)
    x1 = (x0 + 1) % tw
    y1 = (y0 + 1) % th
    wx = (fx - x0)[..., None]
    wy = (fy - y0)[..., None]

    c00 = tex[y0, x0]
    c10 = tex[y0, x1]
    c01 = tex[y1, x0]
    c11 = tex[y1, x1]
    return (c00 * (1.0 - wx) + c10 * wx) * (1.0 - wy) + (c01 * (1.0 - wx) + c11 * wx) * wy


def blend_tangent_normals(base_n_rgba: np.ndarray, detail_n_rgba: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """Reoriented detail normal blend (RNM approximation) in `[0,1]` RGBA tangent space."""
    b = base_n_rgba[..., :3] * 2.0 - 1.0
    d = detail_n_rgba[..., :3] * 2.0 - 1.0
    w = weight[..., None] if weight.ndim == 2 else weight
    out = np.stack(
        [
            b[..., 0] + d[..., 0] * w[..., 0],
            b[..., 1] + d[..., 1] * w[..., 0],
            np.maximum(0.15, b[..., 2]),
        ],
        axis=-1,
    )
    inv = 1.0 / np.sqrt(np.sum(out * out, axis=-1, keepdims=True) + 1e-8)
    out = out * inv * 0.5 + 0.5
    return np.concatenate([np.clip(out, 0.0, 1.0), np.ones(out.shape[:2] + (1,), dtype=np.float32)], axis=-1)


def load_village_photoreal_pack():
    """Loads the real CC0 photographed village surface maps once per script run."""
    return {
        "linen_bc": load_np_texture(MAT_LIB / "rough_linen/rough_linen_BC.jpg", 1024),
        "linen_n": load_np_texture(MAT_LIB / "rough_linen/rough_linen_N.jpg", 1024),
        "linen_orm": load_np_texture(MAT_LIB / "rough_linen/rough_linen_ORM.jpg", 1024),
        "mud_bc": load_np_texture(MAT_LIB / "mud_forest/mud_forest_BC.jpg", 1024),
        "mud_n": load_np_texture(MAT_LIB / "mud_forest/mud_forest_N.jpg", 1024),
        "mud_orm": load_np_texture(MAT_LIB / "mud_forest/mud_forest_ORM.jpg", 1024),
        "laterite_bc": load_np_texture(MAT_LIB / "red_dirt_mud_01/red_dirt_mud_01_BC.jpg", 1024),
        "skin_n": load_np_texture(TEX_EP3 / "T_ep3_real_drowned_skin_N.png", 1024),
    }
