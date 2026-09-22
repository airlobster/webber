"""Tests for webber.py"""

import sys
import os
import io
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from webber import (
    parse_html,
    parse_plain_text,
    batch_mode,
    _build_search_hits,
    _resolve_url,
    _strip_tags,
    Link,
    Document,
)


class TestStripTags(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(_strip_tags("<b>hello</b>"), "hello")

    def test_entity_amp(self):
        self.assertEqual(_strip_tags("a &amp; b"), "a & b")

    def test_entity_lt_gt(self):
        self.assertEqual(_strip_tags("&lt;tag&gt;"), "<tag>")

    def test_entity_numeric(self):
        self.assertEqual(_strip_tags("&#65;"), "A")

    def test_entity_hex(self):
        self.assertEqual(_strip_tags("&#x41;"), "A")

    def test_nbsp(self):
        self.assertEqual(_strip_tags("a&nbsp;b"), "a b")


class TestResolveUrl(unittest.TestCase):
    def test_absolute(self):
        self.assertEqual(
            _resolve_url("http://example.com/page", "http://other.com/foo"),
            "http://other.com/foo",
        )

    def test_root_relative(self):
        self.assertEqual(
            _resolve_url("http://example.com/a/b", "/c/d"),
            "http://example.com/c/d",
        )

    def test_relative(self):
        self.assertEqual(
            _resolve_url("http://example.com/a/b", "c"),
            "http://example.com/a/c",
        )

    def test_protocol_relative(self):
        self.assertEqual(
            _resolve_url("https://example.com/page", "//cdn.example.com/file"),
            "https://cdn.example.com/file",
        )


class TestParsePlainText(unittest.TestCase):
    def test_lines(self):
        doc = parse_plain_text("hello\nworld")
        self.assertIn("hello", doc.lines)
        self.assertIn("world", doc.lines)

    def test_no_links(self):
        doc = parse_plain_text("no links here")
        self.assertEqual(doc.links, [])

    def test_wrapping(self):
        long_line = "word " * 30
        doc = parse_plain_text(long_line, width=40)
        for line in doc.lines:
            self.assertLessEqual(len(line), 40)


class TestParseHtml(unittest.TestCase):
    def test_title(self):
        html = "<html><head><title>My Page</title></head><body>Hello</body></html>"
        doc = parse_html(html)
        self.assertEqual(doc.title, "My Page")

    def test_strips_tags(self):
        html = "<p>Hello <b>World</b></p>"
        doc = parse_html(html)
        full_text = "\n".join(doc.lines)
        self.assertIn("Hello", full_text)
        self.assertIn("World", full_text)
        self.assertNotIn("<p>", full_text)
        self.assertNotIn("<b>", full_text)

    def test_link_extracted(self):
        html = '<p>Visit <a href="http://example.com">Example</a> today</p>'
        doc = parse_html(html, width=120)
        self.assertEqual(len(doc.links), 1)
        self.assertEqual(doc.links[0].url, "http://example.com")
        self.assertEqual(doc.links[0].text, "Example")

    def test_multiple_links(self):
        html = (
            '<a href="http://a.com">A</a> and '
            '<a href="http://b.com">B</a>'
        )
        doc = parse_html(html, width=120)
        urls = {lnk.url for lnk in doc.links}
        self.assertIn("http://a.com", urls)
        self.assertIn("http://b.com", urls)


class TestBuildSearchHits(unittest.TestCase):
    def test_finds_term(self):
        doc = parse_plain_text("the quick brown fox\njumps over the lazy dog")
        hits = _build_search_hits(doc, "the")
        self.assertGreaterEqual(len(hits), 2)

    def test_case_insensitive(self):
        doc = parse_plain_text("Hello World")
        hits = _build_search_hits(doc, "hello")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][1], 0)

    def test_no_match(self):
        doc = parse_plain_text("Hello World")
        hits = _build_search_hits(doc, "xyz")
        self.assertEqual(hits, [])

    def test_empty_term(self):
        doc = parse_plain_text("Hello World")
        hits = _build_search_hits(doc, "")
        self.assertEqual(hits, [])


class TestBatchMode(unittest.TestCase):
    def _capture(self, doc, use_color=False):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            batch_mode(doc, use_color=use_color)
        finally:
            sys.stdout = old
        return buf.getvalue()

    def test_plain_output(self):
        doc = parse_plain_text("Hello batch world")
        out = self._capture(doc)
        self.assertIn("Hello batch world", out)

    def test_title_shown(self):
        doc = parse_html("<title>My Doc</title><p>Content</p>")
        out = self._capture(doc)
        self.assertIn("My Doc", out)

    def test_link_refs_shown(self):
        html = '<p>See <a href="http://example.com">Example</a> now</p>'
        doc = parse_html(html, width=120)
        out = self._capture(doc)
        self.assertIn("http://example.com", out)
        self.assertIn("[1]", out)

    def test_no_color_no_ansi(self):
        html = '<p>See <a href="http://example.com">Example</a> now</p>'
        doc = parse_html(html, width=120)
        out = self._capture(doc, use_color=False)
        self.assertNotIn("\033[", out)


if __name__ == "__main__":
    unittest.main()
