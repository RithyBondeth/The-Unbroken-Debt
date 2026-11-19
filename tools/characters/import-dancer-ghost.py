"""Prepares the dancer ghost for the Episode 1 studio (November 2026).

The source is the user's own Tripo model (~/Downloads/red-khmer-dancer-ghost.glb, made
on a paid Tripo plan, so the studio owns it): a royal-ballet dancer in a red sampot and
strapless top, a gold mokot crown, her face white with paint, her throat cut and her
hands clawed and bloody, her head lolling to her right, her left arm out in a dance
gesture and her right hand at her waist. It replaced the headless dancer on November 19
(the user: "delete the old model and use this new model instead").

    blender -b --factory-startup --python-exit-code 1 -P tools/characters/import-dancer-ghost.py -- \\
        ~/Downloads/red-khmer-dancer-ghost.glb

tools/areas/statue_prep.py decimates her to about 150k triangles on fresh UVs and bakes
the original's colour and normals onto them at 4K as they are (`original` below: nothing
is regraded). Writes art-source/library/scans/dancer_ghost.glb: 1.85 m to the tip of the
crown (about 1.55 m to the top of her head), her feet at the origin, facing -Y. Then
tools/characters/rig-dancer-ghost.py gives her a skeleton and her dance, and
`npm run assets -- ep1/dancer_ghost` the game's copy.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "areas"))
from statue_prep import node, prepare  # noqa: E402

SRC = os.path.expanduser(sys.argv[sys.argv.index("--") + 1])


def original(nt, base_tex, normal_tex, look, blotch=None):
    """The source's own colour as an emission (for the colour bake) and a Principled with
    its normal map (for the normal bake); same contract as statue_prep.aged."""
    L = nt.links
    for n in list(nt.nodes):
        if n not in (base_tex, normal_tex):
            nt.nodes.remove(n)
    out = node(nt, "ShaderNodeOutputMaterial", (900, 0))
    emit = node(nt, "ShaderNodeEmission", (500, 200))
    L.new(base_tex.outputs["Color"], emit.inputs["Color"])
    nmap = node(nt, "ShaderNodeNormalMap", (300, -300))
    L.new(normal_tex.outputs["Color"], nmap.inputs["Color"])
    bsdf = node(nt, "ShaderNodeBsdfPrincipled", (500, -300))
    L.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return out, emit, bsdf


prepare(
    # High quality (the user, November 19): her face, crown and claws keep their shape,
    # the maps baked at the source's own 4K and kept lossless.
    SRC, "dancer_ghost", 1.85, tris=150000, bake_px=4096, shader=original, image_format="AUTO",
    # Her crown and nails may be pieces of their own: keep every real piece.
    min_piece=500,
    # The silk keeps some of its sheen: it catches the light that falls on her.
    look=dict(roughness=.45),
    extras={
        "title": "Red dancer ghost (the studio's ghost)",
        "author": "The Unbroken Debt (made by the studio with Tripo AI, paid plan)",
        "source": "user-supplied red-khmer-dancer-ghost.glb",
        "license": "Studio-owned (Tripo paid plan: commercial use, no attribution required)",
        "adapted": "decimated to {tris} triangles on new UVs; colour and normals baked from the original at {px} px; scaled to {height} m",
    })
