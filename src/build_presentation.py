"""Build the web version of the Kanda Code slide deck.

Reads the 19 slide files in presentation/slides/ (one 1920x1080 <section> per file, order in deck.json),
inlines them into presentation/player_template.html, points every figure at outputs/figures/ and writes
a self-contained static site to presentation/web/ (index.html + assets/). GitHub Pages serves that folder.

Run from the repository root:  python src/build_presentation.py
Preview locally:              python -m http.server -d presentation/web 8000   ->  http://localhost:8000
"""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRES = ROOT / "presentation"
SLIDES = PRES / "slides"
TEMPLATE = PRES / "player_template.html"
OUT = PRES / "web"
FIGURES = ROOT / "outputs" / "figures"

REPO_URL = "https://github.com/23f2003700/Kanda-Code"
VIDEO_URL = "https://www.youtube.com/watch?v=mao4kfn39vw"

IMG_SRC = re.compile(r'src="project/ds/kc/([^"]+)"')
ASIDE = re.compile(r"<aside[^>]*>(.*?)</aside>", re.S)
HEADING = re.compile(r"<h[12][^>]*>(.*?)</h[12]>", re.S)
TAG = re.compile(r"<[^>]+>")


def text_of(fragment: str) -> str:
    return " ".join(html.unescape(TAG.sub(" ", fragment)).split())


def main() -> None:
    deck = json.loads((SLIDES / "deck.json").read_text(encoding="utf-8"))
    order: list[str] = deck["order"]

    # Section (presenter) for each slide: a section runs from its start slide to the next section's start.
    starts = {v["start"]: v["description"] for v in deck.get("sections", {}).values()}
    speaker, section = "", ""

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets" / "figures").mkdir(parents=True)

    parts, meta, used = [], [], set()
    for sid in order:
        src = (SLIDES / f"{sid}.html").read_text(encoding="utf-8").strip()
        if not src.startswith(f'<section id="{sid}"'):
            raise SystemExit(f"{sid}.html must contain exactly one <section id=\"{sid}\">")
        if sid in starts:
            speaker, _, section = starts[sid].partition(" — ")
        for name in IMG_SRC.findall(src):
            if not (FIGURES / name).exists():
                raise SystemExit(f"{sid}: figure {name} not found in outputs/figures/")
            used.add(name)
        src = IMG_SRC.sub(r'src="assets/figures/\1" loading="eager" decoding="async"', src)
        notes = ASIDE.search(src)
        title = HEADING.search(src)
        meta.append({
            "id": sid,
            "title": text_of(title.group(1)) if title else sid,
            "speaker": speaker,
            "section": section[:1].upper() + section[1:] if section else "",
            "notes": text_of(notes.group(1)) if notes else "",
        })
        parts.append(src)

    for name in sorted(used):
        shutil.copy2(FIGURES / name, OUT / "assets" / "figures" / name)

    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("<!--SLIDES-->", "\n".join(parts))
    page = page.replace("__META__", json.dumps(meta, ensure_ascii=False).replace("</", "<\\/"))
    page = page.replace("__REPO__", REPO_URL).replace("__VIDEO__", VIDEO_URL)
    page = page.replace("1 / 19", f"1 / {len(order)}").replace("19 slides", f"{len(order)} slides")
    (OUT / "index.html").write_text(page, encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    cover = PRES / "cover.png"  # optional social-preview image (screenshot of slide 1)
    if cover.exists():
        shutil.copy2(cover, OUT / "assets" / "cover.png")

    total = sum(len(m["notes"].split()) for m in meta)
    print(f"wrote {OUT.relative_to(ROOT)}/index.html: {len(order)} slides, {len(used)} figures, "
          f"{total} words of speaker notes (~{total / 150:.1f} min at 150 wpm)")


if __name__ == "__main__":
    main()
