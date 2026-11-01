"""Original-IP integrity and rejected-reference checks; no visual approval."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath


class IdentityError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise IdentityError(message)


def safe_path(root, name):
    need(isinstance(name, str) and name and '\\' not in name, 'Invalid policy path')
    p = PurePosixPath(name)
    need(not p.is_absolute() and '..' not in p.parts, 'Policy path escapes repository')
    resolved = (Path(root) / name).resolve()
    need(resolved.is_relative_to(Path(root).resolve()), 'Policy path escapes repository')
    need(resolved.is_file(), 'Required policy/asset file missing: ' + name)
    return resolved


def load_json(path):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            need(k not in out, 'Duplicate JSON key: ' + k)
            out[k] = v
        return out
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IdentityError(str(exc)) from exc
    need(isinstance(data, dict), 'Policy JSON must be an object')
    return data


def load_policy(root, canon=None):
    root = Path(root).resolve()
    canon = canon if canon is not None else load_json(root / 'references/character-canon.json')
    name = canon.get('identity_policy_path', 'references/identity-policy.json')
    # Minimal external/test fixtures without a recorded origin remain supported.
    if not canon.get('source_revision') and not canon.get('identity_policy_path') and not (root / name).exists():
        return None
    policy = load_json(safe_path(root, name))
    need(policy.get('schema_version') == '1.0', 'Unsupported identity policy')
    for key in ('blocked_sets', 'blocked_ids', 'blocked_paths', 'blocked_sha256', 'required_source_ids'):
        need(isinstance(policy.get(key), list) and all(isinstance(x, str) and x for x in policy[key]),
             'Invalid identity policy field: ' + key)
    return policy


def verify_originals(root, policy=None):
    root = Path(root).resolve()
    policy = policy if policy is not None else load_policy(root)
    need(policy is not None, 'Original-IP policy is required')
    lock = load_json(safe_path(root, policy.get('original_lock')))
    need(isinstance(lock.get('files'), list) and lock['files'], 'Original lock has no files')
    seen = set()
    for item in lock['files']:
        need(isinstance(item, dict), 'Invalid original lock entry')
        name = item.get('path')
        need(isinstance(name, str) and name not in seen, 'Duplicate/invalid original lock path')
        seen.add(name)
        data = safe_path(root, name).read_bytes()
        digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        need(digest == item.get('git_blob_sha'), 'Original IP file changed: ' + name)
    return {'ok': True, 'baseline': lock.get('baseline'), 'checked_files': len(seen)}


def inspect_asset(root, registry, asset_id, policy, visiting=None, checked=None):
    visiting = set() if visiting is None else visiting
    checked = {} if checked is None else checked
    need(asset_id not in visiting, 'Asset ancestry cycle: ' + str(asset_id))
    if asset_id in checked:
        return checked[asset_id]
    need(asset_id in registry, 'Unknown ancestry asset: ' + str(asset_id))
    a = registry[asset_id]
    need(isinstance(a, dict), 'Invalid asset record')
    need(asset_id not in policy['blocked_ids'] and a.get('set_id') not in policy['blocked_sets']
         and a.get('path') not in policy['blocked_paths']
         and a.get('status') not in {'rejected', 'archived'},
         'Rejected/archived identity reference: ' + asset_id)
    raw = safe_path(root, a.get('path')).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    need(digest not in policy['blocked_sha256'], 'Rejected image content (including renamed copies): ' + asset_id)
    need(digest == a.get('sha256'), 'Asset SHA256 mismatch: ' + asset_id)
    provenance = a.get('provenance', {})
    need(isinstance(provenance, dict), 'Invalid provenance: ' + asset_id)
    parents = provenance.get('source_asset_ids', [])
    need(isinstance(parents, list) and all(isinstance(p, str) and p for p in parents),
         'Invalid source_asset_ids: ' + asset_id)
    visiting.add(asset_id)
    ancestors = {asset_id}
    for parent in parents:
        ancestors |= inspect_asset(root, registry, parent, policy, visiting, checked)
    visiting.remove(asset_id)
    checked[asset_id] = ancestors
    return ancestors


def enforce_plan(root, plan):
    policy = load_policy(root)
    if policy is None:
        return False
    verify_originals(root, policy)
    manifest = load_json(safe_path(root, 'assets/asset-manifest.json'))
    entries = manifest.get('assets')
    need(isinstance(entries, list), 'Invalid asset manifest')
    registry = {}
    for a in entries:
        need(isinstance(a, dict) and isinstance(a.get('id'), str) and a['id'] not in registry,
             'Duplicate/invalid manifest ID')
        registry[a['id']] = a
    checked = {}
    for shot in plan.get('shots', []):
        ids = list(shot.get('reference_ids', []))
        ids += [shot[k] for k in ('first_frame_id', 'last_frame_id') if shot.get(k)]
        for asset_id in ids:
            ancestors = inspect_asset(root, registry, asset_id, policy, checked=checked)
            need(set(policy['required_source_ids']) <= ancestors,
                 'Video asset lacks declared original identity/character/shoe ancestry: ' + asset_id)
    return True


if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(json.dumps(verify_originals(args.root), ensure_ascii=False))
    except (IdentityError, OSError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(2)
