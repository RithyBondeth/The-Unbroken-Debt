# Sora’s anatomical first-person hands

The continuous hand and forearm come from the MakeHuman human base, shaped with
its Asian young female and young female average-weight/muscle macro targets.
The surface includes the original thumb web, metacarpals, finger joints, nail
beds and wrist. It replaces the earlier procedural palm/finger surfaces.

The MakeHuman skeleton and per-vertex weights author six complete hand poses:
relaxed, lamp, receiver, journal support, match pinch and reach. Subdivision is
applied after the weighted deformer. The runtime mirrors the left asset for the
right hand and blends the baked positions/normals on the GPU, retaining skin
continuity rather than assembling separate finger tubes.

The lamp grip is authored separately in `tools/characters/sora_grip.py`.
Each phalanx is aligned in anatomical hand space: the four fingers adduct and
curl around the bail wire, while the thumb opposes across them. A shared bend
axis kept the original open-hand splay and sent the thumb outward. The runtime
anchor is centred on the actual handle crown; it follows lamp raising and swing
without inheriting the lantern's 180-degree gauge-facing model rotation.

`blender -b -t 4 -P tools/characters/render-sora-grip.py` renders a close view of
the hand and original lamp geometry together for contact inspection.

The skin is `young_lightskinned_female_diffuse3.png` from the official CC0
`young_asian_female` system-asset skin. Only the UV region needed by the hand and
forearm is included in the runtime atlas. `tools/characters/sora_skin.py` adds an
editable Blender material with skin pores and fine furrows, curved joint folds,
palm/wrist creases and branching dorsal veins. Rest-space position/normal
attributes anchor these details to the anatomy before baking, so they follow all
grip poses. Veins have faint pigmentation and shallow relief; nails have smoother
relief and lower roughness than skin. These authored details supplement the CC0
photo rather than claiming to be captured scan data.

Colour, tangent normal and linear roughness maps are baked at 816×3552. The
runtime uses green-channel roughness with metallic disabled, plus the hand-only
fill; skin does not use emissive colour. All procedural shading is baked during
asset authoring and adds no runtime shader noise or extra geometry.

## Rebuild

```sh
python3 tools/characters/fetch-sora-source.py
blender -b -t 4 -P tools/characters/build-sora-hands.py
```

- `sora-hands.blend`: editable, packed authoring source, hidden weighted source
  hand/rig and the six named pose shape keys (weights default to zero).
- `sora-hands.glb`: portable textured export with the same pose keys.
- `public/assets/shared/sora_hand.mesh`: versioned runtime geometry/pose file.
- `public/assets/shared/sora_hand_skin.png`: cropped photo skin atlas.
- `public/assets/shared/sora_hand_normal.png`: baked tangent normal map.
- `public/assets/shared/sora_hand_roughness.png`: linear surface roughness.

The binary starts with `SORA` and a little-endian uint32 header byte count. Its
padded JSON header gives counts and pose order. Data is uint32 triangle indices,
float32 UVs and, for each pose, interleaved float32 position/normal triples.
`HandAsset.ts` validates and decodes it. These files ship with the game, so normal
builds do not download source assets or need Blender.

## Provenance

`sources.json` records original URLs and SHA-256 hashes for the base OBJ,
MakeHuman skeleton/weights, two macro targets and skin. Raw inputs are in the
ignored `art-source/library/makehuman-sora/` cache. These are the same official
MakeHuman core assets used by the existing character pipeline, with a different
age/sex macro and skin. All used assets are CC0; their software source licences
are separate from exported assets.

- [MakeHuman asset licence](https://static.makehumancommunity.org/about/license.html)
- [System asset pack and skin licences](https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html)
- [MakeHuman source asset repository](https://github.com/makehumancommunity/makehuman)

Original contributors include Manuel Bastioni, Data Collection AB, Joel Palmius
and Jonas Hauquier. The CC0 text is included. The user's reference was used as
visual direction; it is not distributed as a texture or game asset.
