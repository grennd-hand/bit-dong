#!/usr/bin/env python3
"""Validate and export Bit东 shot inputs; never call a video provider.

Only Python's standard library is required. The manifest's visual classifications
and approval records are declarations; this tool checks files and structure, not
whether a person or a video actually looks correct.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import struct
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


class PackError(ValueError):
    """An input cannot safely be exported as the requested pack."""


def require(condition, message):
    if not condition:
        raise PackError(message)


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"JSON contains duplicate key: {key}")
        result[key] = value
    return result


def reject_nonfinite(value):
    raise PackError(f"JSON contains a nonstandard numeric constant: {value}")


def read_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"),
                          object_pairs_hook=unique_object, parse_constant=reject_nonfinite)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackError(f"Cannot read JSON {path}: {exc}") from exc
    require(isinstance(data, dict), f"JSON root must be an object: {path}")
    return data


def valid_date(value):
    if not nonblank(value):
        return False
    try:
        if len(value) == 10:
            date.fromisoformat(value)
        else:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def valid_https_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.hostname)
    except ValueError:
        return False


def image_info(data):
    """Read native PNG/JPEG dimensions without resampling or third-party code."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        require(len(data) >= 33 and data[12:16] == b"IHDR",
                "Invalid PNG header")
        width, height = struct.unpack(">II", data[16:24])
        require(width > 0 and height > 0, "Invalid PNG dimensions")
        return width, height, ".png"
    require(data.startswith(b"\xff\xd8"), "Only native PNG/JPEG images are supported")
    offset = 2
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
           0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while offset < len(data):
        require(data[offset] == 0xFF, "Invalid JPEG marker")
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        require(offset < len(data), "Truncated JPEG marker")
        marker = data[offset]
        offset += 1
        if marker in {0xD9, 0xDA}:
            break
        if marker in {0x01, 0xD8} or 0xD0 <= marker <= 0xD7:
            continue
        require(offset + 2 <= len(data), "Truncated JPEG segment")
        length = struct.unpack(">H", data[offset:offset + 2])[0]
        require(length >= 2 and offset + length <= len(data),
                "Invalid JPEG segment length")
        if marker in sof:
            require(length >= 8, "Invalid JPEG frame header")
            height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
            require(width > 0 and height > 0, "Invalid JPEG dimensions")
            return width, height, ".jpg"
        offset += length
    raise PackError("JPEG has no readable frame dimensions")


def asset_path(root, relative):
    require(nonblank(relative) and "\\" not in relative,
            "Asset path must be a nonempty repository-relative POSIX path")
    parts = PurePosixPath(relative)
    require(not parts.is_absolute() and ".." not in parts.parts,
            f"Asset path escapes repository: {relative}")
    resolved = (root / relative).resolve()
    require(resolved.is_relative_to(root), f"Asset path escapes repository: {relative}")
    require(resolved.is_file(), f"Asset file is missing: {relative}")
    return resolved


def validate_pack(root, plan, allow_draft=False):
    """Return a checked export description. No files are modified."""
    require(isinstance(plan, dict), "Plan root must be an object")
    root = Path(root).resolve()
    canon = read_json(root / "references/character-canon.json")
    manifest = read_json(root / "assets/asset-manifest.json")
    for label, document in (("plan", plan), ("canon", canon), ("manifest", manifest)):
        require(document.get("schema_version") == "1.0", f"Unsupported {label} schema_version")
    require(nonblank(canon.get("character_id")), "Canon character_id is missing")
    require(plan.get("character_id") == canon["character_id"] == manifest.get("character_id"),
            "character_id differs between plan, canon and manifest")
    require(nonblank(canon.get("design_version")) and
            plan.get("design_version") == canon["design_version"],
            "Plan design_version does not match canon")
    require(nonblank(plan.get("project")), "Plan project is required")
    require(isinstance(plan.get("aspect_ratio"), str) and
            re.fullmatch(r"[1-9]\d*:[1-9]\d*", plan["aspect_ratio"]),
            "aspect_ratio must be a positive ratio such as 9:16")
    require(plan.get("negative_prompt_supported") is None or
            isinstance(plan["negative_prompt_supported"], bool),
            "negative_prompt_supported must be true, false or null")

    entries = manifest.get("assets")
    require(isinstance(entries, list) and entries, "Manifest assets must be a nonempty list")
    registry = {}
    for item in entries:
        require(isinstance(item, dict) and nonblank(item.get("id")), "Asset id is missing")
        require(item["id"] not in registry, f"Duplicate asset id: {item['id']}")
        registry[item["id"]] = item

    warnings = []
    incomplete = []
    for key in ("provider", "provider_surface", "model"):
        value = plan.get(key)
        if not nonblank(value) or value.strip().lower() in {"generic", "unspecified", "unknown", "unverified"}:
            incomplete.append(key)
    if not valid_date(plan.get("capabilities_verified_at")):
        incomplete.append("capabilities_verified_at")
    sources = plan.get("official_sources")
    if not (isinstance(sources, list) and sources and all(valid_https_url(url) for url in sources)):
        incomplete.append("official_sources")
    if incomplete:
        require(allow_draft, "Provider capability record is incomplete: " + ", ".join(incomplete) +
                ". Use --allow-draft for a clearly marked draft.")
        warnings.append("Provider capability record is incomplete: " + ", ".join(incomplete))

    shots = plan.get("shots")
    require(isinstance(shots, list) and shots, "Plan shots must be a nonempty list")
    shot_ids, selected, checked_shots, selected_sets = set(), {}, [], set()
    previous_state = None
    has_text_only = False
    for number, shot in enumerate(shots, 1):
        require(isinstance(shot, dict) and nonblank(shot.get("id")), f"Shot {number} needs an id")
        shot_id = shot["id"]
        require(shot_id not in shot_ids, f"Duplicate shot id: {shot_id}")
        shot_ids.add(shot_id)
        duration = shot.get("duration_seconds")
        require(isinstance(duration, (int, float)) and not isinstance(duration, bool) and
                math.isfinite(duration) and duration > 0, f"{shot_id}: duration_seconds must be positive")
        for key in ("prompt_zh", "prompt_en"):
            require(nonblank(shot.get(key)), f"{shot_id}: {key} is required")
        for key in ("continuity_in", "continuity_out"):
            require(isinstance(shot.get(key), dict), f"{shot_id}: {key} must be an object")
        require(shot.get("explicit_cut", False) in (True, False) and
                isinstance(shot.get("explicit_cut", False), bool), f"{shot_id}: explicit_cut must be boolean")
        if shot.get("explicit_cut", False):
            require(nonblank(shot.get("cut_reason")),
                    f"{shot_id}: explicit_cut=true requires a nonempty cut_reason")
        if previous_state is not None and not shot.get("explicit_cut", False):
            for key in previous_state.keys() & shot["continuity_in"].keys():
                require(previous_state[key] == shot["continuity_in"][key],
                        f"{shot_id}: continuity conflict for {key}; explain an intentional change with explicit_cut=true")
        previous_state = shot["continuity_out"]
        for key in ("negative_prompt", "dialogue_zh"):
            require(shot.get(key) is None or isinstance(shot.get(key), str),
                    f"{shot_id}: {key} must be a string or null")
        if nonblank(shot.get("negative_prompt")):
            require(plan.get("negative_prompt_supported") is True,
                    f"{shot_id}: nonempty negative_prompt requires negative_prompt_supported=true for the selected entry; "
                    "otherwise remove it from the model prompt and retain the requirements as QA checks")

        refs = shot.get("reference_ids", [])
        require(isinstance(refs, list) and all(nonblank(ref) for ref in refs),
                f"{shot_id}: reference_ids must be a list of asset ids")
        require(len(refs) == len(set(refs)), f"{shot_id}: duplicate reference id")
        first, last, mode = shot.get("first_frame_id"), shot.get("last_frame_id"), shot.get("mode")
        require(first is None or nonblank(first), f"{shot_id}: invalid first_frame_id")
        require(last is None or nonblank(last), f"{shot_id}: invalid last_frame_id")
        if mode == "subject_reference":
            require(refs and first is None and last is None,
                    f"{shot_id}: subject_reference requires only reference_ids")
            inputs = [(ref, "character_identity") for ref in refs]
            expected_role = "character_master"
        elif mode == "first_frame":
            require(not refs and first is not None and last is None,
                    f"{shot_id}: first_frame requires only first_frame_id")
            inputs, expected_role = [(first, "first_frame")], "shot_frame"
        elif mode == "first_last":
            require(not refs and first is not None and last is not None,
                    f"{shot_id}: first_last requires first_frame_id and last_frame_id only")
            inputs, expected_role = [(first, "first_frame"), (last, "last_frame")], "shot_frame"
        elif mode == "text_only":
            require(not refs and first is None and last is None, f"{shot_id}: text_only cannot contain image inputs")
            require(allow_draft, f"{shot_id}: text_only has no visual identity constraint; use --allow-draft")
            inputs, expected_role, has_text_only = [], None, True
            warnings.append(f"{shot_id}: text-only draft has no visual identity constraint")
        else:
            raise PackError(f"{shot_id}: unknown input mode {mode!r}")

        upload_map, shot_sets = [], set()
        for order, (asset_id, purpose) in enumerate(inputs, 1):
            require(asset_id in registry, f"{shot_id}: unknown asset id {asset_id}")
            asset = registry[asset_id]
            require(asset.get("status") in {"candidate", "approved"},
                    f"{asset_id}: source/archived material cannot be submitted as a video input")
            require(asset.get("role") == expected_role,
                    f"{asset_id}: {mode} requires {expected_role}, got {asset.get('role')!r}")
            require(asset.get("single_subject") is True,
                    f"{asset_id}: input must be a declared single-subject image, not a sheet")
            require(nonblank(asset.get("set_id")), f"{asset_id}: set_id is missing")
            shot_sets.add(asset["set_id"])
            selected_sets.add(asset["set_id"])
            provenance = asset.get("provenance")
            require(isinstance(provenance, dict), f"{asset_id}: provenance is required")
            if asset["status"] == "approved":
                require(nonblank(provenance.get("approved_by")) and valid_date(provenance.get("approved_at")),
                        f"{asset_id}: approved asset lacks approved_by/approved_at evidence")
            else:
                require(allow_draft, f"{asset_id}: candidate is not approved; use --allow-draft")
            if not allow_draft:
                require(asset["set_id"] == canon.get("approved_master_set"),
                        f"{asset_id}: set_id is not canon.approved_master_set")
            if asset_id not in selected:
                path = asset_path(root, asset.get("path"))
                data = path.read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                require(isinstance(asset.get("sha256"), str) and
                        re.fullmatch(r"[0-9a-f]{64}", asset["sha256"]) and digest == asset["sha256"],
                        f"{asset_id}: SHA256 mismatch or invalid manifest hash")
                width, height, extension = image_info(data)
                require(type(asset.get("width")) is int and type(asset.get("height")) is int and
                        (width, height) == (asset["width"], asset["height"]),
                        f"{asset_id}: native dimensions differ from manifest")
                destination = f"assets/{len(selected) + 1:02d}-{digest[:12]}{extension}"
                selected[asset_id] = {"manifest": asset, "source_path": path,
                                      "file": destination, "sha256": digest,
                                      "width": width, "height": height}
            upload_map.append({"upload_index": order, "asset_id": asset_id,
                               "purpose": purpose, "file": selected[asset_id]["file"],
                               "platform_reference_name": None})
        require(len(shot_sets) <= 1, f"{shot_id}: mixed character asset sets are not allowed")
        checked_shots.append({"shot": shot, "directory": f"shots/shot-{number:03d}",
                              "upload_map": upload_map})
    require(len(selected_sets) <= 1, "Shots mix different character asset sets in one pack")
    require(selected or has_text_only, "No usable visual assets were selected")
    if allow_draft:
        warnings.append("DRAFT: candidate art and/or provider settings may still require review")
    warnings.extend([
        "No provider API was called; provider capability records are supplied declarations, not live verification",
        "Single-subject classification, character likeness and approval authorship are not visually or externally verified by this tool",
    ])
    return {"plan": plan, "assets": selected, "shots": checked_shots,
            "status": "draft" if allow_draft else "approved_inputs_recorded_capabilities",
            "warnings": warnings}


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def export_pack(checked, output):
    """Write a new directory atomically after all validation has succeeded."""
    output = Path(output).absolute()
    require(not output.is_symlink(), "Output directory cannot be a symlink")
    require(not output.exists() or (output.is_dir() and not any(output.iterdir())),
            "Output directory already exists and is not empty; choose a new directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".bitdong-pack-", dir=output.parent))
    try:
        exported_assets = []
        for asset_id, asset in checked["assets"].items():
            destination = temporary / asset["file"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(asset["source_path"], destination)
            require(hashlib.sha256(destination.read_bytes()).hexdigest() == asset["sha256"],
                    f"{asset_id}: source changed after validation; export stopped")
            exported_assets.append({"asset_id": asset_id, "file": asset["file"],
                                    "sha256": asset["sha256"], "width": asset["width"], "height": asset["height"],
                                    "status": asset["manifest"]["status"], "set_id": asset["manifest"]["set_id"],
                                    "role": asset["manifest"]["role"],
                                    "source_repository_path": asset["manifest"]["path"],
                                    "provenance": asset["manifest"]["provenance"]})
        for record in checked["shots"]:
            shot, directory = record["shot"], temporary / record["directory"]
            directory.mkdir(parents=True)
            (directory / "prompt.zh.txt").write_text(shot["prompt_zh"].strip() + "\n", encoding="utf-8")
            (directory / "prompt.en.txt").write_text(shot["prompt_en"].strip() + "\n", encoding="utf-8")
            if nonblank(shot.get("negative_prompt")):
                (directory / "negative-prompt.txt").write_text(shot["negative_prompt"].strip() + "\n", encoding="utf-8")
            write_json(directory / "upload-map.json", {"shot_id": shot["id"], "mode": shot["mode"],
                       "paths_relative_to": "pack_root", "inputs": record["upload_map"]})
            write_json(directory / "shot.json", shot)
        packet = {"schema_version": "1.0", "status": checked["status"],
                  "generation_executed": False, "capabilities_verified_by_tool": False,
                  "visual_consistency_verified_by_tool": False, "plan": checked["plan"],
                  "assets": exported_assets, "warnings": checked["warnings"]}
        write_json(temporary / "pack.json", packet)
        readme = "# BIT东视频输入包\n\n状态：`" + checked["status"] + "`。\n\n"
        readme += "这是素材与提示词交付包，不是任何厂商的 API 请求，也没有生成视频。\n\n"
        readme += "按 `shots/shot-NNN/upload-map.json` 的顺序上传素材；其中 file 路径相对于本包根目录。"
        readme += "`platform_reference_name: null` 表示尚未上传绑定。选用对应中英文提示词；负面提示单独保留，只有当前入口确认支持时才使用。\n\n"
        readme += "素材保持原始字节，没有裁切、放大或增加真实细节。尺寸与哈希已检查；视觉一致性仍需看图和实际视频验收。\n\n"
        readme += "## 检查与待办\n\n" + "\n".join("- " + warning for warning in checked["warnings"]) + "\n"
        (temporary / "README.md").write_text(readme, encoding="utf-8")
        if output.exists():
            output.rmdir()  # Only the empty directory checked above may be replaced.
        temporary.rename(output)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True, help="Shot plan JSON")
    parser.add_argument("--out", type=Path, help="New/empty output directory")
    parser.add_argument("--allow-draft", action="store_true", help="Export unapproved candidate inputs as DRAFT")
    parser.add_argument("--validate-only", action="store_true", help="Validate without writing a pack")
    args = parser.parse_args(argv)
    if not args.validate_only and args.out is None:
        parser.error("--out is required unless --validate-only is used")
    try:
        checked = validate_pack(Path(__file__).resolve().parents[1], read_json(args.plan), args.allow_draft)
        if args.validate_only:
            print(f"VALID: {checked['status']}; {len(checked['shots'])} shots; {len(checked['assets'])} unique images")
        else:
            destination = export_pack(checked, args.out)
            print(f"EXPORTED: {checked['status']}; {len(checked['shots'])} shots; {len(checked['assets'])} unique images; {destination}")
        for warning in checked["warnings"]:
            print("NOTE: " + warning)
        return 0
    except (PackError, OSError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
