import math

import pytest

from app.core.config import Settings

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def embedder():
    from app.embeddings.model import Embedder  # importa o torch só quando os testes slow rodam

    return Embedder(Settings.model_fields["embedding_model"].default, num_threads=4)


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def test_vectors_have_1024_dims_and_unit_norm(embedder):
    vectors = embedder.encode(["Protocolo anestésico em felinos.", "Canine osteoarthritis."])

    assert all(len(v) == 1024 for v in vectors)
    assert all(math.isclose(math.sqrt(_dot(v, v)), 1.0, abs_tol=1e-3) for v in vectors)


def test_portuguese_question_is_closer_to_english_translation(embedder):
    pt, en, unrelated = embedder.encode([
        "O tratamento reduziu a dor em gatos após a cirurgia.",
        "The treatment reduced pain in cats after surgery.",
        "The stock market closed higher today.",
    ])

    assert _dot(pt, en) > _dot(pt, unrelated)
