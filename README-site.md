# HTB Writeups — Hugo site

This repo doubles as a Hugo site (PaperMod theme) that publishes the **retired** writeups.

## Local preview
    ~/htb/.tools/hugo server -D      # http://localhost:1313/

## Build
    ~/htb/.tools/hugo --gc --minify

## Adding / converting writeups
New writeups should carry TOML frontmatter + a `{{< boxinfo >}}` card and live at
`content/posts/<slug>/index.md`. To convert an old root-level `*-writeup.md`:
    python3 scripts/convert_writeups.py <name>-writeup.md      # one
    python3 scripts/convert_writeups.py --all                  # all

Images stay in `images/` (served at `/images/...` by the render hook) — no need to move them.

## Hosting / the site URL
`baseURL` in `hugo.toml` is only used for local builds; the GitHub Action overrides it with
the URL GitHub Pages reports, so the site works under whatever account and repo host it.
The URL is `https://<account>.github.io/HTB-Writeups/`, where `<account>` is the GitHub
account that owns the repo — this is fixed by the account name, not configurable in Hugo.

## NEVER publish private writeups
Only retired-box writeups belong here. Active-box and fortress writeups live in the separate
`HTB-private` repo and must never be added to this site — publishing them breaks HTB's rules.
