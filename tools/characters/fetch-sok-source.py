"""Download hash-verified CC0 model inputs; use Range requests for the skin ZIP."""
import concurrent.futures, hashlib, json, struct, urllib.request, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'art-source/library/makehuman-sok'
DEST.mkdir(parents=True,exist_ok=True)
def request(url, start=None, end=None):
    headers={} if start is None else {'Range':f'bytes={start}-{end}'}
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=120) as r:
        if start is not None and r.status != 206:raise RuntimeError('Asset host must support byte ranges')
        return r.read()
def fetch(e):
    p=DEST/e['file']
    if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256']:return
    if 'zipEntry' not in e:data=request(e['url'])
    else:
        start=e['zipOffset'];header=request(e['url'],start,start+29)
        n,x=struct.unpack_from('<HH',header,26);start+=30+n+x;end=start+e['compressedSize']
        spans=[(a,min(a+262143,end-1)) for a in range(start,end,262144)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            packed=b''.join(pool.map(lambda s:request(e['url'],*s),spans))
        data=zlib.decompress(packed,-15)
    if hashlib.sha256(data).hexdigest()!=e['sha256']:raise RuntimeError('Source checksum changed: '+e['file'])
    p.write_bytes(data);print('Fetched',p.name,flush=True)
for entry in json.loads((ROOT/'art-source/characters/sok/sources.json').read_text()):fetch(entry)
