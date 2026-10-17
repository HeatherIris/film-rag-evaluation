import re
import sys
from pathlib import Path

import numpy as np
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

FIXTURE_SCENES = Path(__file__).resolve().parent / "fixtures" / "scenes"


def fake_embed(texts):
    """Bag-of-words hashing embedding: deterministic, no API key."""
    matrix = np.zeros((len(texts), 512), dtype=np.float32)
    for row, text in enumerate(texts):
        for token in re.findall(r"[a-z]+", text.lower()):
            if len(token) > 2:
                matrix[row, hash(token) % 512] += 1.0
    norms = np.clip(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12, None)
    return matrix / norms


@pytest.fixture
def demo_scenes(monkeypatch):
    from app.services import retrieval_service, scene_retrieval

    monkeypatch.setattr(retrieval_service, "_embed", fake_embed)
    monkeypatch.setattr(scene_retrieval, "SCENES_DIR", FIXTURE_SCENES)
    monkeypatch.setattr(scene_retrieval, "_index", None)
    return FIXTURE_SCENES
