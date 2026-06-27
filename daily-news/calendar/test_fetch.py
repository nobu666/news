#!/usr/bin/env python3
"""Minimal tests for the dependency-free logic in fetch.py (stdlib unittest only).

The network parts (Calendar API) are not tested. The pure logic that must not break:
  - _load_env_file: .env parsing (skip comments/blanks, `=` inside values, existing env wins)
  - load_creds: absorb Google's {installed} / {web} / flat credential shapes
  - _harden_perms: force 0700/0600 on secrets
  - _window: today 00:00 local -> (today + DAYS_AHEAD + 1) 00:00 local
  - CALENDAR_ENABLED gate: when 0, print [] and exit without touching the network
"""
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

os.environ["NEWS_ENV"] = os.devnull
_spec = importlib.util.spec_from_file_location("fetch", Path(__file__).with_name("fetch.py"))
fetch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch)


class LoadEnvFile(unittest.TestCase):
    def setUp(self):
        self._saved = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)

    def _load(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8")
        f.write(text)
        f.close()
        os.environ["NEWS_ENV"] = f.name
        try:
            fetch._load_env_file()
        finally:
            os.unlink(f.name)

    def test_parses_and_skips_comments_blanks(self):
        os.environ.pop("NEWS_DIR", None)
        os.environ.pop("FOO", None)
        self._load("# comment\n\nNEWS_DIR=/tmp/news\nFOO = bar \n")
        self.assertEqual(os.environ["NEWS_DIR"], "/tmp/news")
        self.assertEqual(os.environ["FOO"], "bar")

    def test_value_may_contain_equals(self):
        os.environ.pop("Q", None)
        self._load("Q=a=b=c\n")
        self.assertEqual(os.environ["Q"], "a=b=c")

    def test_existing_env_wins(self):
        os.environ["NEWS_DIR"] = "/already"
        self._load("NEWS_DIR=/from-file\n")
        self.assertEqual(os.environ["NEWS_DIR"], "/already")


class LoadCreds(unittest.TestCase):
    def setUp(self):
        self._saved_dir = fetch.CONFIG_DIR

    def tearDown(self):
        fetch.CONFIG_DIR = self._saved_dir

    def _creds_dir(self, obj):
        d = Path(tempfile.mkdtemp())
        (d / "credentials.json").write_text(json.dumps(obj), encoding="utf-8")
        fetch.CONFIG_DIR = d
        return d

    def test_installed_form(self):
        self._creds_dir({"installed": {"client_id": "id1", "client_secret": "s1"}})
        self.assertEqual(fetch.load_creds(), {"client_id": "id1", "client_secret": "s1"})

    def test_web_form(self):
        self._creds_dir({"web": {"client_id": "id2", "client_secret": "s2"}})
        self.assertEqual(fetch.load_creds(), {"client_id": "id2", "client_secret": "s2"})

    def test_flat_form(self):
        self._creds_dir({"client_id": "id3", "client_secret": "s3"})
        self.assertEqual(fetch.load_creds(), {"client_id": "id3", "client_secret": "s3"})


class HardenPerms(unittest.TestCase):
    def setUp(self):
        self._saved_dir = fetch.CONFIG_DIR

    def tearDown(self):
        fetch.CONFIG_DIR = self._saved_dir

    def test_sets_0700_and_0600(self):
        d = Path(tempfile.mkdtemp())
        (d / "credentials.json").write_text("{}", encoding="utf-8")
        (d / "token.json").write_text("{}", encoding="utf-8")
        fetch.CONFIG_DIR = d
        fetch._harden_perms()
        self.assertEqual(stat.S_IMODE(d.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((d / "credentials.json").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((d / "token.json").stat().st_mode), 0o600)


class Window(unittest.TestCase):
    def test_starts_at_local_midnight_and_spans_days_ahead_plus_one(self):
        saved = fetch.DAYS_AHEAD
        fetch.DAYS_AHEAD = 1
        try:
            s, e = fetch._window()
            start = datetime.fromisoformat(s)
            end = datetime.fromisoformat(e)
            self.assertEqual((start.hour, start.minute, start.second, start.microsecond), (0, 0, 0, 0))
            self.assertEqual(end - start, timedelta(days=2))  # today + tomorrow
        finally:
            fetch.DAYS_AHEAD = saved


class CalendarGate(unittest.TestCase):
    def test_disabled_outputs_empty_no_network(self):
        env = dict(os.environ, CALENDAR_ENABLED="0", NEWS_ENV=os.devnull)
        r = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("fetch.py"))],
            capture_output=True, text=True, env=env, timeout=15,
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
