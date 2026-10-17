import types

from app.services.scene_store import load_film, parse_scene, render_scene, validate
from tests.conftest import FIXTURE_SCENES

QUESTION = "Where did the letter that Mara finds at the end first appear?"


def test_parse_and_aliases():
    film = load_film(FIXTURE_SCENES / "demo_film")
    assert [s.scene_id for s in film.scenes] == ["s01", "s02", "s03"]
    s01 = film.scene("s01")
    # "Jonathan" and "note" are aliases in film.md
    assert s01.characters == ["Jon"]
    assert s01.events[0].agent == "Jon"
    assert s01.events[0].objects == ["letter", "red book"]
    s03 = film.scene("s03")
    assert s03.events[1].uncertain
    assert [(l.source, l.predicate, l.target) for l in s03.links] == [
        ("s03.e1", "same_object", "s01.e1"),
        ("s03", "follows_from", "s01"),
    ]
    assert s03.claims[0].supports == ["s03.e2", "s01.e1"]
    assert validate(film) == []
    text = render_scene(s03, film)
    assert "s03.e1: Mara finds a letter" in text and "(uncertain)" in text and "Interpretation s03.c1" in text


def test_validate_reports_problems(tmp_path):
    (tmp_path / "film.md").write_text("---\nfilm: X\n---\n## Characters\n- Ann\n", encoding="utf-8")
    (tmp_path / "s01.md").write_text(
        "---\nscene_id: s01\nstart: 5 min\nverified: yes\n---\n"
        "## Description\nAnn leaves.\n## Events\n- e1 | Bob | leaves | objects: key\n"
        "## Links\n- e1 retells s09.e1\n- e1 resembles s01\n"
        "## Interpretations\n- c1 | me | it is sad\n",
        encoding="utf-8",
    )
    problems = "\n".join(validate(load_film(tmp_path)))
    for expected in ["start '5 min'", "no verified_on", "agent 'Bob'", "object 'key'", "unknown 's09.e1'", "'resembles'", "no 'supports:'"]:
        assert expected in problems, expected


def test_template_parses():
    from app.services.scene_store import PROJECT_ROOT

    scene = parse_scene(PROJECT_ROOT / "data" / "scenes" / "_template" / "scene.md")
    assert scene.links == [] and scene.claims == []  # examples live in comments only


def test_graph_finds_linked_scene_that_vector_misses(demo_scenes):
    from app.services.scene_retrieval import retrieve_scenes_graph, retrieve_scenes_vector, retrieved_scene_ids

    vector = retrieved_scene_ids(retrieve_scenes_vector(QUESTION, top_k=1))
    assert vector == ["s03"]
    graph = retrieve_scenes_graph(QUESTION)
    ids = retrieved_scene_ids(graph)
    assert ids[0] == "s03" and "s01" in ids
    s01 = next(s for s in graph if s.filename.endswith("/s01"))
    assert "retrieved because" in s01.chunk


def test_scene_modes_through_evaluation_api(demo_scenes, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.services import chat_service

    prompts = []

    class Completions:
        def create(self, model, messages, **kwargs):
            prompts.append(messages[0]["content"])
            message = types.SimpleNamespace(content="Observed in the film: ... (s01.e1)", tool_calls=None)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    monkeypatch.setattr(chat_service, "_client", lambda: types.SimpleNamespace(chat=types.SimpleNamespace(completions=Completions())))
    response = TestClient(app).post(
        "/api/evaluation/compare",
        json={"question": QUESTION, "modes": ["scene_vector", "scene_graph", "scene_full"]},
    )
    assert response.status_code == 200
    results = {r["mode"]: r for r in response.json()["results"]}
    assert all(r["error"] is None for r in results.values()), results
    full_ids = [s["filename"] for s in results["scene_full"]["sources"] if s["filename"].startswith("scenes/")]
    assert full_ids == ["scenes/demo_film/s01", "scenes/demo_film/s02", "scenes/demo_film/s03"]
    assert all("Observed in the film" in p and "Not covered" in p for p in prompts)
    # scene_graph also gets the metadata graph block (empty here: the demo film is not in it)
    assert "film knowledge graph" in prompts[1] and "knowledge graph" not in prompts[0]
