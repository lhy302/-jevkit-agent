"""Portable rollback regressions; only Python's standard library is required."""
import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


spec = importlib.util.spec_from_file_location("jevkit", Path(__file__).with_name("jevkit-agent.py"))
jev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jev)


def block(bid, value, newline="\n", prefix="#"):
    return ("{0} @jev-block:{1}:begin\nvalue = {2}\n{0} @jev-block:{1}:end\n"
            .format(prefix, bid, value).replace("\n", newline).encode("utf-8"))


class RollbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = jev.ThreeFileManager.resolve_paths(str(self.root / "demo"))

    def checkpoint(self, value, status="confirmed", paths=None, ids=("demo_001",)):
        paths = paths or self.paths
        for key in ("high_dsl", "spec_dsl", "code_file"):
            Path(paths[key]).write_bytes(b"\xef\xbb\xbf" + b"".join(block(bid, value, "\r\n") for bid in ids))
        entries = [jev.Block(bid, "value = %s" % value, 1, 3) for bid in ids]
        jev.ThreeFileManager.update_blocks_index(paths, entries, status=status)
        return {key: Path(paths[key]).read_bytes() for key in ("high_dsl", "spec_dsl", "code_file")}

    def index(self):
        return json.loads(Path(self.paths["index_file"]).read_text(encoding="utf-8"))

    def test_restores_actual_three_files_and_index(self):
        expected = self.checkpoint(1)
        old_entries = self.index()["blocks"]
        self.checkpoint(2)
        result = jev.jev_rollback(str(self.root / "demo"))
        self.assertEqual(result["status"], "success")
        for key, raw in expected.items():
            self.assertEqual(Path(self.paths[key]).read_bytes(), raw)
        self.assertEqual(self.index()["blocks"], old_entries)
        self.assertEqual(len(self.index()["history"]), 1)

    def test_repeated_rollback_walks_back_history(self):
        expected = self.checkpoint(1)
        self.checkpoint(2)
        self.checkpoint(3)
        jev.jev_rollback(str(self.root / "demo"))
        jev.jev_rollback(str(self.root / "demo"))
        self.assertEqual(Path(self.paths["code_file"]).read_bytes(), expected["code_file"])
        self.assertEqual(jev.jev_rollback(str(self.root / "demo"))["status"], "noop")

    def test_draft_restores_latest_confirmed_snapshot(self):
        expected = self.checkpoint(1)
        self.checkpoint(2, status="translated")
        jev.jev_rollback(str(self.root / "demo"))
        self.assertEqual(Path(self.paths["code_file"]).read_bytes(), expected["code_file"])

    def test_no_confirmed_snapshot_is_noop(self):
        current = self.checkpoint(1, status="draft")
        self.assertEqual(jev.jev_rollback(str(self.root / "demo"))["status"], "noop")
        self.assertEqual(Path(self.paths["code_file"]).read_bytes(), current["code_file"])

    def test_legacy_metadata_history_is_rejected_without_mutation(self):
        self.checkpoint(1)
        data = self.index()
        data["history"] = [{"blocks": data["blocks"], "status": "confirmed"}] * 2
        Path(self.paths["index_file"]).write_text(json.dumps(data), encoding="utf-8")
        original = Path(self.paths["index_file"]).read_bytes()
        with self.assertRaisesRegex(jev.JevBlockError, "旧历史"):
            jev.jev_rollback(str(self.root / "demo"))
        self.assertEqual(Path(self.paths["index_file"]).read_bytes(), original)

    def test_module_rollback_does_not_touch_other_module(self):
        expected = self.checkpoint(1)
        other = jev.ThreeFileManager.resolve_paths(str(self.root / "other"))
        other_files = self.checkpoint(9, paths=other, ids=("other_001",))
        other_history = [s for s in self.index()["history"] if s["module"] == "other"]
        self.checkpoint(2)
        jev.jev_rollback(str(self.root / "demo"))
        self.assertEqual(Path(self.paths["code_file"]).read_bytes(), expected["code_file"])
        for key, raw in other_files.items():
            self.assertEqual(Path(other[key]).read_bytes(), raw)
        self.assertIn("other_001", [b["block_id"] for b in self.index()["blocks"]])
        self.assertEqual([s for s in self.index()["history"] if s["module"] == "other"], other_history)

    def test_restores_all_languages_and_removes_new_projections(self):
        expected = self.checkpoint(1)
        c_paths = jev.ThreeFileManager.resolve_paths(str(self.root / "demo"), "c")
        self.checkpoint(2, paths=c_paths)
        jev.jev_rollback(str(self.root / "demo"))
        self.assertEqual(Path(self.paths["high_dsl"]).read_bytes(), expected["high_dsl"])
        self.assertFalse(Path(c_paths["spec_dsl"]).exists())
        self.assertFalse(Path(c_paths["code_file"]).exists())

    def test_recreates_deleted_file(self):
        expected = self.checkpoint(1)
        self.checkpoint(2)
        Path(self.paths["code_file"]).unlink()
        jev.jev_rollback(str(self.root / "demo"))
        self.assertEqual(Path(self.paths["code_file"]).read_bytes(), expected["code_file"])

    def test_block_rollback_preserves_other_blocks_and_bom(self):
        self.checkpoint(1, ids=("demo_001", "demo_002"))
        self.checkpoint(2, ids=("demo_001", "demo_002"))
        expected = b"\xef\xbb\xbf" + block("demo_001", 1, "\r\n") + block("demo_002", 2, "\r\n")
        jev.jev_rollback(str(self.root / "demo"), block_id="demo_001")
        for key in ("high_dsl", "spec_dsl", "code_file"):
            self.assertEqual(Path(self.paths[key]).read_bytes(), expected)
        entries = {b["block_id"]: b for b in self.index()["blocks"]}
        self.assertNotEqual(entries["demo_001"]["version_vector"], entries["demo_002"]["version_vector"])

    def test_unknown_block_is_rejected_without_writes(self):
        self.checkpoint(1)
        current = self.checkpoint(2)
        with self.assertRaises(jev.JevBlockError):
            jev.jev_rollback(str(self.root / "demo"), block_id="missing")
        self.assertEqual(Path(self.paths["code_file"]).read_bytes(), current["code_file"])

    def test_invalid_snapshot_content_is_rejected_before_writes(self):
        self.checkpoint(1)
        current = self.checkpoint(2)
        data = self.index()
        data["history"][0]["files"]["demo.py"] = "invalid-base64!"
        Path(self.paths["index_file"]).write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            jev.jev_rollback(str(self.root / "demo"))
        self.assertEqual(Path(self.paths["code_file"]).read_bytes(), current["code_file"])

    def test_snapshot_cannot_escape_module_directory(self):
        self.checkpoint(1)
        current = self.checkpoint(2)
        data = self.index()
        data["history"][0]["files"]["../outside"] = base64.b64encode(b"bad").decode()
        Path(self.paths["index_file"]).write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(jev.JevBlockError):
            jev.jev_rollback(str(self.root / "demo"))
        self.assertEqual(Path(self.paths["code_file"]).read_bytes(), current["code_file"])

    def test_replace_failure_restores_files_and_index(self):
        self.checkpoint(1)
        current = self.checkpoint(2)
        index_before = Path(self.paths["index_file"]).read_bytes()
        replace = jev.os.replace
        calls = []

        def fail_once(src, dst):
            calls.append(dst)
            if len(calls) == 3:
                raise OSError("injected replacement failure")
            return replace(src, dst)

        with mock.patch.object(jev.os, "replace", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "injected"):
                jev.jev_rollback(str(self.root / "demo"))
        for key, raw in current.items():
            self.assertEqual(Path(self.paths[key]).read_bytes(), raw)
        self.assertEqual(Path(self.paths["index_file"]).read_bytes(), index_before)
        self.assertFalse(list(self.root.glob(".jev-rollback-*")))

    def test_history_limit_is_per_module(self):
        other = jev.ThreeFileManager.resolve_paths(str(self.root / "other"))
        self.checkpoint(9, paths=other, ids=("other_001",))
        for n in range(12):
            self.checkpoint(n)
        history = self.index()["history"]
        self.assertEqual(sum(s["module"] == "demo" for s in history), 10)
        self.assertEqual(sum(s["module"] == "other" for s in history), 1)

    def test_real_translation_can_be_rolled_back(self):
        p = Path(self.paths["spec_dsl"])
        p.write_bytes(block("demo_001", 1))
        jev.jev_spec_to_code(str(p))
        expected = Path(self.paths["code_file"]).read_bytes()
        jev.jev_translate_block("demo_001", "spec_to_code", str(p), block_content="设 value = 2")
        self.assertNotEqual(Path(self.paths["code_file"]).read_bytes(), expected)
        jev.jev_rollback(str(p))
        self.assertEqual(Path(self.paths["code_file"]).read_bytes(), expected)


if __name__ == "__main__":
    unittest.main()
