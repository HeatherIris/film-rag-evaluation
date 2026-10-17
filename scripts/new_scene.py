"""Create data/scenes/<film>/<scene_id>.md from the template.

    python scripts/new_scene.py the_handmaiden s01
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data" / "scenes" / "_template" / "scene.md"


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: python scripts/new_scene.py <film_slug> <scene_id like s01>")
    film, scene_id = sys.argv[1], sys.argv[2]
    directory = ROOT / "data" / "scenes" / film
    if not (directory / "film.md").exists():
        sys.exit(f"{directory}/film.md not found; copy data/scenes/_template/film.md there first")
    target = directory / f"{scene_id}.md"
    if target.exists():
        sys.exit(f"{target.relative_to(ROOT)} already exists")
    text = TEMPLATE.read_text(encoding="utf-8").replace("scene_id: s01", f"scene_id: {scene_id}", 1)
    target.write_text(text, encoding="utf-8")
    print(f"created {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
