"""Prevent broken or unregistered images entering a BIT东 release."""
import hashlib
import importlib.util
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_assets import audit


def png(width=3, height=4):
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    row = b"\x00" + b"\xff\xff\xff" * width
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(row * height)) +
            chunk(b"IEND", b""))


class InventoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "references").mkdir()
        (self.root / "assets").mkdir()
        self.bytes = png()
        (self.root / "assets" / "front.png").write_bytes(self.bytes)
        self.item = {"id": "front", "path": "assets/front.png",
                     "role": "character_master", "status": "candidate",
                     "set_id": "test-candidates", "width": 3, "height": 4,
                     "sha256": hashlib.sha256(self.bytes).hexdigest(),
                     "provenance": {"kind": "generated"}}
        self.canon = {"schema_version": "1.0", "character_id": "bitdong",
                      "approved_master_set": None}
        self.manifest = {"schema_version": "1.0", "character_id": "bitdong",
                         "assets": [self.item]}
        self.save()

    def save(self):
        (self.root / "references" / "character-canon.json").write_text(json.dumps(self.canon))
        (self.root / "assets" / "asset-manifest.json").write_text(json.dumps(self.manifest))

    def test_valid_inventory(self):
        out = audit(self.root)
        self.assertTrue(out["ok"])
        self.assertEqual(out["checked_count"], 1)
        self.assertFalse(out["unregistered_paths"])

    def test_modified_file_detected(self):
        (self.root / "assets/front.png").write_bytes(png(5, 5))
        self.assertIn("SHA256 mismatch", "\n".join(audit(self.root)["errors"]))
        self.assertIn("native dimensions differ", "\n".join(audit(self.root)["errors"]))

    def test_missing_file_detected(self):
        (self.root / "assets/front.png").unlink()
        self.assertFalse(audit(self.root)["ok"])

    def test_duplicate_id_and_path_detected(self):
        self.manifest["assets"].append(dict(self.item))
        self.save()
        self.assertIn("duplicate id", "\n".join(audit(self.root)["errors"]))
        self.assertIn("duplicate path", "\n".join(audit(self.root)["errors"]))

    def test_unregistered_file_reported(self):
        (self.root / "assets/another.png").write_bytes(self.bytes)
        self.assertEqual(audit(self.root)["unregistered_paths"], ["assets/another.png"])

    def test_approved_asset_without_evidence_fails(self):
        self.item["status"] = "approved"
        self.save()
        self.assertFalse(audit(self.root)["ok"])

    def test_source_path_escape_fails(self):
        self.item["path"] = "../outside.png"
        self.save()
        self.assertFalse(audit(self.root)["ok"])


if __name__ == "__main__":
    unittest.main()
