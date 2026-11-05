"""Fetch the two CC0 MakeHuman child macro targets used by Pich."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT/'art-source/library/makehuman-ep3'
DEST.mkdir(parents=True, exist_ok=True)
entries = []
for name in ['asian-male-child.target', 'universal-male-child-averagemuscle-averageweight.target']:
    url = 'https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/targets/macrodetails/'+name
    path = DEST/name
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    entries.append({'file': name, 'url': url, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'license': 'MakeHuman exported art assets CC0'})
manifest = ROOT/'art-source/characters/ep3/sources.json'
manifest.parent.mkdir(parents=True, exist_ok=True)
if manifest.exists() and json.loads(manifest.read_text()) != entries:
    raise RuntimeError('Recorded character source checksum changed')
manifest.write_text(json.dumps(entries, indent=2)+'\n')
print('Verified child anatomy inputs')
