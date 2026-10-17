"""
Load hand-written scene notes from data/scenes/<film_slug>/.

Each film directory holds:
- film.md: the film title and the canonical character / object names with aliases
- one sNN.md file per scene, written from data/scenes/_template/scene.md

The markdown files are the source of truth. scripts/scenes_check.py validates them and
exports results/scenes_<slug>.json; nothing here calls an LLM.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCENES_DIR = PROJECT_ROOT / "data" / "scenes"

LINK_PREDICATES = {"retells", "same_object", "follows_from", "contradicts"}
SCENE_ID = re.compile(r"^s\d{2,3}$")
EVENT_ID = re.compile(r"^e\d+$")
CLAIM_ID = re.compile(r"^c\d+$")
TIME = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")
HEADING = re.compile(r"^##\s+(.+?)\s*$")


@dataclass
class Event:
    id: str
    agent: str
    action: str
    objects: list[str] = field(default_factory=list)
    uncertain: bool = False


@dataclass
class Link:
    source: str  # "s03" or "s03.e1"
    predicate: str
    target: str
    verified: bool = True
    note: str = ""


@dataclass
class Claim:
    id: str
    attributed_to: str
    text: str
    supports: list[str] = field(default_factory=list)


@dataclass
class Scene:
    scene_id: str
    part: str = ""
    start: str = ""
    end: str = ""
    pov: str = ""
    location: str = ""
    verified: bool = False
    verified_on: str = ""
    description: str = ""
    characters: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    objects: list[str] = field(default_factory=list)
    dialogue: str = ""
    camera: str = ""
    claims: list[Claim] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    path: str = ""


@dataclass
class Film:
    slug: str
    title: str
    # alias (lowercased) -> canonical name, canonical names included
    names: dict[str, str] = field(default_factory=dict)
    characters: list[str] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)

    def scene(self, scene_id: str) -> Scene | None:
        return next((scene for scene in self.scenes if scene.scene_id == scene_id), None)

    def canonical(self, name: str) -> str:
        return self.names.get(name.strip().lower(), name.strip())


class SceneFormatError(ValueError):
    pass


def _front_matter(text: str, path: Path) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SceneFormatError(f"{path}: file must start with a '---' front-matter block")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration as exc:
        raise SceneFormatError(f"{path}: front-matter block is not closed with '---'") from exc
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise SceneFormatError(f"{path}: front-matter line has no ':' -> {line!r}")
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip()
    return meta, "\n".join(lines[end + 1 :])


def _sections(body: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in body.splitlines():
        match = HEADING.match(line)
        if match:
            current = sections.setdefault(match.group(1).strip().lower(), [])
            continue
        if current is not None:
            current.append(line)
    return sections


def _strip_comments(lines: list[str]) -> list[str]:
    text = re.sub(r"<!--.*?-->", "", "\n".join(lines), flags=re.DOTALL)
    return text.splitlines()


def _bullets(lines: list[str]) -> list[str]:
    return [line.strip()[2:].strip() for line in _strip_comments(lines) if line.strip().startswith("- ")]


def _prose(lines: list[str]) -> str:
    return " ".join(line.strip() for line in _strip_comments(lines) if line.strip()).strip()


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_event(line: str, path: Path) -> Event:
    # e1 | Agent | what is done | objects: a, b | uncertain
    parts = [part.strip() for part in line.split("|")]
    if len(parts) < 3:
        raise SceneFormatError(f"{path}: event needs 'id | agent | action' -> {line!r}")
    event = Event(id=parts[0], agent=parts[1], action=parts[2])
    for extra in parts[3:]:
        if extra.lower().startswith("objects:"):
            event.objects = _split_list(extra.split(":", 1)[1])
        elif extra.lower() == "uncertain":
            event.uncertain = True
        elif extra:
            raise SceneFormatError(f"{path}: unknown event field {extra!r} in {line!r}")
    return event


def _parse_claim(line: str, path: Path) -> Claim:
    # c1 | attributed to | claim text | supports: s03.e1, s21.e2
    parts = [part.strip() for part in line.split("|")]
    if len(parts) < 3:
        raise SceneFormatError(f"{path}: claim needs 'id | attributed to | text' -> {line!r}")
    claim = Claim(id=parts[0], attributed_to=parts[1], text=parts[2])
    for extra in parts[3:]:
        if extra.lower().startswith("supports:"):
            claim.supports = _split_list(extra.split(":", 1)[1])
        elif extra:
            raise SceneFormatError(f"{path}: unknown claim field {extra!r} in {line!r}")
    return claim


def _parse_link(line: str, scene_id: str, path: Path) -> Link:
    # e1 retells s21.e2 | unverified | note: ...
    parts = [part.strip() for part in line.split("|")]
    words = parts[0].split()
    if len(words) != 3:
        raise SceneFormatError(f"{path}: link needs 'source predicate target' -> {line!r}")
    source, predicate, target = words
    if source in ("scene", scene_id):
        source = scene_id
    elif not source.startswith(f"{scene_id}."):
        source = f"{scene_id}.{source}"
    link = Link(source=source, predicate=predicate, target=target)
    for extra in parts[1:]:
        if extra.lower() == "unverified":
            link.verified = False
        elif extra.lower().startswith("note:"):
            link.note = extra.split(":", 1)[1].strip()
        elif extra:
            raise SceneFormatError(f"{path}: unknown link field {extra!r} in {line!r}")
    return link


def parse_scene(path: Path) -> Scene:
    meta, body = _front_matter(path.read_text(encoding="utf-8"), path)
    sections = _sections(body)
    scene_id = meta.get("scene_id", path.stem)
    scene = Scene(
        scene_id=scene_id,
        part=meta.get("part", ""),
        start=meta.get("start", ""),
        end=meta.get("end", ""),
        pov=meta.get("pov", ""),
        location=meta.get("location", ""),
        verified=meta.get("verified", "no").lower() in ("yes", "true"),
        verified_on=meta.get("verified_on", ""),
        description=_prose(sections.get("description", [])),
        characters=_bullets(sections.get("characters", [])),
        objects=_bullets(sections.get("objects", [])),
        dialogue=_prose(sections.get("dialogue summary", [])),
        camera=_prose(sections.get("camera", [])),
        path=str(path.relative_to(PROJECT_ROOT)) if path.is_relative_to(PROJECT_ROOT) else str(path),
    )
    scene.events = [_parse_event(line, path) for line in _bullets(sections.get("events", []))]
    scene.claims = [_parse_claim(line, path) for line in _bullets(sections.get("interpretations", []))]
    scene.links = [_parse_link(line, scene_id, path) for line in _bullets(sections.get("links", []))]
    return scene


def parse_film_file(path: Path, slug: str) -> Film:
    meta, body = _front_matter(path.read_text(encoding="utf-8"), path)
    film = Film(slug=slug, title=meta.get("film", slug))
    sections = _sections(body)
    for heading in ("characters", "objects"):
        for line in _bullets(sections.get(heading, [])):
            canonical, _, aliases = (part.strip() for part in line.partition("|"))
            if heading == "characters":
                film.characters.append(canonical)
            film.names[canonical.lower()] = canonical
            for alias in _split_list(aliases):
                film.names[alias.lower()] = canonical
    return film


def load_film(directory: Path) -> Film:
    film_file = directory / "film.md"
    if not film_file.exists():
        raise SceneFormatError(f"{directory}: missing film.md")
    film = parse_film_file(film_file, directory.name)
    film.scenes = [parse_scene(path) for path in sorted(directory.glob("s*.md"))]
    _canonicalize(film)
    return film


def _canonicalize(film: Film) -> None:
    for scene in film.scenes:
        scene.characters = [film.canonical(name) for name in scene.characters]
        scene.objects = [film.canonical(name) for name in scene.objects]
        if scene.pov:
            scene.pov = film.canonical(scene.pov)
        for event in scene.events:
            event.agent = film.canonical(event.agent)
            event.objects = [film.canonical(name) for name in event.objects]


def load_films(root: Path = SCENES_DIR) -> list[Film]:
    if not root.is_dir():
        return []
    return [load_film(path) for path in sorted(root.iterdir()) if path.is_dir() and not path.name.startswith("_")]


def validate(film: Film) -> list[str]:
    """Return human-readable problems. An empty list means the notes are consistent."""
    problems: list[str] = []
    seen: dict[str, str] = {}
    event_ids: set[str] = set()
    for scene in film.scenes:
        where = scene.path or scene.scene_id
        if not SCENE_ID.match(scene.scene_id):
            problems.append(f"{where}: scene_id {scene.scene_id!r} should look like s03")
        if scene.scene_id in seen:
            problems.append(f"{where}: scene_id {scene.scene_id} also used in {seen[scene.scene_id]}")
        seen[scene.scene_id] = where
        for key in ("start", "end"):
            value = getattr(scene, key)
            if value and not TIME.match(value):
                problems.append(f"{where}: {key} {value!r} should look like 00:18:00")
        if not scene.description:
            problems.append(f"{where}: Description is empty")
        if not scene.events:
            problems.append(f"{where}: no Events")
        if scene.verified and not scene.verified_on:
            problems.append(f"{where}: verified: yes but no verified_on date")
        known_names = set(scene.characters) | set(film.characters)
        ids_here: set[str] = set()
        for event in scene.events:
            if not EVENT_ID.match(event.id):
                problems.append(f"{where}: event id {event.id!r} should look like e1")
            if event.id in ids_here:
                problems.append(f"{where}: duplicate event id {event.id}")
            ids_here.add(event.id)
            event_ids.add(f"{scene.scene_id}.{event.id}")
            if event.agent not in known_names and event.agent.lower() not in ("unknown", "none"):
                problems.append(f"{where}: event {event.id} agent {event.agent!r} is not in Characters or film.md")
            for obj in event.objects:
                if obj not in scene.objects:
                    problems.append(f"{where}: event {event.id} object {obj!r} is not listed under Objects")
        for claim in scene.claims:
            if not CLAIM_ID.match(claim.id):
                problems.append(f"{where}: claim id {claim.id!r} should look like c1")
            if not claim.supports:
                problems.append(f"{where}: claim {claim.id} has no 'supports:' evidence")

    scene_ids = set(seen)
    for scene in film.scenes:
        where = scene.path or scene.scene_id
        for link in scene.links:
            if link.predicate not in LINK_PREDICATES:
                problems.append(f"{where}: link predicate {link.predicate!r} not in {sorted(LINK_PREDICATES)}")
            for ref in (link.source, link.target):
                if not _ref_exists(ref, scene_ids, event_ids):
                    problems.append(f"{where}: link refers to unknown {ref!r}")
        for claim in scene.claims:
            for ref in claim.supports:
                if not _ref_exists(ref, scene_ids, event_ids):
                    problems.append(f"{where}: claim {claim.id} cites unknown {ref!r}")
    return problems


def _ref_exists(ref: str, scene_ids: set[str], event_ids: set[str]) -> bool:
    return ref in event_ids if "." in ref else ref in scene_ids


def all_links(film: Film) -> list[Link]:
    return [link for scene in film.scenes for link in scene.links]


def scene_of(ref: str) -> str:
    return ref.split(".", 1)[0]


def render_scene(scene: Scene, film: Film, include_claims: bool = True) -> str:
    """Plain-text view of one scene, used as evidence in prompts."""
    header = f"[{film.title} / {scene.scene_id}]"
    when = f" {scene.start}-{scene.end}" if scene.start else ""
    lines = [f"{header} part {scene.part or '?'}{when}, point of view: {scene.pov or 'n/a'}, location: {scene.location or 'n/a'}"]
    if not scene.verified:
        lines.append("(notes not yet verified against the film)")
    lines.append(f"Description: {scene.description}")
    if scene.characters:
        lines.append(f"Characters: {', '.join(scene.characters)}")
    for event in scene.events:
        objects = f" [objects: {', '.join(event.objects)}]" if event.objects else ""
        flag = " (uncertain)" if event.uncertain else ""
        lines.append(f"- {scene.scene_id}.{event.id}: {event.agent} {event.action}{objects}{flag}")
    if scene.dialogue:
        lines.append(f"Dialogue (paraphrase): {scene.dialogue}")
    if scene.camera:
        lines.append(f"Camera: {scene.camera}")
    for link in scene.links:
        flag = "" if link.verified else " (unverified link)"
        note = f" - {link.note}" if link.note else ""
        lines.append(f"Link: {link.source} --{link.predicate}--> {link.target}{flag}{note}")
    if include_claims:
        for claim in scene.claims:
            lines.append(
                f"Interpretation {scene.scene_id}.{claim.id} ({claim.attributed_to}): {claim.text} "
                f"[supported by {', '.join(claim.supports)}]"
            )
    return "\n".join(lines)


def to_dict(film: Film) -> dict:
    return {
        "slug": film.slug,
        "title": film.title,
        "characters": film.characters,
        "names": film.names,
        "scenes": [asdict(scene) for scene in film.scenes],
    }
