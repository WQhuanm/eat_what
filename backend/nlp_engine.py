import os
from functools import lru_cache
from typing import List

import numpy as np


DEFAULT_VECTOR_DIM = int(os.getenv("DISH_VECTOR_DIM", "768"))
DEFAULT_MODEL_NAME = os.getenv("NLP_MODEL_NAME", "shibing624/text2vec-base-chinese")


class ModelUnavailableError(RuntimeError):
    pass


def _l2_normalize(values: List[float]) -> List[float]:
    arr = np.asarray(values, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    if norm <= 1e-12:
        return arr.tolist()
    return (arr / norm).tolist()


@lru_cache(maxsize=1)
def _sentence_model():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None
    try:
        return SentenceTransformer(DEFAULT_MODEL_NAME, local_files_only=True)
    except Exception:
        return None


def _fit_dim(vec: List[float], dim: int) -> List[float]:
    if len(vec) > dim:
        return vec[:dim]
    if len(vec) < dim:
        return vec + [0.0] * (dim - len(vec))
    return vec


def vectorize_text(text: str, dim: int = DEFAULT_VECTOR_DIM) -> List[float]:
    model = _sentence_model()
    if model is None:
        raise ModelUnavailableError("sentence-transformers 模型不可用")
    try:
        embedding = model.encode([text], normalize_embeddings=True)[0]
        vec = [float(v) for v in embedding.tolist()]
        vec = _fit_dim(vec, dim)
        return [round(float(x), 8) for x in _l2_normalize(vec)]
    except Exception as exc:
        raise ModelUnavailableError(f"模型推理失败: {exc}") from exc


def active_model_name() -> str:
    return DEFAULT_MODEL_NAME if _sentence_model() is not None else "unavailable"
