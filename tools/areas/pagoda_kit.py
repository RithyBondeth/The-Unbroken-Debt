"""The built kit of sculpted, baked masonry and statuary (tools/ep2/build-stupas.py). Its
pieces are placed many times, sharing their meshes, so they lean as whole objects."""
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / 'art-source/kits/stupa_kit.blend'
_meshes = {}
_materials = {}


def _load():
    if _meshes:
        return
    with bpy.data.libraries.load(str(KIT), link=False) as (src, dst):
        dst.meshes = list(src.meshes)
        dst.materials = [n for n in src.materials if n.startswith('M_ep2_funeral_photo')]
    for me in dst.meshes:
        _meshes[me.name] = me
    for mat in dst.materials:
        _materials[mat.name] = mat


def material(name):
    _load()
    return _materials[name]


def piece(coll, mesh, name, x=0.0, y=0.0, z=0.0, yaw=0.0, scale=1.0, tilt=(0.0, 0.0)):
    """A placed copy of kit mesh `mesh`. Returns the object."""
    _load()
    o = bpy.data.objects.new(name, _meshes[mesh])
    coll.objects.link(o)
    o.rotation_mode = 'XYZ'
    o.location = (x, y, z)
    o.rotation_euler = (tilt[0], tilt[1], yaw)
    o.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
    o['kit_piece'] = True
    return o
