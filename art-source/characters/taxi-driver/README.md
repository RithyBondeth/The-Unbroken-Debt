# Taxi driver

The seated driver in `public/assets/ep1/ep1_taxi_cabin.glb` is built by `tools/travel/build-taxi.py` (`driver()`) from the same CC0 MakeHuman body as Sok, with an adult Asian male age blend, posed at the wheel with his head turned past Sora toward the trees on her side.

MakeHuman proxies are fitted to the morphed body with their `.mhclo` reference triangles and scaled offsets. Their weights come from the base vertices they ride, so they deform with the same rig:

- `short02` short hair (cut out of its map, darkened, with its own relief);
- `eyebrow002` and `eyelashes01`;
- `high-poly` eyes with the `brown_eye` iris;
- `male_casualsuit01`: its button shirt and trousers keep their folds and seams, but the denim colour is washed to grey and re-dyed as a pale cotton shirt and dark trousers. Body skin the suit covers (`delete_verts`) is removed so nothing pokes through.

A `blink` shape key, baked from MakeHuman's eye-closure targets on the posed body and lashes, lets the runtime close his eyes. The checked krama, wristwatch and white blessing threads are authored in the script.

## Rebuild

```sh
python3 tools/travel/fetch-driver-source.py
blender -b --factory-startup -P tools/travel/build-taxi.py -- cabin
node tools/travel/optimise-taxi.mjs cabin
```

`sources.json` records the zip entry, byte offset and SHA-256 of every file. The fetcher reads only those entries from the official pack with HTTP range requests. `--pin` re-records them after changing the selection. Files land in the ignored `art-source/library/makehuman-driver/` cache.

## Provenance and licence

All proxies come from the [MakeHuman System Assets CC0 pack](https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html) (`makehuman_system_assets_cc0.zip`). Their `.mhclo` headers state the September 2020 CC0 release by Data Collection AB, Joel Palmius and Jonas Hauquier. The base body, macro targets, rig and eye-closure targets are the CC0 inputs listed in `art-source/characters/sok/sources.json`.
