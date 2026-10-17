"""LLM extraction experiment: rebuild scene records from the Description paragraphs only, then
compare them with the hand-written records.

    python scripts/extract_scenes.py the_handmaiden

The model sees each scene's Description, the canonical character / object names from film.md, and
the Descriptions of the other scenes (so it can propose links). It never sees the Events, Objects,
Links or Interpretations you wrote. Results go to results/extraction/<film>_<time>.json and .md.

Automatic scores (precision / recall against your notes):
- characters and objects per scene, after mapping aliases to canonical names
- links at scene level: (scene, predicate, other scene)
Events are not scored automatically; the report puts both versions side by side for you to judge.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.chat_service import MODEL, _client  # noqa: E402
from app.services.scene_store import LINK_PREDICATES, SCENES_DIR, Film, Scene, load_film, scene_of  # noqa: E402

PROMPT = """You turn a viewer's description of one film scene into structured notes.
Use only what the description states. Do not add anything you know about the film from elsewhere.

Canonical character names: {characters}
Canonical object names (use them when the same thing is meant): {objects}

Other scenes of the same film, for links only:
{others}

Return JSON with exactly these keys:
{{"characters": [names], "objects": [short object names],
  "events": [{{"agent": name, "action": "what is visibly done", "objects": [names]}}],
  "links": [{{"predicate": one of {predicates}, "target": other scene id, "reason": "short"}}]}}
Link meanings: retells = the other scene shows the same event from another view; same_object = an object
here is the same physical object as there; follows_from = this scene is a consequence of the other;
contradicts = this scene shows that the other scene's version was false.
Only propose a link if the descriptions support it.

Scene {scene_id} description:
{description}
"""


def _prf(gold: set, predicted: set) -> dict:
    hit = len(gold & predicted)
    precision = hit / len(predicted) if predicted else (1.0 if not gold else 0.0)
    recall = hit / len(gold) if gold else (1.0 if not predicted else 0.0)
    return {"gold": len(gold), "predicted": len(predicted), "matched": hit,
            "precision": round(precision, 3), "recall": round(recall, 3),
            "missed": sorted(gold - predicted), "extra": sorted(predicted - gold)}


def _norm(film: Film, names: list[str]) -> set[str]:
    return {film.canonical(name).lower() for name in names if name.strip()}


def _gold_links(film: Film) -> set[tuple[str, str, str]]:
    return {(scene_of(l.source), l.predicate, scene_of(l.target)) for s in film.scenes for l in s.links}


def extract(film: Film, scene: Scene, client) -> dict:
    others = "\n".join(f"- {s.scene_id}: {s.description}" for s in film.scenes if s.scene_id != scene.scene_id)
    objects = sorted({canonical for canonical in film.names.values() if canonical not in film.characters})
    prompt = PROMPT.format(
        characters=", ".join(film.characters) or "(none listed)",
        objects=", ".join(objects) or "(none listed)",
        others=others or "(none)",
        predicates=sorted(LINK_PREDICATES),
        scene_id=scene.scene_id,
        description=scene.description,
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content or "{}")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/extract_scenes.py <film_slug>")
    film = load_film(SCENES_DIR / sys.argv[1])
    if not film.scenes:
        sys.exit("no scenes yet")
    client = _client()

    per_scene = []
    predicted_links: set[tuple[str, str, str]] = set()
    for scene in film.scenes:
        print(f"extracting {scene.scene_id} ...")
        output = extract(film, scene, client)
        for link in output.get("links", []):
            if link.get("predicate") in LINK_PREDICATES and link.get("target"):
                predicted_links.add((scene.scene_id, link["predicate"], scene_of(str(link["target"]))))
        per_scene.append({
            "scene_id": scene.scene_id,
            "characters": _prf(_norm(film, scene.characters), _norm(film, output.get("characters", []))),
            "objects": _prf(_norm(film, scene.objects), _norm(film, output.get("objects", []))),
            "gold_events": [f"{e.agent} {e.action}" for e in scene.events],
            "predicted_events": [f"{e.get('agent', '?')} {e.get('action', '')}" for e in output.get("events", [])],
            "raw": output,
        })

    links = _prf({"|".join(t) for t in _gold_links(film)}, {"|".join(t) for t in predicted_links})
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_dir = ROOT / "results" / "extraction"
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / f"{film.slug}_{stamp}"
    base.with_suffix(".json").write_text(
        json.dumps({"film": film.title, "model": MODEL, "links": links, "scenes": per_scene}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def mean(key: str, metric: str) -> float:
        return round(sum(s[key][metric] for s in per_scene) / len(per_scene), 3)

    lines = [f"# Extraction vs hand-written notes: {film.title}", "", f"Model: {MODEL}. Input: Description paragraphs only.", "",
             "| | precision | recall |", "|---|---|---|",
             f"| characters (mean per scene) | {mean('characters', 'precision')} | {mean('characters', 'recall')} |",
             f"| objects (mean per scene) | {mean('objects', 'precision')} | {mean('objects', 'recall')} |",
             f"| links (scene level, whole film) | {links['precision']} | {links['recall']} |", "",
             f"Links missed: {links['missed'] or 'none'}", f"Links invented: {links['extra'] or 'none'}", ""]
    for scene in per_scene:
        lines += [f"## {scene['scene_id']}", "",
                  f"Objects missed: {scene['objects']['missed'] or 'none'}; extra: {scene['objects']['extra'] or 'none'}", "",
                  "| your events | extracted events | judgement (fill in: matched / missed / invented / wrong) |", "|---|---|---|"]
        rows = max(len(scene["gold_events"]), len(scene["predicted_events"]))
        for i in range(rows):
            gold = scene["gold_events"][i] if i < len(scene["gold_events"]) else ""
            pred = scene["predicted_events"][i] if i < len(scene["predicted_events"]) else ""
            lines.append(f"| {gold} | {pred} | |")
        lines.append("")
    base.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:12]))
    print(f"\nwrote {base.with_suffix('.json').relative_to(ROOT)} and {base.with_suffix('.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
