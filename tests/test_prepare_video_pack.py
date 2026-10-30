"""Exercise input integrity and portable handoff, without a provider or network."""

import copy
import hashlib
import importlib.util
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_video_pack.py"
SPEC = importlib.util.spec_from_file_location("prepare_video_pack", SCRIPT)
pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pack)


def png(width=2, height=3):
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    pixels = b"".join(b"\x00" + b"\xff\xff\xff" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


class PackTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        (self.root / "references").mkdir(parents=True)
        (self.root / "assets").mkdir()
        self.data = png()
        (self.root / "assets/front.png").write_bytes(self.data)
        self.canon = {"schema_version": "1.0", "character_id": "bitdong",
                      "design_version": "1.0-inherited", "approved_master_set": None}
        self.asset = {"id": "front", "path": "assets/front.png", "role": "character_master",
                      "status": "candidate", "set_id": "candidate-v2", "single_subject": True,
                      "sha256": hashlib.sha256(self.data).hexdigest(), "width": 2, "height": 3,
                      "provenance": {"kind": "generated"}}
        self.manifest = {"schema_version": "1.0", "character_id": "bitdong", "assets": [self.asset]}
        self.plan = {"schema_version": "1.0", "project": "Bit东中文示例", "character_id": "bitdong",
                     "design_version": "1.0-inherited", "provider": "generic",
                     "provider_surface": "unspecified", "model": None,
                     "capabilities_verified_at": None, "official_sources": [], "aspect_ratio": "9:16",
                     "shots": [{"id": "s01", "duration_seconds": 5, "mode": "subject_reference",
                                "reference_ids": ["front"], "first_frame_id": None, "last_frame_id": None,
                                "prompt_zh": "Bit东微笑并挥手。", "prompt_en": "The character smiles and waves.",
                                "negative_prompt": None, "dialogue_zh": None,
                                "continuity_in": {"hand": "lowered"}, "continuity_out": {"hand": "raised"}}]}
        self.save()

    def save(self):
        pack.write_json(self.root / "references/character-canon.json", self.canon)
        pack.write_json(self.root / "assets/asset-manifest.json", self.manifest)

    def checked(self, draft=True):
        self.save()
        return pack.validate_pack(self.root, self.plan, allow_draft=draft)

    def complete_provider(self):
        self.plan.update(provider="example-provider", provider_surface="official_api", model="documented-model",
                         capabilities_verified_at="2026-10-30", official_sources=["https://example.com/docs"])

    def test_draft_export_preserves_utf8_and_original_bytes(self):
        checked = self.checked()
        destination = Path(self.temporary.name) / "export"
        pack.export_pack(checked, destination)
        result = pack.read_json(destination / "pack.json")
        self.assertEqual(result["status"], "draft")
        self.assertIsNone(result["plan"]["model"])
        self.assertFalse(result["generation_executed"])
        self.assertFalse(result["capabilities_verified_by_tool"])
        self.assertEqual((destination / result["assets"][0]["file"]).read_bytes(), self.data)
        self.assertEqual((destination / "shots/shot-001/prompt.zh.txt").read_text(), "Bit东微笑并挥手。\n")
        self.assertEqual((destination / "shots/shot-001/prompt.en.txt").read_text(), "The character smiles and waves.\n")
        mapping = pack.read_json(destination / "shots/shot-001/upload-map.json")
        self.assertEqual(mapping["inputs"][0]["upload_index"], 1)
        self.assertIsNone(mapping["inputs"][0]["platform_reference_name"])

    def test_strict_mode_rejects_missing_capabilities(self):
        with self.assertRaisesRegex(pack.PackError, "capability record"):
            self.checked(draft=False)

    def test_strict_mode_rejects_candidate(self):
        self.complete_provider()
        with self.assertRaisesRegex(pack.PackError, "candidate is not approved"):
            self.checked(draft=False)

    def test_strict_mode_requires_approval_and_canon_set(self):
        self.complete_provider()
        self.asset["status"] = "approved"
        with self.assertRaisesRegex(pack.PackError, "approved_by/approved_at"):
            self.checked(draft=False)
        self.asset["provenance"].update(approved_by="owner-record", approved_at="2026-10-30")
        with self.assertRaisesRegex(pack.PackError, "approved_master_set"):
            self.checked(draft=False)
        self.canon["approved_master_set"] = "candidate-v2"
        self.assertEqual(self.checked(draft=False)["status"], "approved_inputs_recorded_capabilities")

    def test_archives_and_design_sources_never_bypass_with_draft(self):
        for status, role in (("archived", "character_master"), ("source", "design_source"),
                             ("candidate", "identity_source"), ("candidate", "performance_reference")):
            with self.subTest(status=status, role=role):
                self.asset.update(status=status, role=role)
                with self.assertRaises(pack.PackError):
                    self.checked()

    def test_contact_sheet_is_rejected(self):
        self.asset["single_subject"] = False
        with self.assertRaisesRegex(pack.PackError, "single-subject"):
            self.checked()

    def test_first_frame_mode_is_not_reference_mode(self):
        shot = self.plan["shots"][0]
        shot.update(mode="first_frame", first_frame_id="front")
        with self.assertRaisesRegex(pack.PackError, "only first_frame_id"):
            self.checked()
        shot["reference_ids"] = []
        with self.assertRaisesRegex(pack.PackError, "requires shot_frame"):
            self.checked()
        self.asset["role"] = "shot_frame"
        self.assertEqual(self.checked()["shots"][0]["upload_map"][0]["purpose"], "first_frame")

    def test_first_last_requires_two_frames(self):
        shot = self.plan["shots"][0]
        shot.update(mode="first_last", reference_ids=[], first_frame_id="front", last_frame_id=None)
        with self.assertRaisesRegex(pack.PackError, "requires first_frame_id and last_frame_id"):
            self.checked()
        second = copy.deepcopy(self.asset)
        second.update(id="last", role="shot_frame")
        self.asset["role"] = "shot_frame"
        self.manifest["assets"].append(second)
        shot["last_frame_id"] = "last"
        self.assertEqual(len(self.checked()["shots"][0]["upload_map"]), 2)

    def test_path_escape_and_symlink_escape(self):
        (self.root.parent / "outside.png").write_bytes(self.data)
        self.asset["path"] = "../outside.png"
        with self.assertRaisesRegex(pack.PackError, "escapes repository"):
            self.checked()
        (self.root / "assets/link.png").symlink_to(self.root.parent / "outside.png")
        self.asset["path"] = "assets/link.png"
        with self.assertRaisesRegex(pack.PackError, "escapes repository"):
            self.checked()

    def test_tampered_hash_and_native_size(self):
        self.asset["sha256"] = "0" * 64
        with self.assertRaisesRegex(pack.PackError, "SHA256"):
            self.checked()
        self.asset["sha256"] = hashlib.sha256(self.data).hexdigest()
        self.asset["width"] = 2000
        with self.assertRaisesRegex(pack.PackError, "native dimensions"):
            self.checked()

    def test_duplicate_and_unknown_ids(self):
        self.manifest["assets"].append(copy.deepcopy(self.asset))
        with self.assertRaisesRegex(pack.PackError, "Duplicate asset id"):
            self.checked()
        self.manifest["assets"].pop()
        self.plan["shots"][0]["reference_ids"] = ["unknown"]
        with self.assertRaisesRegex(pack.PackError, "unknown asset id"):
            self.checked()
        self.plan["shots"][0]["reference_ids"] = ["front", "front"]
        with self.assertRaisesRegex(pack.PackError, "duplicate reference id"):
            self.checked()

    def test_continuity_conflict_needs_explicit_cut(self):
        second = copy.deepcopy(self.plan["shots"][0])
        second["id"] = "s02"
        self.plan["shots"].append(second)
        with self.assertRaisesRegex(pack.PackError, "continuity conflict for hand"):
            self.checked()
        second["explicit_cut"] = True
        with self.assertRaisesRegex(pack.PackError, "nonempty cut_reason"):
            self.checked()
        second["cut_reason"] = "Cut to a later moment after the hand is lowered."
        self.assertEqual(len(self.checked()["shots"]), 2)

    def test_explicit_cut_always_requires_a_reason(self):
        shot = self.plan["shots"][0]
        shot["explicit_cut"] = True
        for reason in (None, "", "  ", True):
            with self.subTest(reason=reason):
                shot["cut_reason"] = reason
                with self.assertRaisesRegex(pack.PackError, "nonempty cut_reason"):
                    self.checked()
        shot["cut_reason"] = "Start after the previous scene's action."
        self.checked()

    def test_negative_prompt_requires_explicit_support(self):
        self.plan["shots"][0]["negative_prompt"] = "unwanted extra people"
        for support in (None, False):
            with self.subTest(support=support):
                self.plan["negative_prompt_supported"] = support
                with self.assertRaisesRegex(pack.PackError, "requires negative_prompt_supported=true"):
                    self.checked()
        self.plan["negative_prompt_supported"] = True
        checked = self.checked()
        destination = Path(self.temporary.name) / "with-negative"
        pack.export_pack(checked, destination)
        self.assertEqual((destination / "shots/shot-001/negative-prompt.txt").read_text(),
                         "unwanted extra people\n")
        self.plan["negative_prompt_supported"] = False
        self.plan["shots"][0]["negative_prompt"] = "   "
        destination = Path(self.temporary.name) / "without-negative"
        pack.export_pack(self.checked(), destination)
        self.assertFalse((destination / "shots/shot-001/negative-prompt.txt").exists())

    def test_wrong_json_types_have_clear_errors(self):
        for value in (None, [], True, "not an object"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(pack.PackError, "Plan root must be an object"):
                    pack.validate_pack(self.root, value, allow_draft=True)
        cases = (("schema_version", True, "schema_version"),
                 ("negative_prompt_supported", "true", "true, false or null"),
                 ("negative_prompt_supported", 1, "true, false or null"),
                 ("aspect_ratio", True, "aspect_ratio"),
                 ("shots", "one shot", "nonempty list"))
        for key, value, error in cases:
            with self.subTest(key=key, value=value):
                plan = copy.deepcopy(self.plan)
                plan[key] = value
                with self.assertRaisesRegex(pack.PackError, error):
                    pack.validate_pack(self.root, plan, allow_draft=True)
        for key, value, error in (("explicit_cut", "false", "must be boolean"),
                                   ("duration_seconds", True, "must be positive"),
                                   ("reference_ids", "front", "list of asset ids")):
            with self.subTest(key=key):
                plan = copy.deepcopy(self.plan)
                plan["shots"][0][key] = value
                with self.assertRaisesRegex(pack.PackError, error):
                    pack.validate_pack(self.root, plan, allow_draft=True)

    def test_asset_sets_must_not_change_between_shots(self):
        second = copy.deepcopy(self.asset)
        second.update(id="other", set_id="other-set")
        self.manifest["assets"].append(second)
        self.plan["shots"][0]["reference_ids"].append("other")
        with self.assertRaisesRegex(pack.PackError, "mixed character asset sets"):
            self.checked()

    def test_text_only_is_honestly_marked_draft(self):
        self.plan["shots"][0].update(mode="text_only", reference_ids=[])
        checked = self.checked()
        self.assertEqual(checked["assets"], {})
        self.assertTrue(any("no visual identity constraint" in w for w in checked["warnings"]))
        self.complete_provider()
        with self.assertRaisesRegex(pack.PackError, "text_only has no visual identity"):
            self.checked(draft=False)

    def test_output_never_overwrites_and_source_change_is_detected(self):
        checked = self.checked()
        destination = Path(self.temporary.name) / "export"
        destination.mkdir()
        (destination / "keep.txt").write_text("keep")
        with self.assertRaisesRegex(pack.PackError, "not empty"):
            pack.export_pack(checked, destination)
        self.assertEqual((destination / "keep.txt").read_text(), "keep")
        (self.root / "assets/front.png").write_bytes(png(3, 4))
        with self.assertRaisesRegex(pack.PackError, "source changed"):
            pack.export_pack(checked, Path(self.temporary.name) / "changed")
        self.assertFalse((Path(self.temporary.name) / "changed").exists())

    def test_ids_are_not_output_paths(self):
        self.asset["id"] = "../../unsafe"
        self.plan["shots"][0].update(id="../../other", reference_ids=["../../unsafe"])
        checked = self.checked()
        self.assertEqual(checked["shots"][0]["directory"], "shots/shot-001")
        self.assertNotIn("unsafe", checked["assets"]["../../unsafe"]["file"])

    def test_duplicate_json_keys_fail_closed(self):
        path = self.root / "duplicate.json"
        path.write_text('{"status":"approved","status":"candidate"}')
        with self.assertRaisesRegex(pack.PackError, "duplicate key"):
            pack.read_json(path)

    def test_nonstandard_json_numbers_and_malformed_urls(self):
        path = self.root / "invalid.json"
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                path.write_text('{"value":' + value + '}')
                with self.assertRaisesRegex(pack.PackError, "nonstandard numeric"):
                    pack.read_json(path)
        self.complete_provider()
        self.plan["official_sources"] = ["https://["]
        with self.assertRaisesRegex(pack.PackError, "official_sources"):
            self.checked(draft=False)
        self.assertTrue(any("official_sources" in warning for warning in self.checked()["warnings"]))

    def test_minimal_jpeg_header_and_malformed_image(self):
        jpeg = (b"\xff\xd8\xff\xc0" + struct.pack(">H", 11) +
                b"\x08" + struct.pack(">HH", 3, 2) + b"\x01\x01\x11\x00\xff\xd9")
        self.assertEqual(pack.image_info(jpeg), (2, 3, ".jpg"))
        with self.assertRaises(pack.PackError):
            pack.image_info(b"\xff\xd8\xff\xc0\x00")


if __name__ == "__main__":
    unittest.main()
