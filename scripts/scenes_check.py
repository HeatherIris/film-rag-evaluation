"""Validate the scene notes and export them to results/scenes_<film>.json. No API key needed.

    python scripts/scenes_check.py                  # every film in data/scenes/
    python scripts/scenes_check.py the_handmaiden   # one film
    python scripts/scenes_check.py --show s03       # also print how a scene is given to the model

Exit code 1 if any problem is found, so it can run before every commit.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.scene_store import SCENES_DIR, SceneFormatError, load_film, render_scene, to_dict, validate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("films", nargs="*", help="film directory names under data/scenes/")
    parser.add_argument("--show", action="append", default=[], help="scene id to print as the model sees it")
    args = parser.parse_args()

    names = args.films or sorted(p.name for p in SCENES_DIR.iterdir() if p.is_dir() and not p.name.startswith("_"))
    failed = False
    for name in names:
        try:
            film = load_film(SCENES_DIR / name)
        except SceneFormatError as exc:
            print(f"FORMAT ERROR {exc}")
            failed = True
            continue

        events = sum(len(scene.events) for scene in film.scenes)
        links = [link for scene in film.scenes for link in scene.links]
        claims = sum(len(scene.claims) for scene in film.scenes)
        verified = sum(scene.verified for scene in film.scenes)
        print(f"== {film.title} ({name})")
        print(f"   scenes {len(film.scenes)} (verified {verified}), events {events}, links {len(links)}, interpretations {claims}")
        if links:
            print("   links by type: " + ", ".join(f"{k} {v}" for k, v in Counter(l.predicate for l in links).items()))
        unverified_links = sum(not link.verified for link in links)
        if unverified_links:
            print(f"   unverified links: {unverified_links}")

        problems = validate(film)
        for problem in problems:
            print(f"   PROBLEM {problem}")
        failed = failed or bool(problems)

        for scene_id in args.show:
            scene = film.scene(scene_id)
            if scene:
                print("\n" + render_scene(scene, film) + "\n")

        if not film.scenes:
            continue
        out = ROOT / "results" / f"scenes_{name}.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(to_dict(film), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   exported {out.relative_to(ROOT)}")

    if failed:
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
