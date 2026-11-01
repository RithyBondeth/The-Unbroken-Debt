"""Fetch the taxi driver's CC0 MakeHuman proxies (hair, brows, lashes, eyes, shirt and
trousers) from the official system-assets pack, reading only the needed zip entries.
python3 tools/travel/fetch-driver-source.py [--pin]   (--pin records offsets and hashes)
"""
import hashlib, json, struct, sys, urllib.request, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'art-source/library/makehuman-driver'
MANIFEST=ROOT/'art-source/characters/taxi-driver/sources.json'
PACK='https://files.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip'
WANTED=['hair/short02/short02.obj','hair/short02/short02.mhclo','hair/short02/short02_diffuse.png','hair/short02/short02_normal.png',
    'eyebrows/eyebrow002/eyebrow002.obj','eyebrows/eyebrow002/eyebrow002.mhclo','eyebrows/eyebrow002/eyebrow002.png',
    'eyelashes/eyelashes01/eyelashes01.obj','eyelashes/eyelashes01/eyelashes01.mhclo','eyelashes/eyelashes01/eyelashes01.png',
    'eyes/high-poly/high-poly.obj','eyes/high-poly/high-poly.mhclo','eyes/materials/brown_eye.png',
    'clothes/male_casualsuit01/male_casualsuit01.obj','clothes/male_casualsuit01/male_casualsuit01.mhclo',
    'clothes/male_casualsuit01/male_casualsuit01_diffuse.png','clothes/male_casualsuit01/male_casualsuit01_normal.png']
def get(a,b):
    with urllib.request.urlopen(urllib.request.Request(PACK,headers={'Range':f'bytes={a}-{b}'}),timeout=120) as r:
        if r.status!=206: raise RuntimeError('Asset host must support byte ranges')
        return r.read()
def directory():
    size=int(urllib.request.urlopen(urllib.request.Request(PACK,method='HEAD'),timeout=60).headers['Content-Length'])
    tail=get(size-65536,size-1); e=tail.rfind(b'PK\x05\x06'); length,offset=struct.unpack_from('<II',tail,e+12)
    cd=get(offset,offset+length-1); i=0; found={}
    while i<len(cd):
        method=struct.unpack_from('<H',cd,i+10)[0]; packed=struct.unpack_from('<I',cd,i+20)[0]
        n,x,c=struct.unpack_from('<HHH',cd,i+28); local=struct.unpack_from('<I',cd,i+42)[0]
        found[cd[i+46:i+46+n].decode()]=dict(zipOffset=local,compressedSize=packed,method=method); i+=46+n+x+c
    return found
def read(entry):
    h=get(entry['zipOffset'],entry['zipOffset']+29); n,x=struct.unpack_from('<HH',h,26)
    start=entry['zipOffset']+30+n+x; data=get(start,start+entry['compressedSize']-1)
    return zlib.decompress(data,-15) if entry['method']==8 else data
DEST.mkdir(parents=True,exist_ok=True)
if '--pin' in sys.argv:
    found=directory(); entries=[]
    for name in WANTED:
        e=dict(file=name.split('/')[-1],url=PACK,zipEntry=name,**found[name]); data=read(e)
        e['sha256']=hashlib.sha256(data).hexdigest(); entries.append(e); (DEST/e['file']).write_bytes(data)
    MANIFEST.write_text(json.dumps(entries,indent=2)+'\n')
for e in json.loads(MANIFEST.read_text()):
    p=DEST/e['file']
    if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256']: continue
    data=read(e)
    if hashlib.sha256(data).hexdigest()!=e['sha256']: raise RuntimeError('Source checksum changed: '+e['file'])
    p.write_bytes(data); print('Fetched',p.name,flush=True)
print('Driver sources ready in',DEST)
