#!/usr/bin/env python3
"""Audit ALL registered BIT东 image files, not only the images in a shot plan.

Checks are mechanical: presence, containment, SHA256, native dimensions and
manifest consistency. This does NOT visually approve an image or test a video.
Requires only the Python standard library.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from prepare_video_pack import PackError, asset_path, image_info, nonblank, read_json


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def audit(root: Path) -> dict:
    root = root.resolve()
    canon = read_json(root / "references" / "character-canon.json")
    manifest = read_json(root / "assets" / "asset-manifest.json")
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise PackError("Manifest assets must be a list")
    errors, warnings, checked = [], [], []
    seen_ids, seen_paths = set(), set()
    counts = Counter()

    if manifest.get("character_id") != canon.get("character_id"):
        errors.append("Manifest and canon character_id mismatch")
    if manifest.get("schema_version") != "1.0" or canon.get("schema_version") != "1.0":
        errors.append("Unsupported manifest or canon schema version")
    approved_set = canon.get("approved_master_set")

    for index, asset in enumerate(assets, 1):
        label = f"asset[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{label}: expected an object")
            continue
        asset_id = asset.get("id")
        if not nonblank(asset_id):
            errors.append(f"{label}: missing id")
            continue
        label = asset_id
        if asset_id in seen_ids:
            errors.append(f"{label}: duplicate id")
        seen_ids.add(asset_id)
        status = asset.get("status")
        counts[str(status)] += 1
        if status not in {"source", "archived", "candidate", "approved"}:
            errors.append(f"{label}: invalid status {status!r}")
        if not nonblank(asset.get("role")):
            errors.append(f"{label}: missing role")
        if status in {"candidate", "approved"} and asset.get("role") == "character_master":
            if not nonblank(asset.get("set_id")):
                errors.append(f"{label}: master has no set_id")
            if status == "approved":
                p = asset.get("provenance") or {}
                if not nonblank(p.get("approved_by")) or not nonblank(p.get("approved_at")):
                    errors.append(f"{label}: approved master missing approval provenance")
                if asset.get("set_id") != approved_set:
                    errors.append(f"{label}: approved set differs from canon.approved_master_set")
        path = asset.get("path")
        if not nonblank(path):
            errors.append(f"{label}: missing repository-relative path")
            continue
        if path in seen_paths:
            errors.append(f"{label}: duplicate path {path}")
        seen_paths.add(path)
        if Path(path).suffix.lower() not in IMAGE_EXTENSIONS:
            errors.append(f"{label}: unsupported extension")
        try:
            source = asset_path(root, path)
            raw = source.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            native_w, native_h, _ = image_info(raw)
        except (PackError, OSError, ValueError) as exc:
            errors.append(f"{label}: cannot read image: {exc}")
            continue
        expected_digest = asset.get("sha256")
        if not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
            errors.append(f"{label}: invalid sha256 field")
        elif digest != expected_digest:
            errors.append(f"{label}: SHA256 mismatch")
        if type(asset.get("width")) is not int or type(asset.get("height")) is not int:
            errors.append(f"{label}: width/height must be integers")
        elif (native_w, native_h) != (asset["width"], asset["height"]):
            errors.append(f"{label}: native dimensions differ: {native_w}x{native_h}")
        checked.append({"id": asset_id, "path": path, "status": status,
                        "sha256": digest, "width": native_w, "height": native_h})

    actual_images = {p.relative_to(root).as_posix()
                     for p in (root / "assets").rglob("*")
                     if p.is_file() and not p.is_symlink()
                     and p.suffix.lower() in IMAGE_EXTENSIONS}
    unregistered = sorted(actual_images - seen_paths)
    if unregistered:
        warnings.append(f"{len(unregistered)} unregistered image file(s) under assets/")
    if not approved_set and counts["approved"]:
        errors.append("approved assets exist but canon approved_master_set is empty")
    return {"ok": not errors, "expected_count": len(assets),
            "checked_count": len(checked), "by_status": dict(sorted(counts.items())),
            "errors": errors, "warnings": warnings, "unregistered_paths": unregistered,
            "assets": checked}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-unregistered", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = audit(args.root)
    except (PackError, OSError, ValueError, json.JSONDecodeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    if args.fail_unregistered and result["unregistered_paths"]:
        result["errors"].append("unregistered image files are not allowed")
        result["ok"] = False
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    print(f"CHECKED {result['checked_count']}/{result['expected_count']} images | "
          f"status={result['by_status']} | errors={len(result['errors'])} | "
          f"warnings={len(result['warnings'])}")
    for message in result["errors"]:
        print("ERROR:", message, file=sys.stderr)
    for message in result["warnings"]:
        print("WARNING:", message)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
