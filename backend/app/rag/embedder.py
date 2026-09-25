"""Text encoders. BGE-M3 gives a dense vector and a sparse (lexical) vector in one pass."""

from dataclasses import dataclass
from typing import Protocol

from backend.app.config import Settings


@dataclass
class Encoded:
    dense: list[float]
    sparse: dict[int, float]  # token id -> weight (BGE-M3 "lexical weights")


class Embedder(Protocol):
    dim: int

    def encode(self, texts: list[str], *, is_query: bool = False) -> list[Encoded]: ...


class BGEM3Embedder:
    """BAAI/bge-m3 through FlagEmbedding (`pip install -e ".[ml]"`).

    Queries and documents use the same encoder (BGE-M3 needs no instruction prefix).
    The import is lazy so the rest of the code base works without torch installed.
    """

    def __init__(self, settings: Settings) -> None:
        from FlagEmbedding import BGEM3FlagModel

        self.dim = settings.embedding_dim
        self.batch_size = settings.embedding_batch_size
        self.max_length = settings.embedding_max_length
        self.model = BGEM3FlagModel(
            settings.embedding_model,
            use_fp16=False,  # CPU
            cache_dir=str(settings.hf_cache_dir) if settings.hf_cache_dir else None,
        )

    def encode(self, texts: list[str], *, is_query: bool = False) -> list[Encoded]:
        out = self.model.encode(
            texts,
            batch_size=self.batch_size,
            max_length=128 if is_query else self.max_length,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        return [
            Encoded(
                dense=[float(x) for x in vec], sparse={int(k): float(v) for k, v in lex.items()}
            )
            for vec, lex in zip(out["dense_vecs"], out["lexical_weights"], strict=True)
        ]
