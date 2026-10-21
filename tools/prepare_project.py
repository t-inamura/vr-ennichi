#!/usr/bin/env python3
"""Deterministic text assets only; never imports or executes original generation scripts."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def generate_regions(manifest):
    regions = []
    for s in manifest['stalls']:
        inward = {'南': (0, 1), '北': (0, -1), '東': (-1, 0), '西': (1, 0)}[s['side']]
        ns = s['side'] in ('南', '北')
        regions.append(dict(id=s['id'], name=s['name'], kind=s['kind'], side=s['side'],
                            x=round(s['x']+2.7*inward[0], 6), z=round(s['y']+2.7*inward[1], 6),
                            halfX=1.5 if ns else 1.0, halfZ=1.0 if ns else 1.5))
    return {'regions': regions}

def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def main():
    resources = ROOT/'Unity/Assets/Ennichi/Resources'
    manifest = json.loads((ROOT/'outputs/scene_manifest.json').read_text())
    assert len(manifest['stalls']) == 48
    write(resources/'scene_manifest.json', manifest)
    write(resources/'visit_regions.json', generate_regions(manifest))
    sky=ROOT/'outputs/assets/sunset.hdr'
    if sky.exists() and not sky.read_bytes()[:64].startswith(b'version https://git-lfs'):
        target=ROOT/'Unity/Assets/Ennichi/Derived/sky.hdr';target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(sky,target)
    # Engine builtin modules are fixed by the Editor version; no registry resolution.
    packages = json.loads((ROOT/'Unity/Packages/manifest.json').read_text())['dependencies']
    write(ROOT/'Unity/Packages/packages-lock.json', {'dependencies': {
        name: {'version': version, 'depth': 0, 'source': 'builtin', 'dependencies': {}}
        for name, version in packages.items()}})
    # Stable GUIDs for authored assets. Preserve existing GUIDs; generated importer data is separate.
    assets = ROOT/'Unity/Assets'
    for p in sorted(assets.rglob('*')):
        if p.suffix == '.meta' or p.name.startswith('.'):
            continue
        meta = p.with_name(p.name+'.meta')
        if meta.exists():
            continue
        guid = hashlib.md5(('ennichi/'+p.relative_to(assets).as_posix()).encode()).hexdigest()
        text = 'fileFormatVersion: 2\nguid: '+guid+'\n'
        if p.is_dir():
            text += 'folderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n'
        elif p.suffix == '.cs':
            text += 'MonoImporter:\n  externalObjects: {}\n  serializedVersion: 2\n  defaultReferences: []\n  executionOrder: 0\n  icon: {instanceID: 0}\n  userData:\n  assetBundleName:\n  assetBundleVariant:\n'
        elif p.suffix == '.asmdef':
            text += 'AssemblyDefinitionImporter:\n  externalObjects: {}\n'
        elif p.suffix == '.json':
            text += 'TextScriptImporter:\n  externalObjects: {}\n'
        elif p.suffix == '.shader':
            text += 'ShaderImporter:\n  externalObjects: {}\n  defaultTextures: []\n  nonModifiableTextures: []\n'
        else:
            text += 'DefaultImporter:\n  externalObjects: {}\n'
        meta.write_text(text)

if __name__ == '__main__':
    main()
