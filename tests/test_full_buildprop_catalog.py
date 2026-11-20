"""Full firmware property catalog: read-only runtime, maintainer-side ingest."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("refresh_catalog", ROOT / "scripts" / "refresh_catalog.py")
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)

FP = "google/example/example:14/UP1A.231005.007/1234567:user/release-keys"
FULL = "# extracted stock firmware\nro.build.fingerprint=" + FP + "\nro.product.model=Example\n"

class CatalogBuildPropTests(unittest.TestCase):
    def test_unmodified_file_is_embedded(self):
        c = refresh.Catalog()
        self.assertTrue(c.add(source="ChkDumps", label="Example", manufacturer="Google",
                              model="Example", fingerprint=FP, build_prop=FULL))
        record = next(iter(c.records.values()))
        self.assertEqual(record["builds"]["14"][0]["buildProp"], FULL)

    def test_missing_file_is_not_synthesized(self):
        c = refresh.Catalog()
        c.add(source="Example", label="Example", manufacturer="Google",
              model="Example", fingerprint=FP)
        self.assertNotIn("buildProp", next(iter(c.records.values()))["builds"]["14"][0])

    def test_rejects_mismatched_file(self):
        c = refresh.Catalog()
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            c.add(source="Bad", label="Example", manufacturer="Google",
                  model="Example", fingerprint=FP,
                  build_prop="ro.build.fingerprint=other\n")

    def test_duplicate_records_upgrade_to_full_file(self):
        c = refresh.Catalog()
        c.add(source="Community", label="Example", manufacturer="Google",
              model="Example", fingerprint=FP)
        c.add(source="ChkDumps", label="Example", manufacturer="Google",
              model="Example", fingerprint=FP, build_prop=FULL)
        record = next(iter(c.records.values()))
        self.assertEqual(record["builds"]["14"][0]["buildProp"], FULL)

    def test_runtime_is_read_only(self):
        html = (ROOT / "webroot" / "index.html").read_text()
        self.assertIn('id="catalogBuildProp"', html)
        self.assertIn('readonly spellcheck="false"', html)
        self.assertNotIn('id="catalogImport"', html)

if __name__ == "__main__":
    unittest.main()
