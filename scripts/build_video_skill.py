#!/usr/bin/env python3
"""Build/check a self-contained companion without changing original files."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = ['bitdong-character.md','composition-patterns.md','emotion-system.md','prompt-template.md','qa-checklist.md','style-dna.md']
SCRIPTS = ['identity_guard.py','prepare_original_pack.py','prepare_video_pack.py','register_frame.py','verify_assets.py']


def build(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT/'assets/asset-manifest.json').read_text())
    # Ten original source/reference images; no archived design or rejected master.
    selected = [a for a in manifest['assets'] if a['status']=='source']
    originals = [a['path'] for a in selected] + ['references/'+s for s in SPECS]
    copies = originals + ['scripts/'+s for s in SCRIPTS] + ['references/identity-policy.json','references/character-canon.json','templates/shot-plan.example.json','templates/quality-review.example.json','VIDEO_EXTENSION.md']
    for name in copies:
        out=destination/name;out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,out)
    shutil.copyfile(ROOT/'templates/video-skill.md',destination/'SKILL.md')
    shutil.copyfile(ROOT/'VIDEO_EXTENSION.md',destination/'README.md')
    (destination/'agents').mkdir(exist_ok=True)
    (destination/'agents/openai.yaml').write_text('interface:\n  display_name: "Bit东原版视频"\n  short_description: "保留原IP，准备分镜、首帧与视频输入"\n  default_prompt: "使用 $bitdong-video，严格沿用原来的Bit东形象，不重新设计人物。"\n',encoding='utf-8')
    manifest['assets']=selected
    (destination/'assets/asset-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lock={'baseline':'af81f1257ca097368887b3b96d35210e1692f1d6','ok':True,'files':[]}
    for name in sorted(originals):
        data=(ROOT/name).read_bytes()
        lock['files'].append({'path':name,'git_blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
    (destination/'references/original-ip-lock.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    target=ROOT/'skills/bitdong-video'
    if not args.check:
        build(target);print('BUILT',target);return
    with tempfile.TemporaryDirectory() as directory:
        expected=build(Path(directory)/'expected')
        files=sorted(p.relative_to(expected) for p in expected.rglob('*') if p.is_file())
        for name in files:
            actual=target/name
            if not actual.is_file() or actual.read_bytes()!=(expected/name).read_bytes():
                raise SystemExit('Companion differs from original source: '+str(name))
        extra={p.relative_to(target) for p in target.rglob('*') if p.is_file() and '__pycache__' not in p.parts}-set(files)
        if extra: raise SystemExit('Unexpected companion files: '+str(sorted(extra)))
        print('SELF-CONTAINED COMPANION VERIFIED:',len(files),'files')


if __name__=='__main__': main()
