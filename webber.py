#!/usr/bin/env python3
"""
Webber - A text-mode web/document reader.

Supports:
  - Full-screen interactive mode (curses)
  - Batch mode (print to stdout)
  - Hyperlink navigation
  - Full text search
  - Colors
"""

import argparse
import curses
import re
import sys
import textwrap
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------

@dataclass
class Link:
    """Represents a hyperlink in the document."""
    text: str
    url: str
    line: int       # line index in rendered lines
    col_start: int  # column where link text starts
    col_end: int    # column where link text ends (exclusive)


@dataclass
class Document:
    """Parsed document ready for display."""
    lines: List[str] = field(default_factory=list)
    links: List[Link] = field(default_factory=list)
    title: str = ""
    source_url: str = ""


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

# Simple HTML tag stripper
_TAG_RE = re.compile(r"<[^>]+>")
_ENTITY_RE = re.compile(r"&([a-zA-Z]+|#[0-9]+|#x[0-9a-fA-F]+);")
_ENTITIES = {
    "amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'",
    "nbsp": " ", "copy": "©", "reg": "®", "trade": "™",
    "mdash": "—", "ndash": "–", "ldquo": "\u201c", "rdquo": "\u201d",
    "lsquo": "\u2018", "rsquo": "\u2019",
}

_LINK_RE = re.compile(r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
_TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)


def _decode_entity(m: re.Match) -> str:
    name = m.group(1)
    if name.startswith("#x"):
        return chr(int(name[2:], 16))
    if name.startswith("#"):
        return chr(int(name[1:]))
    return _ENTITIES.get(name, m.group(0))


def _strip_tags(html: str) -> str:
    text = _TAG_RE.sub("", html)
    text = _ENTITY_RE.sub(_decode_entity, text)
    return text


def _extract_links_html(html: str, base_url: str = "") -> List[Tuple[str, str]]:
    """Return list of (link_text, url) from raw HTML."""
    links = []
    for m in _LINK_RE.finditer(html):
        url = m.group(1).strip()
        text = _strip_tags(m.group(2)).strip()
        if not url.startswith(("http://", "https://", "ftp://")):
            url = _resolve_url(base_url, url)
        if text:
            links.append((text, url))
    return links


def _resolve_url(base: str, href: str) -> str:
    if not base:
        return href
    if href.startswith(("http://", "https://", "ftp://")):
        return href
    if href.startswith("//"):
        scheme = base.split("://")[0] if "://" in base else "https"
        return scheme + ":" + href
    if href.startswith("/"):
        if "://" in base:
            parts = base.split("/")
            return parts[0] + "//" + parts[2] + href
        return href
    # relative
    base_dir = base.rsplit("/", 1)[0] if "/" in base else base
    return base_dir + "/" + href


def parse_html(html: str, url: str = "", width: int = 80) -> Document:
    """Parse HTML into a Document."""
    doc = Document(source_url=url)

    # title
    tm = _TITLE_RE.search(html)
    if tm:
        doc.title = _strip_tags(tm.group(1)).strip()

    # collect raw links before stripping
    raw_links = _extract_links_html(html, url)

    # strip tags for body text
    text = _strip_tags(html)

    # wrap and build lines
    raw_lines = text.splitlines()
    wrapped: List[str] = []
    for raw_line in raw_lines:
        raw_line = raw_line.strip()
        if not raw_line:
            wrapped.append("")
            continue
        for wl in textwrap.wrap(raw_line, width) or [""]:
            wrapped.append(wl)

    doc.lines = wrapped

    # Place links: find each link text in the rendered lines
    for link_text, link_url in raw_links:
        _place_link(doc, link_text, link_url)

    return doc


def parse_plain_text(text: str, url: str = "", width: int = 80) -> Document:
    """Parse plain text into a Document."""
    doc = Document(source_url=url)
    lines: List[str] = []
    for raw_line in text.splitlines():
        raw_line = raw_line.rstrip()
        if not raw_line:
            lines.append("")
            continue
        for wl in textwrap.wrap(raw_line, width) or [raw_line]:
            lines.append(wl)
    doc.lines = lines
    return doc


def _place_link(doc: Document, link_text: str, url: str) -> None:
    """Find link_text in doc.lines and register a Link."""
    for i, line in enumerate(doc.lines):
        idx = line.find(link_text)
        if idx != -1:
            doc.links.append(Link(
                text=link_text,
                url=url,
                line=i,
                col_start=idx,
                col_end=idx + len(link_text),
            ))
            return


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------

def fetch_url(url: str, timeout: int = 10) -> Tuple[str, str]:
    """Fetch URL, return (content, content_type)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Webber/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_type = resp.headers.get_content_type() or ""
        charset = resp.headers.get_content_charset() or "utf-8"
        data = resp.read()
    return data.decode(charset, errors="replace"), content_type


def load_document(source: str, width: int = 80) -> Document:
    """Load a document from a URL or file path."""
    if source.startswith(("http://", "https://", "ftp://")):
        content, ctype = fetch_url(source)
        if "html" in ctype:
            return parse_html(content, url=source, width=width)
        return parse_plain_text(content, url=source, width=width)

    # local file
    with open(source, encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    if source.endswith((".html", ".htm")):
        return parse_html(content, url=source, width=width)
    return parse_plain_text(content, url=source, width=width)


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------

def batch_mode(doc: Document, use_color: bool = False) -> None:
    """Print document to stdout (batch/pipe mode)."""
    if doc.title:
        print(f"=== {doc.title} ===")
        print()

    link_index: dict[int, List[Link]] = {}
    for lnk in doc.links:
        link_index.setdefault(lnk.line, []).append(lnk)

    link_refs: List[str] = []
    for i, line in enumerate(doc.lines):
        line_links = link_index.get(i, [])
        if line_links and use_color:
            # ANSI underline for link text
            annotated = line
            offset = 0
            for lnk in sorted(line_links, key=lambda l: l.col_start):
                s = lnk.col_start + offset
                e = lnk.col_end + offset
                ref_num = len(link_refs) + 1
                link_refs.append(lnk.url)
                marker = f"\033[4m{lnk.text}[{ref_num}]\033[0m"
                annotated = annotated[:s] + marker + annotated[e:]
                # offset by visible characters added (the "[N]" suffix only)
                offset += len(f"[{ref_num}]")
            print(annotated)
        elif line_links:
            annotated = line
            offset = 0
            for lnk in sorted(line_links, key=lambda l: l.col_start):
                s = lnk.col_start + offset
                e = lnk.col_end + offset
                ref_num = len(link_refs) + 1
                link_refs.append(lnk.url)
                marker = f"{lnk.text}[{ref_num}]"
                annotated = annotated[:s] + marker + annotated[e:]
                offset += len(marker) - len(lnk.text)
            print(annotated)
        else:
            print(line)

    if link_refs:
        print()
        print("Links:")
        for j, url in enumerate(link_refs, 1):
            print(f"  [{j}] {url}")


# ---------------------------------------------------------------------------
# Full-screen curses mode
# ---------------------------------------------------------------------------

# Color pair IDs
CP_NORMAL = 0
CP_TITLE = 1
CP_LINK = 2
CP_LINK_ACTIVE = 3
CP_SEARCH_HIT = 4
CP_STATUS = 5


def _init_colors() -> None:
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(CP_LINK, curses.COLOR_GREEN, -1)
    curses.init_pair(CP_LINK_ACTIVE, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(CP_SEARCH_HIT, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(CP_STATUS, curses.COLOR_BLACK, curses.COLOR_WHITE)


@dataclass
class ViewerState:
    doc: Document
    scroll: int = 0               # first visible line
    active_link: int = -1         # index into doc.links
    search_term: str = ""
    search_hits: List[Tuple[int, int, int]] = field(default_factory=list)
    # search_hits: list of (line, col_start, col_end)
    search_hit_idx: int = -1
    status_msg: str = ""
    history: List[str] = field(default_factory=list)  # URL history for back navigation


def _build_search_hits(doc: Document, term: str) -> List[Tuple[int, int, int]]:
    hits = []
    if not term:
        return hits
    lterm = term.lower()
    for i, line in enumerate(doc.lines):
        start = 0
        ll = line.lower()
        while True:
            pos = ll.find(lterm, start)
            if pos == -1:
                break
            hits.append((i, pos, pos + len(term)))
            start = pos + 1
    return hits


def _draw_screen(stdscr: "curses._CursesWindow", state: ViewerState, use_color: bool) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    doc = state.doc

    # --- Status bar at top ---
    title_text = (doc.title or doc.source_url or "Webber")[:w - 1]
    if use_color:
        stdscr.attron(curses.color_pair(CP_TITLE))
    stdscr.addstr(0, 0, title_text.ljust(w - 1))
    if use_color:
        stdscr.attroff(curses.color_pair(CP_TITLE))

    # --- Content area ---
    content_h = h - 3  # reserve: 1 title row + 1 status row + 1 help row

    # Build a quick lookup: (line_idx, col) -> (link_idx, is_active)
    link_map: dict[Tuple[int, int, int], int] = {}
    for li, lnk in enumerate(doc.links):
        link_map[(lnk.line, lnk.col_start, lnk.col_end)] = li

    search_set: set[Tuple[int, int, int]] = set(state.search_hits)

    for row in range(content_h):
        line_idx = state.scroll + row
        if line_idx >= len(doc.lines):
            break
        line = doc.lines[line_idx]

        # Find links and search hits on this line, build annotated segments
        annotations: List[Tuple[int, int, int]] = []  # (col_start, col_end, attr)

        for (ll, cs, ce), li in link_map.items():
            if ll == line_idx:
                if li == state.active_link:
                    attr = curses.color_pair(CP_LINK_ACTIVE) if use_color else curses.A_REVERSE
                else:
                    attr = curses.color_pair(CP_LINK) if use_color else curses.A_UNDERLINE
                annotations.append((cs, ce, attr))

        for (ll, cs, ce) in search_set:
            if ll == line_idx:
                attr = curses.color_pair(CP_SEARCH_HIT) if use_color else curses.A_STANDOUT
                annotations.append((cs, ce, attr))

        annotations.sort()

        # Render line segment by segment
        col = 0
        seg_start = 0
        # merge overlapping annotations for simplicity (first wins)
        merged: List[Tuple[int, int, int]] = []
        for ann in annotations:
            if merged and ann[0] < merged[-1][1]:
                continue
            merged.append(ann)

        try:
            for (cs, ce, attr) in merged:
                # plain text before annotation
                if seg_start < cs:
                    plain = line[seg_start:cs]
                    stdscr.addstr(row + 1, col, plain[:w - 1 - col])
                    col += len(plain)
                # annotated text
                ann_text = line[cs:ce]
                stdscr.addstr(row + 1, col, ann_text[:w - 1 - col], attr)
                col += len(ann_text)
                seg_start = ce
            # remainder
            if seg_start < len(line):
                stdscr.addstr(row + 1, col, line[seg_start:][:w - 1 - col])
        except curses.error:
            pass

    # --- Second-to-last row: status bar ---
    total = len(doc.lines)
    pct = int(state.scroll * 100 / max(total - 1, 1))
    links_info = f"Link {state.active_link + 1}/{len(doc.links)}" if doc.links else ""
    search_info = f" Search: {state.search_term!r} ({len(state.search_hits)} hits)" if state.search_term else ""
    status = f" {pct}% ({state.scroll + 1}/{total}) {links_info}{search_info}"
    if state.status_msg:
        status = " " + state.status_msg
    status = status[:w - 1].ljust(w - 1)
    try:
        if use_color:
            stdscr.addstr(h - 2, 0, status, curses.color_pair(CP_STATUS))
        else:
            stdscr.addstr(h - 2, 0, status, curses.A_REVERSE)
    except curses.error:
        pass

    # --- Last row: help line ---
    help_text = "q:Quit  ↑↓/PgUp/PgDn:Scroll  Tab:Next link  Enter:Follow  /:Search  n:Next hit  b:Back"
    try:
        stdscr.addstr(h - 1, 0, help_text[:w - 1].ljust(w - 1),
                      curses.color_pair(CP_STATUS) if use_color else curses.A_REVERSE)
    except curses.error:
        pass

    stdscr.refresh()


def _input_string(stdscr: "curses._CursesWindow", prompt: str) -> str:
    """Show a prompt at the bottom and read a string."""
    h, w = stdscr.getmaxyx()
    curses.echo()
    curses.curs_set(1)
    try:
        stdscr.addstr(h - 1, 0, (prompt + " " * (w - len(prompt) - 1))[:w - 1], curses.A_REVERSE)
        stdscr.refresh()
        result = stdscr.getstr(h - 1, len(prompt), w - len(prompt) - 1)
        return result.decode("utf-8", errors="replace")
    finally:
        curses.noecho()
        curses.curs_set(0)


def _scroll_to_line(state: ViewerState, target_line: int, content_h: int) -> None:
    state.scroll = max(0, min(target_line, len(state.doc.lines) - 1))


def fullscreen_mode(
    initial_doc: Document,
    initial_url: str,
    use_color: bool = True,
    initial_search: str = "",
) -> None:
    """Run the full-screen curses viewer."""
    def _run(stdscr: "curses._CursesWindow") -> None:
        nonlocal use_color
        curses.curs_set(0)
        if use_color and curses.has_colors():
            _init_colors()
        else:
            use_color = False

        state = ViewerState(doc=initial_doc)
        state.history = [initial_url]
        if initial_search:
            state.search_term = initial_search
            state.search_hits = _build_search_hits(initial_doc, initial_search)
            if state.search_hits:
                state.search_hit_idx = 0

        while True:
            h, w = stdscr.getmaxyx()
            content_h = h - 2
            _draw_screen(stdscr, state, use_color and curses.has_colors())
            state.status_msg = ""

            key = stdscr.getch()

            # Quit
            if key in (ord("q"), ord("Q")):
                break

            # Scroll
            elif key in (curses.KEY_DOWN, ord("j")):
                state.scroll = min(state.scroll + 1, max(0, len(state.doc.lines) - content_h))
            elif key in (curses.KEY_UP, ord("k")):
                state.scroll = max(0, state.scroll - 1)
            elif key in (curses.KEY_NPAGE, ord(" ")):
                state.scroll = min(state.scroll + content_h, max(0, len(state.doc.lines) - content_h))
            elif key in (curses.KEY_PPAGE,):
                state.scroll = max(0, state.scroll - content_h)
            elif key in (curses.KEY_HOME, ord("g")):
                state.scroll = 0
            elif key in (curses.KEY_END, ord("G")):
                state.scroll = max(0, len(state.doc.lines) - content_h)

            # Link navigation
            elif key == ord("\t") or key == curses.KEY_RIGHT:
                if state.doc.links:
                    state.active_link = (state.active_link + 1) % len(state.doc.links)
                    lnk = state.doc.links[state.active_link]
                    if lnk.line < state.scroll or lnk.line >= state.scroll + content_h:
                        state.scroll = max(0, lnk.line - content_h // 2)
            elif key == curses.KEY_BTAB or key == curses.KEY_LEFT:
                if state.doc.links:
                    state.active_link = (state.active_link - 1) % len(state.doc.links)
                    lnk = state.doc.links[state.active_link]
                    if lnk.line < state.scroll or lnk.line >= state.scroll + content_h:
                        state.scroll = max(0, lnk.line - content_h // 2)

            # Follow link
            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                if 0 <= state.active_link < len(state.doc.links):
                    lnk = state.doc.links[state.active_link]
                    try:
                        new_doc = load_document(lnk.url, width=w - 2)
                        state.history.append(lnk.url)
                        state.doc = new_doc
                        state.scroll = 0
                        state.active_link = 0 if new_doc.links else -1
                        state.search_term = ""
                        state.search_hits = []
                    except Exception as exc:
                        state.status_msg = f"Error: {exc}"

            # Back
            elif key == ord("b") or key == ord("B"):
                if len(state.history) > 1:
                    state.history.pop()
                    prev_url = state.history[-1]
                    try:
                        new_doc = load_document(prev_url, width=w - 2)
                        state.doc = new_doc
                        state.scroll = 0
                        state.active_link = 0 if new_doc.links else -1
                        state.search_term = ""
                        state.search_hits = []
                    except Exception as exc:
                        state.status_msg = f"Error: {exc}"
                else:
                    state.status_msg = "No history."

            # Search
            elif key == ord("/"):
                term = _input_string(stdscr, "/")
                if term:
                    state.search_term = term
                    state.search_hits = _build_search_hits(state.doc, term)
                    state.search_hit_idx = -1
                    if state.search_hits:
                        state.search_hit_idx = 0
                        target = state.search_hits[0][0]
                        state.scroll = max(0, target - content_h // 2)
                    else:
                        state.status_msg = f"Pattern not found: {term!r}"
                else:
                    state.search_term = ""
                    state.search_hits = []

            # Next search hit
            elif key == ord("n"):
                if state.search_hits:
                    state.search_hit_idx = (state.search_hit_idx + 1) % len(state.search_hits)
                    target = state.search_hits[state.search_hit_idx][0]
                    state.scroll = max(0, target - content_h // 2)
                else:
                    state.status_msg = "No search active. Press / to search."

            # Previous search hit
            elif key == ord("N"):
                if state.search_hits:
                    state.search_hit_idx = (state.search_hit_idx - 1) % len(state.search_hits)
                    target = state.search_hits[state.search_hit_idx][0]
                    state.scroll = max(0, target - content_h // 2)

    curses.wrapper(_run)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="webber",
        description="Webber - a text-mode web/document reader",
    )
    parser.add_argument("source", nargs="?", help="URL or file path to open")
    parser.add_argument(
        "-b", "--batch",
        action="store_true",
        help="Batch mode: print document to stdout and exit",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colors",
    )
    parser.add_argument(
        "-w", "--width",
        type=int,
        default=80,
        help="Line wrap width (default: 80)",
    )
    parser.add_argument(
        "-s", "--search",
        metavar="TERM",
        help="Search term to highlight on startup",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.source:
        # Interactive: read from stdin if piped, else show help
        if not sys.stdin.isatty():
            content = sys.stdin.read()
            doc = parse_plain_text(content, width=args.width)
        else:
            parser.print_help()
            return 0
    else:
        try:
            doc = load_document(args.source, width=args.width)
        except Exception as exc:
            print(f"webber: error loading {args.source!r}: {exc}", file=sys.stderr)
            return 1

    use_color = not args.no_color

    if args.batch or not sys.stdout.isatty():
        batch_mode(doc, use_color=use_color and sys.stdout.isatty())
        return 0

    # Fullscreen mode
    source_label = args.source or "<stdin>"
    fullscreen_mode(doc, source_label, use_color=use_color, initial_search=args.search or "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
