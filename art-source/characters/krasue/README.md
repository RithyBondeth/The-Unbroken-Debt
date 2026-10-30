# Krasue: full 3D character

`krasue.blend` is the editable source. Rebuild it and the self-contained runtime
`public/assets/ep1/krasue/krasue-creature.glb` with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background \
  --python art-source/characters/krasue/build_krasue.py -- --preview
```

The deterministic authoring script makes a closed, sculpted skull with projected
nose, cheekbones, brow ridges, sunken sockets, jaw and chin; inset volumetric eyes,
nostrils, mouth and teeth; a fitted scalp with **2,592 separate fine tapered hair
strands** distributed through 18 motion groups; asymmetric heart, paired lungs, lobed liver and stomach;
branching vessels and five long hanging intestinal loops. Hair is geometry with
triangular cross-sections, including from the back and sides. There are no hair cards
or camera-facing silhouette surfaces.

**101 bones** animate hair, organs and intestines through glTF skinning. Runtime
uses damped, weighted joint dynamics driven by flight velocity, acceleration and
turning, with small varied gusts and a subtle heartbeat.
The mesh uses opaque materials and normal maps, rather than an alpha cutout. Its
roughly 245,000 triangles stay within the existing character geometry budget.
The flight heading exposes its profile during the exterior patrol; when alerted
it turns toward Sora. The closest head-origin approach is 75 cm beyond the wall,
leaving room for the real skull and swinging hair and intestines.

`krasue-apparition.png` is original AI-generated reference art from the previous
iteration. Its face RGB is UV-mapped onto the sculpted front of the solid head.
Its silhouette and alpha are never rendered. The remainder of the model uses
procedural PBR colors and the three generated micro-normal maps stored alongside
the GLB. Images are embedded in the exported GLB. The attached stock reference is
visual research only and is not distributed.

The original reference was generated with the built-in image_gen tool on
2026-10-30 using this prompt:

> A single photoreal supernatural Southeast Asian female spirit, isolated on a
> genuinely transparent background. Real pores, fine wrinkles, irregular pale
> gray olive skin, sunken cheeks, dark eye sockets, small milky eyes, an intense
> hostile stare and a slightly open mouth with irregular natural teeth. Long
> dense tangled damp black hair parted at the forehead, flowing down and outward,
> with individually visible flyaway strands. Dark reddish brown twisting root-like
> tendrils emerge below, fading into long dangling wisps. Neck and body concealed
> by hair and roots. No injuries, wounds, blood or exposed anatomy. Full silhouette,
> vertical front view, neutral dim soft lighting, desaturated colors. No background,
> fog, light beams, floor, external shadows, lettering, labels or watermark.

Anatomy, volume, hair strands and organ geometry are authored independently in
Blender. `--preview` also renders front/profile evidence in `debug-shots/`.
Runtime review: `/tests/browser/krasue.html?start=act1`; use **3D turntable** or
**Verify 3D hair and organs**. Technical verification is in
`tests/unit/krasueAsset.test.ts` and `docs/production/krasue-window.md`.

The current hair uses smooth per-strand curves, varied thickness, uneven cuts,
tapered tips and fine flyaways. The scalp follows a curved hairline. Tissue
meshes carry spatial `TissuePigment` vertex colors, subtle wet coats, branched
vessels, tracheal ridges and closed folded mesentery. Two of the five intestinal
chains are hanging U-shaped coils; the other three extend below the organ mass.
`build_krasue.py` generates and packs the complete source reproducibly.

The face now has deeper sockets, raised eyelid edges, cheek/brow creases, a
recessed oral bowl, separate lips, tongue, gums and curved dental arches. A
`Scream` morph opens the jaw and stretches cheek/chin skin; the teeth move as
rigid pieces. Runtime drives every oral morph from the same detection timestamp
as the 2.4 second shriek, including its attack and fading release.

Flight bends are converted through each bone parent's complete rest matrix,
including the glTF handedness reflection. Faster travel produces stronger drag;
hair responds before viscera, and the heavier bundle carries momentum into the
stop. The browser fixture's **Verify rush trail** checks actual deformed tip
positions behind the direction of flight, rather than only checking that bones
move. **Scream detail** holds the mouth open for inspection; **Scream and rush
preview** repeats the flight and articulation visually.

The hairstyle covers the crown, temples, back and jaw sides with a matte fitted
root layer and 2,592 independent fibers. Hanging solid lock volumes have been
removed. Each strand has its own scalp root, angle, thickness, length and gentle
wave, with thinner uneven ends and loose flyaways. Fibers fill the hair volume
rather than wrapping around a large solid core. They are about 1.16–1.70 mm wide
at the root, with finer flyaways and taper toward the ends. Nine rings with triangular cross-sections
keep the denser fiber geometry inside the existing triangle budget. All fibers
use the existing weighted chains, so neighboring groups lag independently while
remaining attached at the scalp.
