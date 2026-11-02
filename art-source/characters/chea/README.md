# Chea's aged first-person hands

Episode 2's 1910 memory uses an independent anatomical old Asian male hand, authored through the same weighted pose, subdivision, cropped-skin and normal/roughness bake pipeline as Sora. The exact lamp grip and camera anchors match Episode 1; aged anatomy, photographic pigmentation, deeper joint folds, veins and earth-coloured sleeves distinguish Chea. Both hands retain seven complete named poses. Runtime currently shows the lamp hand, with a small tired tremor.

`tools/ep2/build-chea-hands.py` scopes all outputs to this directory and `public/assets/ep2`. Asserted source substitutions reuse the existing authoring pipeline without writing Sora's files. Normal builds need no Blender or downloads.

- Editable: `chea-hands.blend` (packed textures); portable: `chea-hands.glb`.
- Runtime: `chea_hand.mesh`, `chea_hand_skin.png`, `chea_hand_normal.png`, `chea_hand_roughness.png`.
- The historical `SORA` binary magic identifies the shared file format, not the character.

## Rebuild

```sh
python3 tools/characters/fetch-sok-source.py
python3 tools/characters/fetch-sora-source.py
blender -b -t 4 --factory-startup -P tools/ep2/build-chea-hands.py
```

## Provenance

The mesh, old male macro targets, skeleton/weights and `old_lightskinned_male_diffuse2.png` come from the same official CC0 MakeHuman/MPFB caches recorded in `../sok/sources.json` and `../sora/sources.json`. The photographic skin is the `old_asian_male` entry of the official system asset pack. The raw source caches are ignored; the packed adapted outputs are committed for normal builds. Contributors include Manuel Bastioni, Data Collection AB, Joel Palmius and Jonas Hauquier. See the adjacent CC0 text and the source character READMEs for original URLs and licence details. Added pose composition, surface baking, tremor and integration are project work.
