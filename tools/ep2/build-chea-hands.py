"""Build Chea's aged, anatomical hands using the Episode 1 authoring rig.
blender -b --factory-startup -P tools/ep2/build-chea-hands.py
Only writes art-source/characters/chea and public/assets/ep2.
"""
from pathlib import Path
import sys
import types
ROOT=Path(__file__).resolve().parents[2]
CHAR=ROOT/'tools/characters'
sys.path.insert(0,str(CHAR))
# Reuse the exact pose/baking pipeline, with independently scoped source and output.
# Every replacement is asserted so upstream authoring changes cannot touch Sora's assets.
source=(CHAR/'build-sora-hands.py').read_text()
replacements={
    "SRC=ROOT/'art-source/library/makehuman-sora'":"SRC=ROOT/'art-source/library/makehuman-sok'",
    "OUT=ROOT/'public/assets/shared'":"OUT=ROOT/'public/assets/ep2'",
    "EDIT=ROOT/'art-source/characters/sora'":"EDIT=ROOT/'art-source/characters/chea'",
    "['asian-female-young.target','universal-female-young-averagemuscle-averageweight.target']":"['asian-male-old.target','universal-male-old-minmuscle-averageweight.target']",
    'young_lightskinned_female_diffuse3.png':'old_lightskinned_male_diffuse2.png',
    'from sora_skin import build_skin':'from chea_skin import build_skin',
    'sora_hand':'chea_hand',
    'sora-hands':'chea-hands',
    'Sora_connected_female_hand':'Chea_connected_aged_hand',
    'anatomical female hand':'anatomical aged male hand',
}
for old,new in replacements.items():
    if old not in source:raise RuntimeError('Hand pipeline changed: '+old)
    source=source.replace(old,new)
skin=(CHAR/'sora_skin.py').read_text().replace('sora_hand_','chea_hand_').replace('Sora_skin_','Chea_skin_')
# Aged skin retains the photographic pigmentation and has deeper joint folds/veins.
skin=skin.replace("folds, .30", "folds, .38").replace("veins, .00016", "veins, .00024")
module=types.ModuleType('chea_skin');exec(compile(skin,str(CHAR/'sora_skin.py'),'exec'),module.__dict__)
sys.modules['chea_skin']=module
exec(compile(source,str(CHAR/'build-sora-hands.py'),'exec'),{'__file__':str(CHAR/'build-sora-hands.py'),'__name__':'__main__'})
