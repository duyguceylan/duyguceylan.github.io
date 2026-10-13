#!/usr/bin/env python3
"""Build the static website from plain-text source files.

Reads:
  data/resume.json         - who the site is about (identity, socials, awards, ...)
  data/publications.bib    - every publication in the "Publications" section
  news/*.md                - one file per news item (YAML front matter + Markdown)
  templates/site.html      - the Jinja2 layout
  assets/*                 - static assets (style.css, main.js, profile.jpg, ...)

Writes:
  dist/                    - a self-contained static site, ready to host anywhere

Usage:
  python3 build.py
"""

import calendar
import glob
import json
import os
import re
import shutil
import sys

try:
    import markdown
except ImportError:
    markdown = None

try:
    import yaml
except ImportError:
    yaml = None

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------- utilities
def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def month_name(num):
    num = int(num)
    return calendar.month_name[num] if 1 <= num <= 12 else ""


def fmt_date(raw):
    s = str(raw).strip()[:10]
    parts = s.split("-")
    if len(parts) != 3 or not parts[1].isdigit():
        return s
    y, m, d = parts
    name = month_name(m)
    return f"{int(d)} {name} {y}" if name else s


def norm_ws(s):
    return re.sub(r"\s+", " ", s or "").strip()


# --------------------------------------------------------------- bib parser
def _clean_value(v):
    v = v.strip()
    if len(v) >= 2 and v[0] in "\"'":
        v = v[1:-1]
    elif v.startswith("{") and v.endswith("}"):
        v = v[1:-1]
    return re.sub(r"\s+", " ", v).strip()


def _split_top(body, sep=","):
    """Split on top-level separators, ignoring those nested in braces or quotes.

    A quote character opens or closes a quoted section only when at the top
    level (depth 0). Inside a braced group (depth >= 1) it is an ordinary
    character, so apostrophes in titles (for example "MLLMs'") do not break
    the field splitting.
    """
    parts, cur = [], []
    depth = 0
    quote = None
    for ch in body:
        if quote:
            cur.append(ch)
            if ch == quote and depth == 0:
                quote = None
            continue
        if ch in "\"'":
            if depth == 0:
                quote = ch
            cur.append(ch)
        elif ch == "{":
            depth += 1
            cur.append(ch)
        elif ch == "}":
            depth = max(0, depth - 1)
            cur.append(ch)
        elif ch == sep and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def strip_comments(text):
    """Drop BibTeX comment lines (lines starting with '%') at top level."""
    out = []
    depth = 0
    for raw in text.splitlines():
        stripped = raw.strip()
        if depth <= 0 and stripped.startswith("%"):
            continue
        depth += raw.count("{") - raw.count("}")
        if depth < 0:
            depth = 0
        out.append(raw)
    return "\n".join(out)


def _read_braced(text, i):
    """Read a braced group starting at text[i]. Return (content, index_after)."""
    open_ch = text[i]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    p = i
    n = len(text)
    while p < n:
        c = text[p]
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return text[i + 1 : p], p + 1
        p += 1
    return text[i + 1 :], n


def parse_bib(text):
    """Minimal, tolerant BibTeX parser. Good enough for well-formed entries."""
    entries = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != "@":
            i += 1
            continue

        j = i + 1
        while j < n and (text[j].isalpha() or text[j] == "-"):
            j += 1
        etype = text[i + 1 : j].lower()

        k = j
        while k < n and text[k] not in "{[":
            k += 1
        if k >= n:
            break

        body, i = _read_braced(text, k)
        if etype in ("comment", "preamble", "string"):
            continue

        chunks = _split_top(body)
        key = chunks[0] if chunks else ""
        fields = {}
        for chunk in chunks[1:]:
            if "=" not in chunk:
                continue
            name, value = chunk.split("=", 1)
            fields[name.strip().lower()] = _clean_value(value)
        entries.append({"key": key, "type": etype, "fields": fields})
    return entries


# --------------------------------------------------------------- front matter
def split_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end = i
            break
    if end is None:
        return {}, text
    yaml_text = "".join(lines[1:end])
    body = "".join(lines[end + 1 :])
    data = yaml.safe_load(yaml_text) if yaml else None
    return (data or {}, body)


# ------------------------------------------------------------------- authors
def split_authors(raw):
    parts = re.split(r"\s+and\s+", raw)
    return [p.strip() for p in parts if p.strip()]


def flip_name(name):
    name = name.strip()
    if "," in name:
        last, first = name.split(",", 1)
        return (first.strip() + " " + last.strip()).strip()
    return name


def name_tokens(name):
    return sorted(set(re.findall(r"[A-Za-z0-9]+", name.lower())))


# --------------------------------------------------------------------- build
def build():
    # ---- resume ----
    resume_json = json.loads(read(os.path.join(ROOT, "data", "resume.json")))
    resume = {
        "name": resume_json.get("name", ""),
        "title": resume_json.get("title", ""),
        "affiliation": resume_json.get("affiliation", ""),
        "photo": resume_json.get("photo", ""),
        "email": resume_json.get("email", ""),
        "about": resume_json.get("about", []),
        "quick_links": resume_json.get("quick_links", []),
        "socials": resume_json.get("socials", []),
        "experience": resume_json.get("experience", []),
        "education": resume_json.get("education", []),
        "awards": resume_json.get("awards", []),
        "thesis": resume_json.get("thesis"),
    }
    me_tokens = name_tokens(resume.get("name", ""))

    # ---- publications ----
    raw_entries = parse_bib(strip_comments(read(os.path.join(ROOT, "data", "publications.bib"))))
    pubs = []
    for ent in raw_entries:
        f = ent["fields"]
        year = f.get("year", "").strip()
        try:
            year_int = int(year)
        except ValueError:
            year_int = 0
        authors_raw = split_authors(f.get("author", ""))
        authors = []
        for a in authors_raw:
            display = flip_name(a)
            authors.append({"name": display, "me": name_tokens(display) == me_tokens and bool(me_tokens)})
        venue_raw = f.get("booktitle") or f.get("journal") or f.get("venue") or ""
        venue = norm_ws(venue_raw)
        venue_has_year = bool(year and venue) and (year in venue)
        urls = {
            "paper": f.get("url") or f.get("paper") or f.get("pdf") or f.get("doi"),
            "project": f.get("project"),
            "code": f.get("code"),
            "video": f.get("video"),
            "slides": f.get("slides"),
            "supplement": f.get("supplement"),
        }
        pubs.append(
            {
                "key": ent["key"],
                "type": ent["type"],
                "title": norm_ws(f.get("title", ent["key"])),
                "authors": authors,
                "venue": venue,
                "venue_has_year": venue_has_year,
                "year": year,
                "_year": year_int,
                "month": f.get("month", ""),
                "note": f.get("note", ""),
                "doi": f.get("doi", ""),
                "preview": f.get("preview", ""),
                "urls": urls,
            }
        )

    # Group by year, newest first; keep file order within a year.
    years = sorted({p["_year"] for p in pubs if p["_year"]}, reverse=True)
    grouped = []
    for y in years:
        grouped.append({"year": str(y), "entries": [p for p in pubs if p["_year"] == y]})
    # Any entries without a usable year (shouldn't happen) still get shown.
    orphans = [p for p in pubs if p["_year"] == 0]
    if orphans:
        grouped.append({"year": "Unclassified", "entries": orphans})

    # ---- news ----
    news = []
    for path in sorted(glob.glob(os.path.join(ROOT, "news", "*.md"))):
        text = read(path)
        fm, body = split_frontmatter(text)
        date_raw = fm.get("date") or ""
        iso = str(date_raw).strip()
        title = fm.get("title") or ""
        if markdown:
            html = markdown.markdown(body, extensions=["extra", "sane_lists"])
        else:
            html = "<br>".join(p for p in [x.strip() for x in body.strip().splitlines()])
        news.append(
            {
                "date_display": fmt_date(date_raw),
                "iso": iso,
                "title": title if title != os.path.basename(path)[:-3] else "",
                "html": html,
            }
        )
    news.sort(key=lambda x: x["iso"], reverse=True)

    # ---- render ----
    env = Environment(
        loader=FileSystemLoader(os.path.join(ROOT, "templates")),
        autoescape=select_autoescape(["html", "htm"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals.get("date")  # (no-op; clarity only)
    tpl = env.get_template("site.html")

    newest = max(
        (os.path.getmtime(p) for p in (
            glob.glob(os.path.join(ROOT, "data", "*"))
            + glob.glob(os.path.join(ROOT, "news", "*.md"))
            + glob.glob(os.path.join(ROOT, "assets", "*"))
            + glob.glob(os.path.join(ROOT, "templates", "*"))
        )),
        default=os.path.getmtime(__file__),
    )
    import time

    build_date = time.strftime("%d %b %Y", time.localtime(newest))

    html = tpl.render(
        resume=resume,
        pubs=grouped,
        pub_count=len(pubs),
        news=news,
        build_date=build_date,
    )

    dist = os.path.join(ROOT, "dist")
    if os.path.isdir(os.path.join(dist, "assets")):
        shutil.rmtree(os.path.join(dist, "assets"))
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(dist, "assets"))
    write(os.path.join(dist, "index.html"), html)

    print(f"OK  Wrote {os.path.relpath(os.path.join(dist, 'index.html'), ROOT)}")
    print(f"    publications : {len(pubs)} (across {len(years)} years)")
    print(f"    news items   : {len(news)}")
    print(f"    host         : any static host (serve the 'dist' directory)")
    return 0


if __name__ == "__main__":
    sys.exit(build())
