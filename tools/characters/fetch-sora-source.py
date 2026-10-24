"""Fetch CC0 MakeHuman source inputs, checking the recorded SHA-256 values."""
from pathlib import Path
import concurrent.futures,urllib.request,hashlib,json,struct,zlib
ROOT=Path(__file__).resolve().parents[2]; DEST=ROOT/'art-source/library/makehuman-sora'
DEST.mkdir(parents=True,exist_ok=True)
def request(url,start=None,end=None):
    h={} if start is None else {'Range':f'bytes={start}-{end}'}
    with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=120) as r:
        if start is not None and r.status!=206:raise RuntimeError('Range response required')
        return r.read()
def fetch(e):
    path=DEST/e['file']
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==e.get('sha256'):return
    if 'zipEntry' not in e:data=request(e['url'])
    else:
        off=e['zipOffset']; head=request(e['url'],off,off+29)
        a,b=struct.unpack_from('<HH',head,26);off+=30+a+b;end=off+e['compressedSize']
        spans=[(i,min(i+262143,end-1)) for i in range(off,end,262144)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:packed=b''.join(pool.map(lambda s:request(e['url'],*s),spans))
        data=zlib.decompress(packed,-15)
    digest=hashlib.sha256(data).hexdigest()
    if e.get('sha256') and e['sha256']!=digest:raise RuntimeError('Hash mismatch: '+e['file'])
    path.write_bytes(data);e['sha256']=digest;print('Fetched',path.name,flush=True)
if __name__=='__main__':
    manifest=ROOT/'art-source/characters/sora/sources.json'; entries=json.loads(manifest.read_text())
    for e in entries:fetch(e)
    manifest.write_text(json.dumps(entries,indent=2)+'\n')
