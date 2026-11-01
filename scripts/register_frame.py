#!/usr/bin/env python3
"""Register a real scene frame as candidate; never invent visual approval."""
from __future__ import annotations
import argparse
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path
from identity_guard import load_json, load_policy, verify_originals, inspect_asset, IdentityError
from prepare_video_pack import image_info, PackError, write_json


def register(root, source, asset_id, set_id, parents, prompt_file):
    root = Path(root).resolve()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', asset_id) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', set_id):
        raise PackError('IDs must use 1-80 lowercase letters, digits, underscore or hyphen')
    if not parents or len(parents) != len(set(parents)):
        raise PackError('Supply the actual distinct source asset IDs')
    raw = Path(source).read_bytes()
    prompt = Path(prompt_file).read_text(encoding='utf-8')
    if not prompt.strip():
        raise PackError('Record the actual nonempty generation prompt')
    width, height, extension = image_info(raw)
    digest = hashlib.sha256(raw).hexdigest()
    policy = load_policy(root)
    verify_originals(root, policy)
    if digest in policy['blocked_sha256'] or set_id in policy['blocked_sets'] or asset_id in policy['blocked_ids']:
        raise PackError('Rejected redesign cannot be registered under a new name')
    manifest_path = root / 'assets/asset-manifest.json'
    lock_path = root / 'assets/.register-frame.lock'
    # Serialize writers. Do not remove an existing lock owned by another process.
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise PackError('Another registration is in progress; inspect stale locks before retrying') from exc
    os.close(fd)
    created = []
    temp_name = None
    try:
        manifest = load_json(manifest_path)
        registry = {a['id']: a for a in manifest['assets']}
        if asset_id in registry or len(registry) != len(manifest['assets']):
            raise PackError('Duplicate asset ID')
        ancestry = set()
        for parent in parents:
            ancestry |= inspect_asset(root, registry, parent, policy)
        if not set(policy['required_source_ids']) <= ancestry:
            raise PackError('Parents must trace to actual original identity, character and shoe references')
        if any(a.get('sha256') == digest for a in registry.values()):
            raise PackError('This exact image is already registered; do not relabel a source sheet as a frame')
        relative = f'assets/shot-frames/{asset_id}{extension}'
        destination = root / relative
        prompt_dest = root / f'assets/shot-frames/{asset_id}.prompt.txt'
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.parent.resolve().is_relative_to(root):
            raise PackError("Scene frame directory escapes repository")
        for path, data in ((destination, raw), (prompt_dest, prompt.encode('utf-8'))):
            with path.open('xb') as stream:
                created.append(path)
                stream.write(data)
        asset = {'id': asset_id, 'path': relative, 'role': 'shot_frame', 'status': 'candidate',
                 'set_id': set_id, 'single_subject': True, 'sha256': digest, 'width': width, 'height': height,
                 'provenance': {'kind': 'registered_scene_frame', 'source_asset_ids': list(parents),
                                'prompt_path': prompt_dest.relative_to(root).as_posix(),
                                'approved_by': None, 'approved_at': None},
                 'notes': ['Reference lineage and single-subject status are operator declarations, not machine visual verification.']}
        manifest['assets'].append(asset)
        fd, temp_name = tempfile.mkstemp(prefix='.manifest-', suffix='.json', dir=manifest_path.parent)
        os.close(fd)
        write_json(Path(temp_name), manifest)
        os.replace(temp_name, manifest_path)
        temp_name = None
        created = []
        return asset
    finally:
        for path in created:
            path.unlink(missing_ok=True)
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)
        lock_path.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--id', required=True)
    parser.add_argument('--set-id', required=True)
    parser.add_argument('--parents', nargs='+', required=True)
    parser.add_argument('--prompt-file', type=Path, required=True)
    args = parser.parse_args()
    try:
        asset = register(Path(__file__).resolve().parents[1], args.source, args.id, args.set_id, args.parents, args.prompt_file)
        print('REGISTERED CANDIDATE:', asset['id'], asset['width'], asset['height'], asset['sha256'])
    except (IdentityError, PackError, OSError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(2)
