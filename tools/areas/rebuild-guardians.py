"""Update only the village's five guardians without rebuilding the forest.

Run after `npm run drawings -- ep1 tingmong_face` (also tingmong_shirt,
tingmong_wrap and tingmong_weave):
  blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/rebuild-guardians.py
Then `npm run export -- ep1/ep1_area_village` and
`npm run assets -- ep1/ep1_area_village.glb`.
"""
import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from ting_mong import ting_mong

# Reuse the existing support materials; cloth is authored by the shared builder.
m = {key: bpy.data.materials[name] for key, name in {
    'bamboo_dead': 'M_bamboo_dead', 'straw': 'M_straw', 'post_rough': 'M_wet_rough_posts',
}.items()}
# Remove old dedicated cloth so repeated rebuilds preserve stable material names.
for material in list(bpy.data.materials):
    if material.name.startswith('M_tingmong_'):
        bpy.data.materials.remove(material, do_unlink=True)
for image in bpy.data.images:
    if 'T_ep1_tingmong_' in image.name:
        if image.packed_file:
            image.unpack(method='REMOVE')
        image.reload()

specs = [(-1.4, -61.0, -.15, False), (4.4, -60.8, .25, True),
         (-7.5, -71.5, math.pi, True), (-4.4, -26.0, .2, False), (3.8, -8.5, -.3, True)]
for k, (x, y, facing, raised) in enumerate(specs):
    old = bpy.data.objects[f'tingmong_{k}']
    coll = old.users_collection[0]
    bpy.data.objects.remove(old, do_unlink=True)
    body = bpy.data.objects.get(f'col_tingmong_{k}')
    if body:
        bpy.data.objects.remove(body, do_unlink=True)
    figure = ting_mong(coll, m, x, y, facing, k, np.random.default_rng(1910 + k), raised)
    bpy.context.view_layer.update()
    bounds = [figure.matrix_world @ v.co for v in figure.data.vertices]
    height = max(v.z for v in bounds) - min(v.z for v in bounds)
    assert 1.8 < height < 2.3, f'Unexpected guardian height: {height}'
    assert abs(figure.location.x - x) < .001 and abs(figure.location.y - y) < .001
    print(f'{figure.name}: {len(figure.data.polygons)} polygons, {height:.2f}m including stake')

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Five guardians rebuilt; watcher origins and front metadata preserved.')
