"""Episode 1 village nature pass (November 19, 2026; village_nature.py): the user's
scanned trees, palms, bamboo and bananas replace the procedural plants, the Neak Ta
shrine stands under the scanned banyan, the forest floor is scanned litter (decaying
leaves, bark, twigs, roots, mossy stones) under scanned understory (anthurium,
calathea, ferns, shrubs, nettle, periwinkle), and the drowned paddies are planted
with rice at grain filling and a ripe golden field between rebuilt earth dikes.

    blender -b art-source/blender/ep1/ep1_area_village.blend --python-exit-code 1 \\
        -P tools/areas/rebuild-village-nature.py
    npm run export -- ep1/ep1_area_village && npm run assets -- ep1/ep1_area_village.glb

Needs `npm run fetch-library` (Poly Haven plants and ground) and the scans from
tools/areas/prep-village-flora.py. Re-runnable: the pass's own objects live in the
collection `village_nature` and are cleared each run; plants it swaps keep their
names (tree_N, palm_N, bamboo_N, dead_N, banana_N, banyan) so the game finds them.
Every object it does not own is checked unchanged before saving.
"""
import math
import os
import re
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import countryside as C  # noqa: E402
import village_expansion as VE  # noqa: E402
import village_nature as VN  # noqa: E402

TEX = os.path.join(VN.ROOT, "art-source", "textures", "ep1")
# The earth road in from the road bank, dead straight to the compound (the user, Nov 19).
PATH = C.ROAD_LINE
YARD = {"x0": -13.0, "x1": 13.0, "y0": -3.0, "y1": 32.0}
OLD = re.compile(r"^(forest_grass|grove_grass|yard_edge_grass|road_grass|paddy_stubble|house_forest_house_sedge|"
                 r"forest_edge_sedge|jungle_understory|forest_understory|house_forest_forest_understory|"
                 r"jungle_litter|forest_litter|house_forest_forest_litter)")
SWAPPED = re.compile(r"^((col_)?(tree|palm|coco|bamboo|dead|banana)_\d+|banyan|banyan_cloth|neakta_shrine_wet_bark|"
                     r"rock_moss_set_01_rock\d+\.\d+|(col_)?(ragtree|old_flag|termite)_\d+|(col_)?tingmong_\d+|"
                     r"(col_)?ng_termite[\w.]*|(col_)?hero_tree_\d+|col_rock_moss_set_01[\w.]*|banana_g\d+(\.\d+)?|"
                     r"root_cluster_01\.00[12]|ground_offering_[01]|cook_firewood_\d+|puddle_\d+|yard_cart_11|"
                     r"folded_cloth_[12]|ground|col_ground|flood_water|island_tree_02_LOD0\.\d+|"
                     r"(col_)?(shrub|fern|pachira|grass|moss_01|dry_branches|dead_tree_trunk|tree_stump|"
                     r"root_cluster|weed|nettle)[\w.]*)$")


def path_distance(x, y):
    best = 1e9
    for (ax, ay), (bx, by) in zip(PATH, PATH[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - ax - dx * t, y - ay - dy * t))
    return best


def in_yard(x, y, margin=0.0):
    return YARD["x0"] - margin < x < YARD["x1"] + margin and YARD["y0"] - margin < y < YARD["y1"] + margin


def props(obj):
    return {k: v.to_list() if hasattr(v, "to_list") else v.to_dict() if hasattr(v, "to_dict") else v
            for k, v in obj.items()}


def main():
    area = bpy.data.collections["ep1_area_village"]
    own = bpy.data.collections.get("village_nature")
    if own is None:
        own = bpy.data.collections.new("village_nature")
        bpy.context.scene.collection.children.link(own)
    for o in list(own.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    old = [o for o in bpy.data.objects if OLD.match(o.name)]
    untouched = {o.name: (o.matrix_world.copy(), o.data, props(o)) for o in bpy.data.objects
                 if o not in old and not SWAPPED.match(o.name) and o.users_collection
                 and o.users_collection[0].name not in ("village_nature", "_protos", "nature_templates")}
    for o in old:
        bpy.data.objects.remove(o, do_unlink=True)
    print(f"Removed {len(old)} procedural grass, understory and litter patches", flush=True)

    rng = np.random.default_rng(6242300)
    ground = VE.Ground()
    print("2K plant maps:", VN.use_2k_maps(), flush=True)
    made = VN.swap_plants(area, ground, rng, path_distance, in_yard)
    print(f"Swapped {len(made)} plants for scans", flush=True)
    VN.spirit_banyan(area, ground, path_distance)
    VN.litter_ground()
    print(f"Removed {VN.remove_boulders()} boulders", flush=True)
    print(f"Removed clutter: {VN.remove_clutter()}", flush=True)
    C.stand_scarecrows()                # along the straight road, before they are dressed
    print(f"Scarecrows: {VN.scarecrows()}", flush=True)
    placed = VN.floor_cover(own, ground, rng, path_distance, in_yard)
    print(f"Forest floor: {placed}", flush=True)
    hills = {"green": VN.rice_material("M_paddy_rice_green", os.path.join(TEX, "T_ep1_rice_hills_green_BC.png")),
             "ripe": VN.rice_material("M_paddy_rice_ripe", os.path.join(TEX, "T_ep1_rice_hills_ripe_BC.png"))}
    mud = VN.library_material("brown_mud_03", "M_paddy_bund_mud", tint=(0.7, 0.62, 0.55))
    # The countryside round the house (the user, Nov 19): paddies for the jungle.
    print(f"Countryside: {C.build(own, area, rng, path_distance, in_yard, VE.Ground, hills, mud)}", flush=True)
    VN.templates(os.path.join(TEX, "T_ep1_far_trees_BC.png"))
    floaters = ["ground_offering_0", "ground_offering_1", "yard_cart_11", "folded_cloth_1", "folded_cloth_2",
                "puddle_7", "puddle_11"] + [o.name for o in bpy.data.objects if o.name.startswith("cook_firewood_")]
    print(f"Settled {VN.settle(floaters)} floating parts", flush=True)
    VN.unify_palette()

    bpy.context.view_layer.update()
    changed = [n for n, (m, d, p) in untouched.items()
               if not (bpy.data.objects.get(n) and bpy.data.objects[n].matrix_world == m
                       and bpy.data.objects[n].data == d and props(bpy.data.objects[n]) == p)]
    import collections
    print("CHANGED", collections.Counter(re.sub(r"[_.]?\d+$", "", re.sub(r"[_.]\d+$", "", n)) for n in changed).most_common(40),
          flush=True)
    assert not changed, f"{len(changed)} unrelated objects changed"
    for name in ("marker_neakta", "banyan_cloth", "interact_thread", "neakta_stone_watch", "spirit_house"):
        assert bpy.data.objects.get(name), f"Missing gameplay node: {name}"
    if os.environ.get("NATURE_PREVIEW"):
        print("Preview: not saved", flush=True)
        return
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print("Saved", bpy.data.filepath, flush=True)


main()
