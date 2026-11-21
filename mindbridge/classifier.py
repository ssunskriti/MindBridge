# Partly generated with AI assistance (Claude, Anthropic): key_words() added with AI help
"""Concern classifier (8 labels).

Synopsis: "we will test a TF-IDF baseline against sentence-embedding features,
using logistic regression in both cases".

  * feature="tfidf"     -> TF-IDF (word 1-2 grams + char 3-5 grams) + LogisticRegression
  * feature="embedding" -> MiniLM sentence embeddings + LogisticRegression
                           (needs `sentence-transformers`; skipped if not installed)
"""
from __future__ import annotations

from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from .config import CLASSIFIER_PATH, EMBED_MODEL, TRAIN_CSV


@dataclass
class Prediction:
    label: str
    confidence: float
    probs: dict


def build_tfidf_pipeline() -> Pipeline:
    feats = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1, lowercase=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=2)),
    ])
    return Pipeline([
        ("features", feats),
        ("clf", LogisticRegression(max_iter=2000, C=5.0, class_weight="balanced")),
    ])


class EmbeddingFeaturizer:
    """sklearn-compatible transformer around sentence-transformers."""

    def __init__(self, model_name: str = EMBED_MODEL):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return np.asarray(self._load().encode(list(X), normalize_embeddings=True))

    def __getstate__(self):  # don't pickle the torch model
        return {"model_name": self.model_name, "_model": None}


def build_embedding_pipeline() -> Pipeline:
    return Pipeline([
        ("features", EmbeddingFeaturizer()),
        ("clf", LogisticRegression(max_iter=2000, C=2.0, class_weight="balanced")),
    ])


def load_training_data(path=TRAIN_CSV) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df.dropna(subset=["text", "label"])


def train(feature: str = "tfidf", path=TRAIN_CSV, save: bool = True) -> Pipeline:
    df = load_training_data(path)
    pipe = build_tfidf_pipeline() if feature == "tfidf" else build_embedding_pipeline()
    pipe.fit(df["text"], df["label"])
    if save:
        CLASSIFIER_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipe, CLASSIFIER_PATH)
    return pipe


class ConcernClassifier:
    def __init__(self, pipe: Pipeline | None = None):
        if pipe is None:
            pipe = joblib.load(CLASSIFIER_PATH) if CLASSIFIER_PATH.exists() else train()
        self.pipe = pipe
        self.labels = list(pipe.classes_)

    def predict(self, text: str) -> Prediction:
        p = self.pipe.predict_proba([text])[0]
        i = int(np.argmax(p))
        return Prediction(self.labels[i], float(p[i]), {l: float(v) for l, v in zip(self.labels, p)})

    # Generated with AI assistance (Claude)

    def key_words(self, text: str, label: str, n: int = 3) -> list:
        """Words in the message that pushed the model most towards `label`.

        Uses the word TF-IDF part of the model: weight in this message x the
        model's learned weight for that word and category. This is an
        observable property of the model, shown in "Why am I getting this
        response?". Returns [] for the embedding model.
        """
        features = self.pipe.named_steps.get("features")
        if not isinstance(features, FeatureUnion) or label not in self.labels:
            return []
        word_vec = dict(features.transformer_list)["word"]
        vocab = word_vec.get_feature_names_out()
        clf = self.pipe.named_steps["clf"]
        class_weights = clf.coef_[self.labels.index(label)][: len(vocab)]
        # "can't" is split into "can" + "t", so phrases with these stubs read wrongly
        contraction_stubs = {"can", "don", "won", "isn", "didn", "doesn", "wasn", "aren", "couldn", "shouldn"}
        row = word_vec.transform([text]).tocoo()
        scored = []
        for col, tfidf in zip(row.col, row.data):
            term = vocab[col]
            words = term.split()
            if any(w in contraction_stubs or w in ENGLISH_STOP_WORDS or len(w) < 3 for w in words):
                continue
            contribution = tfidf * class_weights[col]
            if contribution > 0:
                scored.append((contribution, term))
        picked = []
        for _, term in sorted(scored, reverse=True):
            # skip a single word already covered by a chosen two-word phrase, and vice versa
            if any(term in p.split() or p in term.split() for p in picked):
                continue
            picked.append(term)
            if len(picked) == n:
                break
        return picked
