"""
Build a small film knowledge graph from the markdown files in data/rag/.

Only the structured parts of the documents are parsed:
- the "Basic Information" bullet list of each film page
- the filmography, screenwriting, producer and collaborator lists on the director page
- the "Representative Films" list on the film noir page

Plot, theme and analysis paragraphs are not turned into triples; they stay in the
vector RAG index. The field-to-predicate mapping below is written by hand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAG_DIR = PROJECT_ROOT / "data" / "rag"

# Basic Information field name (lowercased) -> predicate.
FIELD_PREDICATES = {
    "director": "directed_by",
    "screenwriters": "written_by",
    "writer": "written_by",
    "producer": "produced_by",
    "producers": "produced_by",
    "music": "music_by",
    "music composer": "music_by",
    "cinematography": "cinematography_by",
    "editing": "edited_by",
    "production company": "production_company",
    "production companies": "production_company",
    "distributor": "distributed_by",
    "distributors": "distributed_by",
    "lead cast": "stars",
    "starring": "stars",
    "supporting cast": "stars",
    "genre": "has_genre",
    "languages": "in_language",
    "original language": "in_language",
    "adapted from": "adapted_from",
}

# Spelling variants found across the documents -> canonical name.
# These were merged because the spellings are close; verify before relying on them.
ALIASES = {
    "Jo Yeong-wook": "Cho Young-wuk",
    "Jeong Seo-kyeong": "Jeong Seo-kyung",
    "Lady Vengeance": "Sympathy for Lady Vengeance",
    "Joint Security Area (JSA)": "Joint Security Area",
}

INVISIBLE = re.compile(r"[​‌‍﻿]")
H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
SECTION = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
YEAR_ITEM = re.compile(r"^-\s*(\d{4}):\s*(.+?)\s*$")
TITLE_YEAR = re.compile(r"^(.+?)\s*\((\d{4})\)\s*$")


@dataclass(frozen=True)
class Triple:
    subject: str
    predicate: str
    object: str
    source: str


def _clean(text: str) -> str:
    text = INVISIBLE.sub("", text)
    text = text.replace("*", "").strip()
    return ALIASES.get(text, text)


def _strip_parenthetical(text: str) -> tuple[str, str | None]:
    match = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return text.strip(), None


def _sections(text: str) -> dict[str, str]:
    """Map lowercased '## heading' -> body text until the next '## heading'."""
    matches = list(SECTION.finditer(text))
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        heading = _clean(match.group(1)).rstrip(":").lower()
        sections[heading] = text[match.end() : end]
    return sections


def _film_title(text: str) -> str:
    match = H1.search(text)
    title = INVISIBLE.sub("", match.group(1)) if match else ""
    # Headings such as "Stoker（2016）" use full-width brackets.
    title = re.sub(r"[（(]\s*\d{4}\s*[）)]", "", title)
    return _clean(title)


def _info_fields(body: str) -> list[tuple[str, list[str]]]:
    """Parse '* field: a, b' bullets, including indented sub-bullets."""
    fields: list[tuple[str, list[str]]] = []
    for raw in body.splitlines():
        line = INVISIBLE.sub("", raw)
        if not line.strip().startswith("*"):
            continue
        content = line.strip()[1:].strip()
        if line.startswith((" ", "\t")) and fields:
            fields[-1][1].append(content)
            continue
        if ":" not in content:
            continue
        name, value = content.split(":", 1)
        values = [value] if value.strip() else []
        fields.append((name.replace("*", "").strip().lower(), values))
    return fields


def _split_values(values: list[str]) -> list[str]:
    parts: list[str] = []
    for value in values:
        parts.extend(piece for piece in re.split(r",\s*", value) if piece.strip())
    return parts


def _person_and_role(value: str) -> tuple[str, str | None]:
    """'Tang Wei (as Seo-rae)' or 'Mia Wasikowska as India Stoker' -> (person, role)."""
    name, note = _strip_parenthetical(value)
    if note and note.startswith("as "):
        return _clean(name), _clean(note[3:])
    if " as " in value:
        name, role = value.split(" as ", 1)
        return _clean(name), _clean(role)
    return _clean(name), None


def _parse_film_page(path: Path, text: str) -> list[Triple]:
    film = _film_title(text)
    info = _sections(text).get("basic information", "")
    triples: list[Triple] = []
    for field, values in _info_fields(info):
        predicate = FIELD_PREDICATES.get(field)
        if predicate is None:
            continue
        if predicate == "adapted_from":
            # "Sarah Waters’s novel Fingersmith (2002)"
            match = re.match(r"^(.+?)[’']s novel (.+?)\s*\((\d{4})\)", values[0].strip())
            if match:
                author, novel, year = (_clean(g) for g in match.groups())
                triples.append(Triple(film, "adapted_from", novel, path.name))
                triples.append(Triple(novel, "written_by", author, path.name))
                triples.append(Triple(novel, "release_year", year, path.name))
            continue
        for value in _split_values(values):
            if predicate == "stars":
                person, role = _person_and_role(value)
                triples.append(Triple(film, "stars", person, path.name))
                if role:
                    triples.append(Triple(person, "plays", role, path.name))
                continue
            name, _ = _strip_parenthetical(value)
            triples.append(Triple(film, predicate, _clean(name), path.name))
    return triples


def _parse_director_page(path: Path, text: str) -> list[Triple]:
    person = _film_title(text)
    sections = _sections(text)
    triples: list[Triple] = []

    list_sections = {
        "major works (director)": "directed",
        "screenwriting credits": "wrote",
        "producer roles": "produced",
    }
    for heading, relation in list_sections.items():
        for raw in sections.get(heading, "").splitlines():
            line = INVISIBLE.sub("", raw).strip()
            match = YEAR_ITEM.match(line)
            if match:
                year, title = match.group(1), match.group(2)
            else:
                match = TITLE_YEAR.match(line.lstrip("- "))
                if not line.startswith("-") or not match:
                    continue
                title, year = match.group(1), match.group(2)
            title, _ = _strip_parenthetical(title)
            title = _clean(title)
            if relation == "directed":
                triples.append(Triple(title, "directed_by", person, path.name))
            elif relation == "wrote":
                triples.append(Triple(title, "written_by", person, path.name))
            else:
                triples.append(Triple(title, "produced_by", person, path.name))
            triples.append(Triple(title, "release_year", year, path.name))

    for raw in sections.get("key collaborators", "").splitlines():
        line = INVISIBLE.sub("", raw).strip()
        match = re.match(r"^\*\s*(Screenwriter|Composer)\s+([^:]+):", line)
        if match:
            triples.append(Triple(person, "collaborates_with", _clean(match.group(2)), path.name))
    return triples


def _parse_genre_page(path: Path, text: str) -> list[Triple]:
    genre = _film_title(text)
    body = next(
        (value for key, value in _sections(text).items() if key.startswith("representative films")),
        "",
    )
    triples: list[Triple] = []
    film: str | None = None
    for raw in body.splitlines():
        line = INVISIBLE.sub("", raw)
        if line.startswith("* "):
            match = TITLE_YEAR.match(line[2:].strip())
            film = _clean(match.group(1)) if match else None
            if film:
                triples.append(Triple(film, "has_genre", genre, path.name))
                triples.append(Triple(film, "release_year", match.group(2), path.name))
            continue
        if film is None or ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        if field == "Director":
            triples.append(Triple(film, "directed_by", _clean(value), path.name))
        elif field == "Stars":
            for star in _split_values([value]):
                triples.append(Triple(film, "stars", _clean(star), path.name))
    return triples


def build_triples(rag_dir: Path = RAG_DIR) -> list[Triple]:
    triples: list[Triple] = []
    for path in sorted(rag_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        sections = _sections(text)
        if "major works (director)" in sections:
            triples.extend(_parse_director_page(path, text))
        elif any(key.startswith("representative films") for key in sections):
            triples.extend(_parse_genre_page(path, text))
        elif "basic information" in sections:
            triples.extend(_parse_film_page(path, text))

    unique: dict[tuple[str, str, str], Triple] = {}
    for triple in triples:
        unique.setdefault((triple.subject, triple.predicate, triple.object), triple)
    return list(unique.values())
