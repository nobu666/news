#!/usr/bin/env python3
"""Minimal tests for prune.py (stdlib unittest only).

The logic that must not break:
  - only YYYY-MM-DD-{morning|evening}.md older than the cutoff is deleted
  - other files (notes, invalid dates, wrong names) are never touched
  - NEWS_RETENTION_DAYS unset/0/garbage disables pruning (CLI prints disabled)
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

# Disable NEWS_ENV before import so _load_env_file does not read a real file
os.environ["NEWS_ENV"] = os.devnull
_spec = importlib.util.spec_from_file_location("prune", Path(__file__).with_name("prune.py"))
prune_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prune_mod)


class TestPrune(unittest.TestCase):
    def _mkdir(self, names):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        for n in names:
            (d / n).write_text("x")
        return d

    def test_deletes_only_old_digests(self):
        d = self._mkdir(
            [
                "2026-06-01-morning.md",   # old -> delete
                "2026-06-01-evening.md",   # old -> delete
                "2026-06-25-morning.md",   # within window -> keep
                "2026-07-02-evening.md",   # today -> keep
            ]
        )
        result = prune_mod.prune(d, 14, date(2026, 7, 2))
        self.assertEqual(result["deleted"], ["2026-06-01-evening.md", "2026-06-01-morning.md"])
        self.assertEqual(result["kept"], 2)
        self.assertEqual(
            sorted(p.name for p in d.iterdir()),
            ["2026-06-25-morning.md", "2026-07-02-evening.md"],
        )

    def test_never_touches_non_digest_files(self):
        d = self._mkdir(
            [
                "README.md",
                "2020-01-01-notes.md",       # wrong suffix
                "2026-13-40-morning.md",     # invalid date
                "2020-01-01-morning.md.bak", # wrong extension
            ]
        )
        result = prune_mod.prune(d, 1, date(2026, 7, 2))
        self.assertEqual(result["deleted"], [])
        self.assertEqual(len(list(d.iterdir())), 4)

    def test_boundary_is_kept(self):
        d = self._mkdir(["2026-06-18-morning.md"])  # exactly retention days ago
        result = prune_mod.prune(d, 14, date(2026, 7, 2))
        self.assertEqual(result["deleted"], [])
        self.assertEqual(result["kept"], 1)

    def _run_cli(self, extra_env):
        env = {**os.environ, "NEWS_ENV": os.devnull, **extra_env}
        out = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("prune.py"))],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(out.returncode, 0)
        return json.loads(out.stdout)

    def test_cli_disabled_when_empty_zero_or_garbage(self):
        for v in ("", "0", "banana"):
            result = self._run_cli({"NEWS_RETENTION_DAYS": v})
            self.assertTrue(result.get("disabled"), f"NEWS_RETENTION_DAYS={v!r}")

    def test_cli_prunes_via_env(self):
        d = self._mkdir(["2026-06-01-morning.md", "2099-01-01-evening.md"])
        result = self._run_cli({"NEWS_RETENTION_DAYS": "14", "NEWS_DIR": str(d)})
        self.assertEqual(result["deleted"], ["2026-06-01-morning.md"])
        self.assertEqual(result["kept"], 1)


if __name__ == "__main__":
    unittest.main()
