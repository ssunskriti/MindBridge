"""RAG pipeline: curated KB -> chunks -> embeddings -> FAISS -> top-k -> LLM.

Embeddings: MiniLM (sentence-transformers) if installed, else TF-IDF vectors.
Index:      FAISS IndexFlatIP if installed, else NumPy dot product.
Each KB file starts with a metadata header (title / source / url / retrieved),
so every answer can show where it came from.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from .config import CHUNK_OVERLAP, CHUNK_WORDS, EMBED_MODEL, KB_DIR, MIN_RETRIEVAL_SCORE, TOP_K


@dataclass
class Chunk:
    text: str
    title: str
    source: str
    url: str
    retrieved: str
    doc: str


def parse_doc(path):
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw
    m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)
    return meta, body.strip()


def chunk_text(body: str, size=CHUNK_WORDS, overlap=CHUNK_OVERLAP):
    words = body.split()
    if len(words) <= size:
        return [body]
    out, step = [], size - overlap
    for i in range(0, len(words), step):
        out.append(" ".join(words[i:i + size]))
        if i + size >= len(words):
            break
    return out


def load_chunks(kb_dir=KB_DIR):
    chunks = []
    for p in sorted(kb_dir.glob("*.md")):
        meta, body = parse_doc(p)
        for c in chunk_text(body):
            chunks.append(Chunk(c, meta.get("title", p.stem), meta.get("source", "MindBridge team"),
                                meta.get("url", ""), meta.get("retrieved", ""), p.name))
    return chunks


class Embedder:
    def __init__(self, texts):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(EMBED_MODEL)
            self.kind = "MiniLM"
        except Exception:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.model = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english").fit(texts)
            self.kind = "TF-IDF (fallback)"

    def encode(self, texts):
        if self.kind == "MiniLM":
            v = self.model.encode(texts, normalize_embeddings=True)
        else:
            v = self.model.transform(texts).toarray()
            v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
        return np.asarray(v, dtype="float32")


class Retriever:
    def __init__(self, kb_dir=KB_DIR):
        self.chunks = load_chunks(kb_dir)
        texts = [f"{c.title}. {c.text}" for c in self.chunks]
        self.embedder = Embedder(texts)
        vecs = self.embedder.encode(texts)
        try:
            import faiss
            self.index = faiss.IndexFlatIP(vecs.shape[1])
            self.index.add(vecs)
            self.backend = "FAISS"
        except Exception:
            self.index, self.backend = vecs, "NumPy"

    def search(self, query: str, k: int = TOP_K):
        q = self.embedder.encode([query])
        if self.backend == "FAISS":
            scores, idx = self.index.search(q, k)
            pairs = zip(scores[0], idx[0])
        else:
            s = self.index @ q[0]
            top = np.argsort(-s)[:k]
            pairs = zip(s[top], top)
        return [(self.chunks[i], float(sc)) for sc, i in pairs if i >= 0 and sc >= MIN_RETRIEVAL_SCORE]
