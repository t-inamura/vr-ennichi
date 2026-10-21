#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import zipfile

def inspect(path,manifest_path):
    stalls=json.loads(manifest_path.read_text())['stalls'];bounds={};vertices=triangles=0
    minimum=[float('inf')]*3;maximum=[float('-inf')]*3;color_min=float('inf');color_max=float('-inf')
    with zipfile.ZipFile(path) as z:
        meta=json.loads(z.read('manifest.json'));assert meta['formatVersion']==2
        assert not meta['subset'] and meta['sourceObjects']==11177
        assert meta['sourceSha256']=='80f4250595674cb13faeeb7904b8536f2a2963d1924f33a440e32bb53bea4413'
        assert len({c['file'] for c in meta['chunks']})==len(meta['chunks'])
        for c in meta['chunks']:
            data=z.read(c['file']);nv,ni=struct.unpack_from('<II',data)
            assert nv==c['vertices'] and ni==c['triangles']*3 and ni%3==0
            assert len(data)==8+40*nv+4*ni and 3<=nv<=60000
            lo,hi=bounds.setdefault(c['name'],([float('inf')]*3,[float('-inf')]*3))
            for record in struct.iter_unpack('<10f',data[8:8+nv*40]):
                assert all(math.isfinite(v) for v in record)
                for i in range(3):lo[i]=min(lo[i],record[i]);hi[i]=max(hi[i],record[i]);minimum[i]=min(minimum[i],record[i]);maximum[i]=max(maximum[i],record[i])
                color_min=min(color_min,*record[6:9]);color_max=max(color_max,*record[6:9])
            for (index,) in struct.iter_unpack('<I',data[8+nv*40:]):assert index<nv
            vertices+=nv;triangles+=ni//3
    assert vertices==meta['vertices'] and triangles==meta['triangles']
    for s in stalls:
        lo,hi=bounds['STALL_%02d'%s['id']]
        assert lo[0]<s['x']<hi[0] and lo[2]<s['y']<hi[2],s
        assert 2.5<hi[1]<5.5 and hi[0]-lo[0]<5.5 and hi[2]-lo[2]<5.5,s
    assert len([k for k in bounds if k.startswith('STALL_')])==48
    return dict(status='structural_pass',appearance=meta['appearance'],visual_approved=False,
                vertices=vertices,triangles=triangles,chunks=len(meta['chunks']),stalls=48,
                bounds_unity_m=[minimum,maximum],color_range=[color_min,color_max],
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('asset',type=Path);parser.add_argument('--manifest',type=Path,default=Path('outputs/scene_manifest.json'))
    args=parser.parse_args();print(json.dumps(inspect(args.asset,args.manifest),indent=2))
