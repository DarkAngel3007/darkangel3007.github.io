#!/usr/bin/env python3
"""Convert a root-level <box>-writeup.md into a Hugo page under content/posts/.

These writeups open with an H1 (`# HTB: Fluffy — Writeup`) and bold metadata lines
(`**Difficulty:** ...`, `**OS:** ...`, `**Techniques:** ...`) rather than the YAML/TOML
frontmatter Hugo needs. This reads those fields, emits TOML frontmatter + a {{< boxinfo >}}
card, and writes the body (from the first `##` heading on) to content/posts/<slug>/index.md.
Images are left as `images/...` refs — the render hook resolves them.

  convert_writeups.py fluffy-writeup.md [more.md ...]     # convert specific files
  convert_writeups.py --all                               # every *-writeup.md at repo root
  convert_writeups.py --all --force                       # overwrite existing output

Non-destructive: the source files are left in place.
"""
import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BOLD = re.compile(r"^\*\*(?P<k>[A-Za-z ]+):\*\*\s*(?P<v>.+?)\s*$")


def git_added_date(path: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "log", "--diff-filter=A", "--follow",
             "--format=%aI", "--", path.name],
            capture_output=True, text=True, timeout=10).stdout.strip().splitlines()
        if out:
            return out[-1]
    except Exception:
        pass
    return dt.datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")


def parse(path: Path):
    lines = path.read_text().splitlines()
    title, meta, body_start = None, {}, 0
    for i, ln in enumerate(lines):
        if title is None and ln.startswith("# "):
            title = ln[2:].strip()
            continue
        m = BOLD.match(ln)
        if m:
            meta[m.group("k").strip().lower()] = m.group("v").strip()
            continue
        if ln.startswith("## "):        # body starts at the first section
            body_start = i
            break
    body = "\n".join(lines[body_start:]).strip() + "\n"
    return title, meta, body


def toml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def classify(name: str, meta: dict):
    """Return (kind, slug). Challenges are named rev_/crypto_/... ; everything else a machine."""
    base = name[: -len("-writeup.md")] if name.endswith("-writeup.md") else name
    kind = "machine"
    # the Techniques/Category wording or filename rarely says 'challenge'; infer from category key
    if "category" in meta or base.split("_", 1)[0] in {
            "rev", "crypto", "pwn", "web", "forensics", "misc", "mobile", "osint",
            "hardware", "blockchain", "stego", "ics", "coding"}:
        kind = "challenge"
    return kind, base.lower().replace(" ", "-")


def convert(path: Path, force: bool):
    title, meta, body = parse(path)
    if not title:
        print(f"  skip {path.name}: no H1 title found")
        return False
    kind, slug = classify(path.name, meta)
    display = re.sub(r"^HTB:\s*", "", title)
    display = re.sub(r"\s*—\s*Writeup\s*$", "", display).strip()

    os_ = meta.get("os", "")
    diff = meta.get("difficulty", "")
    tech = meta.get("techniques", "")
    tags = [kind]
    for t in (os_.split("(")[0].strip(), diff):
        if t and t.lower() not in [x.lower() for x in tags]:
            tags.append(t)

    date = git_added_date(path)
    fm = [
        "+++",
        f'title = "{toml_escape(display)}"',
        f"date = {date}",
        "draft = false",
        f"tags = [{', '.join(chr(34) + toml_escape(t) + chr(34) for t in tags)}]",
        f'categories = ["HTB"]',
        "[params]",
        f'  os = "{toml_escape(os_)}"',
        f'  difficulty = "{toml_escape(diff)}"',
        f'  techniques = "{toml_escape(tech)}"',
        "+++",
        "",
    ]
    box = ['{{< boxinfo'
           + (f' os="{toml_escape(os_)}"' if os_ else "")
           + (f' difficulty="{toml_escape(diff)}"' if diff else "")
           + (f' type="{kind.title()}"')
           + (f' techniques="{toml_escape(tech)}"' if tech else "")
           + ' >}}', ""]
    out_dir = REPO / "content" / "posts" / slug
    out = out_dir / "index.md"
    if out.exists() and not force:
        print(f"  exists, skip (use --force): {out.relative_to(REPO)}")
        return False
    out_dir.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(fm) + "\n".join(box) + "\n" + body)
    print(f"  {path.name} -> {out.relative_to(REPO)}  [{kind}, tags={tags}]")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    files = ([p for p in REPO.glob("*-writeup.md")] if a.all
             else [Path(f) if Path(f).is_absolute() else REPO / f for f in a.files])
    if not files:
        sys.exit("nothing to convert (give filenames or --all)")
    n = 0
    for f in files:
        if not f.exists():
            print(f"  missing: {f}")
            continue
        n += convert(f, a.force)
    print(f"\nconverted {n} file(s)")


if __name__ == "__main__":
    main()
