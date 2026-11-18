"""Prepares the headless dancer for the Episode 1 studio (November 2026).

The source is the user's own Tripo model (~/Downloads/headless-dancer-ghost.glb,
made on a paid Tripo plan, so the studio owns it): a royal-ballet dancer with no
head, in an indigo sampot and blouse with a gold sbai over one shoulder and a
gold border at the hem, one hand lifted in a dance gesture with the fingers
bent back. She stands in the dark corner of Sora's back room for a moment
before the telephone rings (src/episodes/ep1/prologue/DancerGhost.ts).

    blender -b --factory-startup --python-exit-code 1 -P tools/characters/import-dancer-ghost.py -- \\
        ~/Downloads/headless-dancer-ghost.glb

The generator coloured her skin a bright azure. tools/areas/statue_prep.py
decimates her to about 40k triangles and bakes her colour with `ghostly`
below: dead skin (grey, the blood settled purple in the hands and feet), the
silk faded nearly black and the gold tarnished, the hem wet with earth, and the
stump of the neck and the blouse under it dark with old blood. Writes
art-source/library/scans/dancer_ghost.glb: 1.42 m to the neck, her feet at the
origin, facing -Y (Blender). Then tools/characters/rig-dancer-ghost.py gives her a
skeleton and her dance, and `npm run assets -- ep1/dancer_ghost` the game's copy.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "areas"))
from statue_prep import mix, maprange, math_, node, prepare  # noqa: E402

SRC = os.path.expanduser(sys.argv[sys.argv.index("--") + 1])
# Source units: the figure is 0.978 tall, the neck's stump at the top.
TOP = 0.978


def ghostly(nt, base_tex, normal_tex, look, blotch=None):
    """Emission of the regraded colour (for the colour bake) and a Principled with
    the source's normal map (for the normal bake); same contract as statue_prep.aged."""
    L = nt.links
    for n in list(nt.nodes):
        if n not in (base_tex, normal_tex):
            nt.nodes.remove(n)
    out = node(nt, "ShaderNodeOutputMaterial", (1800, 0))
    geo = node(nt, "ShaderNodeNewGeometry", (-1100, -300))
    pos = node(nt, "ShaderNodeSeparateXYZ", (-900, -300))
    L.new(geo.outputs["Position"], pos.inputs[0])
    nrm = node(nt, "ShaderNodeSeparateXYZ", (-900, -500))
    L.new(geo.outputs["Normal"], nrm.inputs[0])
    col = base_tex.outputs["Color"]
    hsv = node(nt, "ShaderNodeSeparateColor", (-900, 300))
    hsv.mode = "HSV"
    L.new(col, hsv.inputs[0])
    lum = node(nt, "ShaderNodeRGBToBW", (-900, 500))
    L.new(col, lum.inputs[0])
    lum = lum.outputs[0]
    fine = node(nt, "ShaderNodeTexNoise", (-700, -800), Scale=60., Detail=8., Roughness=.65)
    L.new(geo.outputs["Position"], fine.inputs["Vector"])
    big = node(nt, "ShaderNodeTexNoise", (-700, -1000), Scale=9., Detail=6., Roughness=.6)
    L.new(geo.outputs["Position"], big.inputs["Vector"])

    # Skin is the generator's saturated azure; everything else is cloth or gold.
    hue = hsv.outputs[0]
    in_hue = math_(nt, "MULTIPLY", maprange(nt, hue, .53, .565, loc=(-650, 400)), maprange(nt, hue, .68, .645, loc=(-650, 300)), (-450, 350))
    skin = math_(nt, "MULTIPLY", in_hue, maprange(nt, hsv.outputs[1], .36, .48, loc=(-650, 200)), (-300, 300))
    gold = math_(nt, "MULTIPLY", maprange(nt, hue, .05, .09, loc=(-650, 100)), maprange(nt, hue, .2, .16, loc=(-650, 0)), (-450, 50))
    gold = math_(nt, "MULTIPLY", gold, maprange(nt, hsv.outputs[1], .16, .3, loc=(-650, -100)), (-300, 50))

    # Dead skin: grey-green, the blood settled dark brown in the hands and feet and in
    # patches (never purple), darker in every crease.
    pale = mix(nt, (.055, .062, .05), (.24, .255, .205), maprange(nt, lum, .25, .75, loc=(-300, 600)), (-100, 600))
    livor_z = maprange(nt, pos.outputs["Z"], .2, .05, loc=(-300, 750))
    hands = maprange(nt, math_(nt, "ABSOLUTE", pos.outputs["X"], 0., (-450, 900)), .24, .33, loc=(-300, 900))
    livor = math_(nt, "ADD", livor_z, hands, (-150, 850))
    livor = math_(nt, "MULTIPLY", livor, maprange(nt, big.outputs["Fac"], .35, .65, .45, 1., loc=(-300, 1050)), (0, 850))
    skin_c = mix(nt, pale, (.075, .055, .04), livor, (150, 650))

    # Her costume faded and filthy, but still a dancer's: the sampot an old wine-dark
    # maroon below the waist, the blouse above it a dirty yellowed ivory, both keeping
    # the folds of the source's shading and mildewed in patches; the gold thread
    # tarnished, still catching a little light.
    # (The source silk is dark: its luminance runs about 0.02-0.3.)
    shade = maprange(nt, lum, .02, .3, .08, 1., loc=(-300, 200))
    below_waist = maprange(nt, pos.outputs["Z"], .55, .52, loc=(-300, 350))
    sampot = mix(nt, (.045, .006, .006), (.46, .05, .045), shade, (-100, 250))
    blouse = mix(nt, (.07, .062, .045), (.66, .6, .46), shade, (-100, 150))
    cloth = mix(nt, blouse, sampot, below_waist, (50, 200))
    mildew = maprange(nt, big.outputs["Fac"], .58, .78, 0., .3, loc=(-300, 100))
    cloth = mix(nt, cloth, (.07, .075, .05), mildew, (100, 200))
    tarnish = node(nt, "ShaderNodeHueSaturation", (-100, 0), Saturation=.7, Value=.55)
    L.new(col, tarnish.inputs["Color"])
    c = mix(nt, cloth, tarnish.outputs["Color"], gold, (150, 150))
    c = mix(nt, c, skin_c, skin, (350, 300))

    # Creases and folds hold the dark.
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-300, -1200))
    ao.only_local = True
    ao.samples = 16
    ao.inputs["Distance"].default_value = .04
    crease = maprange(nt, ao.outputs["AO"], 1., .5, 0., .7, loc=(-100, -1200))
    c = mix(nt, c, (.012, .01, .009), crease, (550, 250))

    # Earth: wet and dark up from the hem and on the feet, in a broken line.
    mud = maprange(nt, pos.outputs["Z"], .42, .03, loc=(-300, -1400))
    mud = math_(nt, "MULTIPLY", mud, maprange(nt, big.outputs["Fac"], .3, .6, .5, 1.2, loc=(-300, -1550)), (-100, -1450))
    c = mix(nt, c, (.035, .027, .019), mud, (750, 250))

    # Old blood: the stump black-red, and run down the front of the blouse from it in
    # streaks (stretched noise), thinning out by the waist.
    stretch = node(nt, "ShaderNodeVectorMath", (-900, -1700))
    stretch.operation = "MULTIPLY"
    L.new(geo.outputs["Position"], stretch.inputs[0])
    stretch.inputs[1].default_value = (55., 55., 3.)
    streak = node(nt, "ShaderNodeTexNoise", (-700, -1700), Scale=1., Detail=4., Roughness=.55)
    L.new(stretch.outputs[0], streak.inputs["Vector"])
    runs = maprange(nt, streak.outputs["Fac"], .46, .58, loc=(-450, -1700))
    down = maprange(nt, pos.outputs["Z"], .4, TOP - .08, loc=(-450, -1850))
    centre = maprange(nt, math_(nt, "ABSOLUTE", pos.outputs["X"], 0., (-600, -2000)), .16, .05, loc=(-450, -2000))
    front = maprange(nt, nrm.outputs["Y"], .2, -.4, loc=(-450, -2150))
    blood = math_(nt, "MULTIPLY", math_(nt, "MULTIPLY", runs, down, (-250, -1750)), math_(nt, "MULTIPLY", centre, front, (-250, -2050)), (-100, -1900))
    stump = maprange(nt, pos.outputs["Z"], TOP - .05, TOP - .015, loc=(-300, -2250))
    stump = math_(nt, "MULTIPLY", stump, centre, (-100, -2250))
    blood = math_(nt, "ADD", blood, stump, (100, -2000))
    # Spattered down the blouse and the skirt, dried in drops.
    spat = node(nt, "ShaderNodeTexNoise", (-700, -2400), Scale=26., Detail=2., Roughness=.4)
    L.new(geo.outputs["Position"], spat.inputs["Vector"])
    drops = maprange(nt, spat.outputs["Fac"], .66, .7, loc=(-450, -2400))
    drops = math_(nt, "MULTIPLY", drops, maprange(nt, pos.outputs["Z"], .15, .35, loc=(-450, -2550)), (-250, -2450))
    drops = math_(nt, "MULTIPLY", drops, front, (-100, -2450))
    blood = math_(nt, "ADD", blood, math_(nt, "MULTIPLY", drops, .85, (0, -2450)), (150, -2100))
    blood_c = mix(nt, (.05, .006, .004), (.11, .015, .009), fine.outputs["Fac"], (300, -2000))
    c = mix(nt, c, blood_c, math_(nt, "MULTIPLY", blood, .92, (250, -1900)), (950, 250))

    emit = node(nt, "ShaderNodeEmission", (1300, 250))
    L.new(c, emit.inputs["Color"])
    nmap = node(nt, "ShaderNodeNormalMap", (1100, -300))
    L.new(normal_tex.outputs["Color"], nmap.inputs["Color"])
    bsdf = node(nt, "ShaderNodeBsdfPrincipled", (1300, -300))
    L.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return out, emit, bsdf


prepare(
    SRC, "dancer_ghost", 1.42, tris=40000, bake_px=2048, shader=ghostly,
    look=dict(roughness=.62),
    extras={
        "title": "Headless royal-ballet dancer (the studio's ghost)",
        "author": "The Unbroken Debt (made by the studio with Tripo AI, paid plan)",
        "source": "user-supplied headless-dancer-ghost.glb",
        "license": "Studio-owned (Tripo paid plan: commercial use, no attribution required)",
        "adapted": ("decimated to {tris} triangles on new UVs; colour (dead skin, maroon sampot and ivory blouse faded and grimed, "
                    "tarnished gold, earth and old blood) and normals baked from the original at {px} px; scaled to {height} m"),
    })
