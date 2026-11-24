#!/usr/bin/env python3
"""Export site writeups (content/posts/<slug>/index.md) back to the plain Markdown format
used by the sdt235 repo: an H1 + bold metadata lines + body, with no Hugo frontmatter or
shortcodes. The site is the source of truth; this keeps the plain repo in sync.

  export_plain.py --all                       # export every non-draft post
  export_plain.py --slug fluffy               # just one
  export_plain.py --all --out /path/to/repo   # default out: ~/htb/HTB-Writeups-sdt235

Writes <out>/<slug>-writeup.md. Drafts (e.g. fortresses) are skipped — they aren't public.
"""
import argparse
import re
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
POSTS = SITE / "content" / "posts"
DEFAULT_OUT = Path.home() / "htb" / "HTB-Writeups-sdt235"


def fm_value(block: str, key: str):
    m = re.search(rf'^\s*{re.escape(key)}\s*=\s*"(.*?)"\s*$', block, re.M)
    return m.group(1) if m else ""


def fm_list(block: str, key: str):
    m = re.search(rf'^\s*{re.escape(key)}\s*=\s*\[(.*?)\]\s*$', block, re.M)
    if not m:
        return []
    return [x.strip().strip('"') for x in m.group(1).split(",") if x.strip()]


def split_frontmatter(text: str):
    m = re.match(r"\+\+\+\s*\n(.*?)\n\+\+\+\s*\n(.*)$", text, re.S)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def export(idx: Path, out_dir: Path):
    slug = idx.parent.name
    fm, body = split_frontmatter(idx.read_text())
    if fm is None:
        print(f"  {slug}: no frontmatter, skipped")
        return False
    if re.search(r"^\s*draft\s*=\s*true", fm, re.M):
        print(f"  {slug}: draft, skipped (not public)")
        return False

    title = fm_value(fm, "title") or slug
    title = re.sub(r"^HTB(?:\s+Challenge|\s+Fortress)?:\s*", "", title)
    title = re.sub(r"\s*—\s*Writeup\s*$", "", title).strip()
    tags = fm_list(fm, "tags")
    kind = next((t for t in (tags[:1]) if t in ("machine", "challenge", "fortress")), "machine")
    os_ = fm_value(fm, "os")
    diff = fm_value(fm, "difficulty")
    tech = fm_value(fm, "techniques")
    cat = fm_value(fm, "category") or (os_ if kind == "challenge" else "")

    # body: drop a leading {{< boxinfo ... >}} line and blank lines, start at first heading
    body = re.sub(r'^\s*\{\{<\s*boxinfo.*?>\}\}\s*\n', "", body, count=1, flags=re.S).lstrip("\n")

    if kind == "challenge":
        head = [f"# HTB Challenge: {title} — Writeup", ""]
        if cat:
            head.append(f"**Category:** {cat}")
    elif kind == "fortress":
        head = [f"# HTB Fortress: {title} — Writeup (PRIVATE)", ""]
    else:
        head = [f"# HTB: {title} — Writeup", ""]
        if os_:
            head.append(f"**OS:** {os_}")
    if diff:
        head.append(f"**Difficulty:** {diff}")
    if tech:
        head.append(f"**Techniques:** {tech}")
    head += ["", "---", "", ""]

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{slug}-writeup.md"
    out.write_text("\n".join(head) + body.rstrip() + "\n")
    print(f"  {slug} -> {out}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--slug")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()
    if a.slug:
        idxs = [POSTS / a.slug / "index.md"]
    elif a.all:
        idxs = sorted(POSTS.glob("*/index.md"))
    else:
        raise SystemExit("give --all or --slug <name>")
    n = sum(export(i, a.out) for i in idxs if i.exists())
    print(f"\nexported {n} writeup(s) to {a.out}")


if __name__ == "__main__":
    main()
