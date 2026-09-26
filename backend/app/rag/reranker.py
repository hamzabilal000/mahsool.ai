"""Cross-encoder reranking with bge-reranker-v2-m3.

Retrieval embeds the question and each chunk *separately* and compares vectors, which is fast
but coarse. A cross-encoder reads the question and one chunk *together* and outputs a single
relevance score, which is far more precise but too slow to run on the whole corpus. So we
retrieve ~30 candidates cheaply, then rerank only those.
"""

import hashlib
from pathlib import Path
from typing import Protocol

from backend.app.config import Settings


class Reranker(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]: ...


class BGEReranker:
    """BAAI/bge-reranker-v2-m3 through FlagEmbedding. Scores are sigmoid-normalised to 0..1."""

    def __init__(self, settings: Settings) -> None:
        from FlagEmbedding import FlagReranker

        self.max_length = settings.reranker_max_length
        self.batch_size = settings.reranker_batch_size
        self.model = FlagReranker(
            settings.reranker_model,
            use_fp16=False,  # CPU
            cache_dir=str(settings.hf_cache_dir) if settings.hf_cache_dir else None,
        )
        if settings.reranker_quantize:
            import torch

            # int8 weights for every Linear layer; activations quantised on the fly (CPU only).
            self.model.model = torch.ao.quantization.quantize_dynamic(
                self.model.model, {torch.nn.Linear}, dtype=torch.qint8
            )

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        scores = self.model.compute_score(
            [[query, p] for p in passages],
            batch_size=self.batch_size,
            max_length=self.max_length,
            normalize=True,
        )
        return [float(s) for s in (scores if isinstance(scores, list) else [scores])]


class CrossEncoderReranker:
    """Any Hugging Face sequence-classification cross-encoder with one relevance logit (e.g.
    Alibaba-NLP/gte-multilingual-reranker-base, cross-encoder/mmarco-mMiniLMv2-L12-H384-v1).
    Scores are sigmoid(logit), 0..1, like BGEReranker (D59)."""

    def __init__(self, settings: Settings) -> None:
        import torch
        from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

        cache = str(settings.hf_cache_dir) if settings.hf_cache_dir else None
        name = settings.reranker_model
        self.torch, self.max_length = torch, settings.reranker_max_length
        self.batch_size = settings.reranker_batch_size
        self.tokenizer = AutoTokenizer.from_pretrained(name, cache_dir=cache)
        config = AutoConfig.from_pretrained(name, cache_dir=cache, trust_remote_code=True)
        if getattr(config, "auto_map", None):
            # Custom model code (gte): transformers 5 loads weights on the meta device and leaves
            # the code's non-persistent buffers (position ids, rotary tables) uninitialised, so
            # build the model normally and load the weights into it.
            from huggingface_hub import snapshot_download
            from safetensors.torch import load_file

            model = AutoModelForSequenceClassification.from_config(config, trust_remote_code=True)
            path = Path(snapshot_download(name, cache_dir=cache)) / "model.safetensors"
            model.load_state_dict(load_file(str(path)), strict=False)
            for m in model.modules():  # removed in transformers 5; the gte code still calls it
                if not hasattr(m, "get_extended_attention_mask") and hasattr(m, "embeddings"):
                    type(m).get_extended_attention_mask = _extended_attention_mask
        else:
            model = AutoModelForSequenceClassification.from_pretrained(name, cache_dir=cache)
        self.model = model.float().eval()

    def score(self, query: str, passages: list[str]) -> list[float]:
        out: list[float] = []
        for i in range(0, len(passages), self.batch_size):
            batch = passages[i : i + self.batch_size]
            enc = self.tokenizer(
                [query] * len(batch), batch, padding=True, truncation="only_second",
                max_length=self.max_length, return_tensors="pt",
            )  # fmt: skip
            with self.torch.inference_mode():
                logits = self.model(**enc).logits.view(-1).float()
            out += self.torch.sigmoid(logits).tolist()
        return out


def _extended_attention_mask(self, attention_mask, input_shape, device=None, dtype=None):
    """transformers 4's encoder mask: 0 where attended, the dtype's minimum where padded."""
    import torch

    dtype = dtype or next(self.parameters()).dtype
    mask = attention_mask[:, None, None, :].to(dtype)
    return (1.0 - mask) * torch.finfo(dtype).min


def make_reranker(settings: Settings) -> Reranker:
    if "bge-reranker" in settings.reranker_model:
        return BGEReranker(settings)
    return CrossEncoderReranker(settings)


class CachedReranker:
    """Wraps a reranker with an on-disk score cache keyed by (query, passage).

    Used by the ablation runs: several presets rerank the same question/chunk pairs, and on a
    CPU each pair costs ~1 s. The cache (eval/cache/rerank.tsv) is committed so a fresh clone
    can re-run the ablation without re-scoring; it stays valid while the chunks don't change.
    """

    def __init__(self, inner: Reranker, path: Path) -> None:
        self.inner, self.path = inner, path
        self.cache: dict[str, float] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                key, value = line.split("\t")
                self.cache[key] = float(value)

    @staticmethod
    def _key(query: str, passage: str) -> str:
        return hashlib.sha256(f"{query}\x00{passage}".encode()).hexdigest()[:24]

    def score(self, query: str, passages: list[str]) -> list[float]:
        keys = [self._key(query, p) for p in passages]
        todo = [i for i, k in enumerate(keys) if k not in self.cache]
        if todo:
            new = self.inner.score(query, [passages[i] for i in todo])
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                for i, s in zip(todo, new, strict=True):
                    self.cache[keys[i]] = s
                    fh.write(f"{keys[i]}\t{s}\n")
        return [self.cache[k] for k in keys]
