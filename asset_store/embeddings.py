import logging
from functools import lru_cache
from sentence_transformers import SentenceTransformer

logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)

MODEL_NAME = "all-mpnet-base-v2"  # 768-dim, matches schema_json.md spec


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> list[float]:
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()
