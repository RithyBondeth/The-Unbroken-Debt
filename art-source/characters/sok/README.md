# Sok's funeral body

The previous runtime spheres have been replaced by an anatomically modelled aged Asian male, posed with MakeHuman's individual finger, arm, neck and head weights. The face uses closed-eye expression targets at rest, sculpted hollow cheeks, sunken temples and loose lower cheeks. The skin has desaturated pallor, uneven brown age spots, forehead lines, radial eye creases, deeper folds beside the mouth, fingernails and orbital undertones. Colour and wrinkle relief are baked into 2K textures for glTF; no custom runtime skin shader is needed. In the final pose one eyelid opens slightly over an anatomical clouded eye and the jaw slackens. The shroud is a gravity-settled cotton mesh with body collision, compressed beneath the bare cupped hands. Sok holds a hand-modelled lotus with layered petals, raised veins, dry tips, sepals and a curved stem. The lotus carries the same four baked morph targets as the body, following the right palm through each saved pose.

- Runtime: `public/assets/ep1/sok_corpse.glb` (five pose states: basis plus four morphs for the body, anatomical eyes and held lotus).
- Editable source: `sok-corpse.blend`, with packed textures and named pose shape keys.
- No runtime cloth simulation or skeletal animation. The existing encounter selects a complete pose only when its conservative visibility guard is offscreen; the existing saved pose index is unchanged.
- All new dialogue remains subtitle-only.

## Rebuild

```sh
python3 tools/characters/fetch-sok-source.py
blender -b -P tools/characters/build-sok-corpse.py
```

Raw input files live in the ignored `art-source/library/makehuman-sok/` cache. `sources.json` records the URLs and SHA-256 of every input. The downloader reads only the required skin entry from the official asset pack, rather than fetching the entire pack.

The additional age sculpt and procedural skin treatment are in `tools/characters/sok_age.py`. They are applied in rest space before all five poses are baked, so the facial details travel with the head. The lotus grip and coffin encounter save flags are unchanged.

## Provenance and licence

Human mesh, macro morphs, rig / weights and expression targets: [MakeHuman Community](https://github.com/makehumancommunity/makehuman) and [MPFB](https://github.com/makehumancommunity/mpfb2). Original asset contributors include Manuel Bastioni, Data Collection AB, Joel Palmius and Jonas Hauquier. The asset files are CC0; their software code licences do not apply to exported character assets. See [MakeHuman's asset licence](https://static.makehumancommunity.org/about/license.html).

Aged Asian male skin: `old_lightskinned_male_diffuse2.png` from the official [MakeHuman System Assets CC0 pack](https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html), entry `skins/old_asian_male/`. This pack explicitly lists the skin as CC0. The older 2016 TuxFamily material descriptor was inspected but is **not used or distributed**.

The CC0 text is included as `CC0-1.0.txt`. Lotus geometry, shroud, pillow, pose composition, pallor treatment and integration were authored for this project. The committed `.blend` and `.glb` include the adapted asset, so normal builds need no third-party download.
