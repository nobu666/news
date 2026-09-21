#!/usr/bin/env python3
"""Tests for oss-seed-scout/fetch.py (no network: parsers are pure, fetchers are mocked).

  - each parser maps the upstream JSON shape to the common item shape
  - titles/snippets are clipped, missing fields default to 0 / ""
  - one failing source lands in "errors" and the others still print
  - an invalid subreddit name never reaches the network
"""
import io
import json
import os
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch  # noqa: E402


class ParserTests(unittest.TestCase):
    def test_reddit_atom_shape_and_clip(self):
        atom = ('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
                '<entry><author><name>/u/alice</name></author><title>' + "T" * 500 + '</title>'
                '<link href="https://www.reddit.com/r/x/1"/>'
                '<content type="html">&lt;p&gt;line1&lt;/p&gt;&lt;p&gt;line2 ' + "s" * 500 + '&lt;/p&gt;</content></entry>'
                '<entry><link href="https://www.reddit.com/r/x/2"/></entry>'  # no title -> skipped
                '</feed>')
        items = fetch.parse_reddit(atom)
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(len(it["title"]), fetch.TITLE_LEN)
        self.assertTrue(it["title"].endswith("…"))
        self.assertEqual(it["url"], "https://www.reddit.com/r/x/1")
        self.assertEqual((it["score"], it["comments"]), (0, 0))
        self.assertTrue(it["snippet"].startswith("/u/alice: line1 line2 "))
        self.assertNotIn("<p>", it["snippet"])
        self.assertEqual(len(it["snippet"]), fetch.SNIPPET_LEN)

    def test_reddit_bare_angle_brackets_in_prose_survive(self):
        atom = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>t</title><link href="u"/>'
                '<content type="html">&lt;p&gt;if x &amp;lt; 2 and y &amp;gt; 3: go()&lt;/p&gt;</content></entry></feed>')
        self.assertEqual(fetch.parse_reddit(atom)[0]["snippet"], "if x < 2 and y > 3: go()")

    def test_reddit_time_budget_skips_remaining_subreddits(self):
        clock = iter([0.0, 0.0, 999.0])
        with mock.patch.object(fetch, "fetch_reddit", return_value=[]) as fr, \
             mock.patch.object(fetch, "fetch_hn", return_value=[]), \
             mock.patch.object(fetch, "fetch_ask_hn", return_value=[]), \
             mock.patch.object(fetch, "fetch_show_hn", return_value=[]), \
             mock.patch.object(fetch, "fetch_github", return_value=[]), \
             mock.patch.object(fetch, "fetch_lobsters", return_value=[]), \
             mock.patch.object(fetch, "fetch_hatena", return_value=[]), \
             mock.patch.object(fetch, "fetch_hf", return_value=[]), \
             mock.patch.object(fetch.time, "sleep"), \
             mock.patch.object(fetch.time, "monotonic", side_effect=lambda: next(clock)):
            out = MainTests._run(self, {"SCOUT_SUBREDDITS": "a b"})
        fr.assert_called_once_with("a")
        self.assertIn("time budget", out["errors"][0])

    def test_hn_falls_back_to_discussion_url(self):
        data = {"hits": [
            {"title": "A", "url": "https://a.example", "points": 150, "num_comments": 3, "objectID": "1"},
            {"title": "B", "url": None, "points": None, "objectID": "2"},
            {"url": "https://c.example", "objectID": "3"},  # no title -> skipped
        ]}
        items = fetch.parse_hn(data)
        self.assertEqual([i["url"] for i in items], ["https://a.example", "https://news.ycombinator.com/item?id=2"])
        self.assertEqual(items[1]["score"], 0)
        self.assertIn("item?id=1", items[0]["snippet"])

    def test_link_breakout_is_neutralised(self):
        data = {"hits": [{"title": "Cool tool](https://evil.example/pwn) [see", "url": "https://a.example/x) y",
                          "objectID": "1"}]}
        it = fetch.parse_hn(data)[0]
        self.assertEqual(it["title"], "Cool tool\\](https://evil.example/pwn) \\[see")
        self.assertEqual(it["url"], "https://a.example/x%29%20y")
        self.assertEqual(fetch.md_url("javascript:alert(1)"), "")

    def test_github_shape(self):
        data = {"items": [{"full_name": "o/r", "html_url": "https://github.com/o/r", "stargazers_count": 42,
                           "forks_count": 7, "language": "Go", "description": None}]}
        it = fetch.parse_github(data)[0]
        self.assertEqual((it["title"], it["score"], it["comments"]), ("o/r", 42, 7))
        self.assertEqual(it["snippet"], "Go · open issues 0 ·")

    def test_lobsters_shape(self):
        data = [{"title": "T", "url": None, "comments_url": "https://lobste.rs/s/x", "score": 3, "comment_count": 1,
                 "tags": ["ai", "security"]}, {"score": 9}]
        items = fetch.parse_lobsters(data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], "https://lobste.rs/s/x")
        self.assertEqual(items[0]["snippet"], "tags: ai, security · lobste.rs: https://lobste.rs/s/x")
        self.assertEqual(fetch.parse_lobsters({"not": "a list"}), [])

    def test_hatena_rss1_shape(self):
        rdf = ('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"'
               ' xmlns:hatena="http://www.hatena.ne.jp/info/xmlns#"><channel><title>c</title></channel>'
               '<item><title>記事</title><link>https://ex.jp/a</link><description>説明</description>'
               '<hatena:bookmarkcount>318</hatena:bookmarkcount></item>'
               '<item><link>https://ex.jp/b</link></item></rdf:RDF>')
        items = fetch.parse_hatena(rdf)
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0]["title"], items[0]["url"], items[0]["score"], items[0]["snippet"]),
                         ("記事", "https://ex.jp/a", 318, "説明"))

    def test_hf_shape(self):
        data = [{"id": "org/model", "likes": 5, "downloads": 1200, "pipeline_tag": "text-generation", "tags": ["gguf"]},
                {"likes": 1}]
        items = fetch.parse_hf(data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], "https://huggingface.co/org/model")
        self.assertEqual(items[0]["snippet"], "text-generation · downloads 1200 · gguf")

    def test_item_cap(self):
        data = {"hits": [{"title": str(i), "objectID": str(i)} for i in range(100)]}
        self.assertEqual(len(fetch.parse_hn(data)), fetch.MAX_ITEMS)


class FetchRedditTests(unittest.TestCase):
    ATOM = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>t</title><link href="u"/></entry></feed>'

    def _http_error(self, code):
        return urllib.error.HTTPError("u", code, "x", {}, None)

    def test_429_is_retried_once_after_a_pause(self):
        with mock.patch.object(fetch, "_get", side_effect=[self._http_error(429), self.ATOM]) as g, \
             mock.patch.object(fetch.time, "sleep") as s:
            items = fetch.fetch_reddit("ClaudeAI")
        self.assertEqual(len(items), 1)
        self.assertEqual(g.call_count, 2)
        s.assert_called_once_with(fetch.REDDIT_RETRY_WAIT)

    def test_other_http_errors_are_not_retried(self):
        with mock.patch.object(fetch, "_get", side_effect=self._http_error(403)) as g, \
             mock.patch.object(fetch.time, "sleep") as s:
            with self.assertRaises(urllib.error.HTTPError):
                fetch.fetch_reddit("ClaudeAI")
        self.assertEqual(g.call_count, 1)
        s.assert_not_called()


class MainTests(unittest.TestCase):
    def _run(self, env):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"NEWS_ENV": "/nonexistent", **env}, clear=False), redirect_stdout(buf):
            fetch.main()
        return json.loads(buf.getvalue())

    def test_one_failing_source_does_not_stop_the_others(self):
        with mock.patch.object(fetch, "fetch_reddit", side_effect=RuntimeError("boom")), \
             mock.patch.object(fetch, "fetch_hn", return_value=[{"title": "h"}]), \
             mock.patch.object(fetch, "fetch_ask_hn", return_value=[]), \
             mock.patch.object(fetch, "fetch_show_hn", return_value=[]), \
             mock.patch.object(fetch, "fetch_github", return_value=[]), \
             mock.patch.object(fetch, "fetch_lobsters", return_value=[]), \
             mock.patch.object(fetch, "fetch_hatena", return_value=[]), \
             mock.patch.object(fetch, "fetch_hf", return_value=[]), \
             mock.patch.object(fetch.time, "sleep"):
            out = self._run({"SCOUT_SUBREDDITS": "ClaudeAI"})
        self.assertEqual(out["hn"], [{"title": "h"}])
        self.assertEqual(out["reddit"], {})
        self.assertEqual(out["errors"], ["reddit r/ClaudeAI: boom"])

    def test_invalid_subreddit_never_hits_the_network(self):
        with mock.patch.object(fetch, "fetch_reddit") as fr, \
             mock.patch.object(fetch, "fetch_hn", return_value=[]), \
             mock.patch.object(fetch, "fetch_ask_hn", return_value=[]), \
             mock.patch.object(fetch, "fetch_show_hn", return_value=[]), \
             mock.patch.object(fetch, "fetch_github", return_value=[]), \
             mock.patch.object(fetch, "fetch_lobsters", return_value=[]), \
             mock.patch.object(fetch, "fetch_hatena", return_value=[]), \
             mock.patch.object(fetch, "fetch_hf", return_value=[]), \
             mock.patch.object(fetch.time, "sleep"):
            fr.return_value = []
            out = self._run({"SCOUT_SUBREDDITS": "ok_sub ../evil?x=1"})
        fr.assert_called_once_with("ok_sub")
        self.assertEqual(len(out["errors"]), 1)
        self.assertIn("invalid subreddit", out["errors"][0])


if __name__ == "__main__":
    unittest.main()
