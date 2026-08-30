"""studyrag skill — query the user's StudyRag vector store."""

import json
import pickle
from pathlib import Path

import numpy as np

STUDYRAG_DB = Path(r"C:\Users\91460\OneDrive\Desktop\studpart\data\chroma_db")
STUDYRAG_TOP_K = 4


def _load_store() -> tuple[np.ndarray, list, object] | str:
    """Load the StudyRag store, transparently handling BOTH the legacy
    pickle format and the newer JSON format. Returns (vectors, metadata,
    vectorizer) on success, or an error string."""
    try:
        vectors = np.load(STUDYRAG_DB / "tfidf_vectors.npy")
    except (FileNotFoundError, ValueError) as e:
        return f"Error: could not load vectors.npy: {e}"

    if (STUDYRAG_DB / "metadata.json").exists():
        metadata = json.loads((STUDYRAG_DB / "metadata.json").read_text(encoding="utf-8"))
    elif (STUDYRAG_DB / "metadata.pkl").exists():
        try:
            metadata = pickle.loads((STUDYRAG_DB / "metadata.pkl").read_bytes())
        except (ValueError, pickle.UnpicklingError) as e:
            return f"Error: metadata.pkl is in an old/incompatible format. Re-ingest the store: {e}"
    else:
        return "Error: neither metadata.pkl nor metadata.json was found in the store."

    if (STUDYRAG_DB / "vectorizer.pkl").exists():
        try:
            vectorizer = pickle.loads((STUDYRAG_DB / "vectorizer.pkl").read_bytes())
        except (ValueError, pickle.UnpicklingError) as e:
            return f"Error: vectorizer.pkl is incompatible. Re-ingest the store: {e}"
    elif (STUDYRAG_DB / "vectorizer.json").exists():
        # JSON serialization loses the fitted state (sklearn stores fitted
        # state in underscore-prefixed attrs). Rebuild a fresh vectorizer
        # by fitting it on the metadata's stored chunk text. Same vocab, same
        # math, just a different path to get there.
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(max_features=5000, stop_words="english", ngram_range=(1, 2))
        vectorizer.fit([m.get("text", "") for m in metadata if m.get("text")])
    else:
        return "Error: neither vectorizer.pkl nor vectorizer.json was found in the store."

    return vectors, metadata, vectorizer


def query_studyrag(question: str) -> str:
    """Search the user's own course notes via the StudyRag TF-IDF store."""
    loaded = _load_store()
    if isinstance(loaded, str):
        return loaded
    vectors, metadata, vectorizer = loaded

    if vectors.size == 0 or not metadata:
        return (
            "The StudyRag knowledge base is empty. "
            "Tell the user to put PDF/PPTX files into studpart/data/documents "
            "and run 'python main.py ingest' from the studpart folder."
        )

    query_vec = vectorizer.transform([question]).toarray().astype(np.float32)
    q_norm = query_vec / (np.linalg.norm(query_vec, axis=1, keepdims=True) + 1e-8)
    d_norms = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-8)
    scores = (d_norms @ q_norm.T).flatten()
    top_indices = np.argsort(scores)[-STUDYRAG_TOP_K:][::-1]

    lines = []
    for rank, idx in enumerate(top_indices, start=1):
        if scores[idx] < 0.01:
            continue
        meta = metadata[idx]
        lines.append(
            f"[{rank}] source: {meta['source']} (relevance {scores[idx]:.3f})\n{meta['text']}"
        )

    if not lines:
        return "No relevant notes found for that question."
    return "\n\n".join(lines)


TOOLS = {"query_studyrag": query_studyrag}
TOOL_SCHEMAS = [{
    "type": "function",
    "function": {
        "name": "query_studyrag",
        "description": (
            "Searches the user's personal study notes and course materials "
            "(the StudyRag knowledge base: lecture slides, handouts and "
            "reviewers the user added, e.g. PDF and PPTX files). Use this "
            "FIRST for any question about the user's own files, notes or "
            "coursework — including questions that name a specific file. "
            "Do not use it for general world knowledge — use web_search instead."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question or topic to look for in the notes, e.g. 'definition of recursion'",
                }
            },
            "required": ["question"],
        },
    },
}]
