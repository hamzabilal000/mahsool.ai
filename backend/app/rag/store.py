"""Qdrant collection with a named dense vector and a named sparse vector per chunk."""

import uuid
from collections.abc import Iterable

from qdrant_client import QdrantClient, models

from backend.app.config import Settings
from backend.app.rag.embedder import Encoded
from ingestion.models import Chunk

DENSE = "dense"
SPARSE = "sparse"


def point_id(chunk: Chunk) -> str:
    """Stable id per chunk *and* snapshot, so a new law version is added, not overwritten."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{chunk.chunk_id}@{chunk.version_date}"))


def make_client(settings: Settings, *, in_memory: bool = False) -> QdrantClient:
    if in_memory:
        return QdrantClient(location=":memory:")
    if settings.qdrant_url:
        key = settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
        return QdrantClient(url=settings.qdrant_url, api_key=key)
    settings.qdrant_path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(settings.qdrant_path))


class VectorStore:
    def __init__(self, client: QdrantClient, collection: str, dim: int) -> None:
        self.client, self.collection, self.dim = client, collection, dim

    def recreate(self) -> None:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            self.collection,
            vectors_config={
                DENSE: models.VectorParams(size=self.dim, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={SPARSE: models.SparseVectorParams()},
        )
        for field, schema in [
            ("law_code", models.PayloadSchemaType.KEYWORD),
            ("section_id", models.PayloadSchemaType.KEYWORD),
            ("tax_year_from", models.PayloadSchemaType.INTEGER),
        ]:
            self.client.create_payload_index(self.collection, field, schema)

    def upsert(self, chunks: list[Chunk], vectors: list[Encoded]) -> None:
        points = [
            models.PointStruct(
                id=point_id(c),
                vector={
                    DENSE: v.dense,
                    SPARSE: models.SparseVector(
                        indices=list(v.sparse), values=list(v.sparse.values())
                    ),
                },
                payload=c.model_dump(mode="json"),
            )
            for c, v in zip(chunks, vectors, strict=True)
        ]
        self.client.upsert(self.collection, points=points)

    def count(self) -> int:
        return self.client.count(self.collection).count

    @staticmethod
    def tax_year_filter(
        tax_year: int | None, law_codes: Iterable[str] | None = None
    ) -> models.Filter | None:
        must: list[models.Condition] = []
        if tax_year is not None:
            must.append(
                models.FieldCondition(key="tax_year_from", range=models.Range(lte=tax_year))
            )
            must.append(
                models.Filter(
                    should=[
                        models.IsNullCondition(is_null=models.PayloadField(key="tax_year_to")),
                        models.FieldCondition(key="tax_year_to", range=models.Range(gte=tax_year)),
                    ]
                )
            )
        if law_codes:
            must.append(
                models.FieldCondition(key="law_code", match=models.MatchAny(any=list(law_codes)))
            )
        return models.Filter(must=must) if must else None

    def search_dense(
        self, vector: list[float], k: int, flt: models.Filter | None = None
    ) -> list[tuple[str, float]]:
        res = self.client.query_points(
            self.collection,
            query=vector,
            using=DENSE,
            limit=k,
            query_filter=flt,
            with_payload=["chunk_id"],
        )
        return [(p.payload["chunk_id"], p.score) for p in res.points]

    def search_sparse(
        self, sparse: dict[int, float], k: int, flt: models.Filter | None = None
    ) -> list[tuple[str, float]]:
        if not sparse:
            return []
        query = models.SparseVector(indices=list(sparse), values=list(sparse.values()))
        res = self.client.query_points(
            self.collection,
            query=query,
            using=SPARSE,
            limit=k,
            query_filter=flt,
            with_payload=["chunk_id"],
        )
        return [(p.payload["chunk_id"], p.score) for p in res.points]
