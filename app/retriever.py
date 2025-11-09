import os
from typing import List, Dict, Any, Optional

from chromadb import PersistentClient
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# Paths & collection name
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION = os.getenv("CHROMA_COLLECTION", "netsec")

_client: Optional[PersistentClient] = None
_collection = None

# -- internal helper ------------------------------------------------------
def _get_collection():
    global _client, _collection
    if _client is None:
        _client = PersistentClient(path=CHROMA_PATH)
    if _collection is None:
        _collection = _client.get_or_create_collection(
            name=COLLECTION,
            embedding_function=ONNXMiniLM_L6_V2(),
        )
    return _collection

# -- public API ------------------------------------------------------------
def retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Return top-k documents from the ChromaDB collection.
    Always returns a safe structured list (never crashes the server).
    """
    q = (query or "").strip()
    if not q:
        return []

    try:
        col = _get_collection()
        result = col.query(
            query_texts=[q],
            n_results=max(1, int(top_k)),
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        return [{
            "title": "Retriever Error",
            "page": "",
            "snippet": f"{type(e).__name__}: {e}",
            "url": "",
            "score": None,
        }]

    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    dists = (result.get("distances") or [[]])[0]

    if not docs:
        return [{
            "title": "No results",
            "page": "",
            "snippet": "Your Chroma collection is empty or query returned nothing.",
            "url": "",
            "score": None,
        }]

    output: List[Dict[str, Any]] = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        output.append({
            "title": meta.get("title") or meta.get("source") or "Document",
            "page": meta.get("page") or meta.get("slide") or meta.get("chunk"),
            "snippet": (doc or "")[:500],
            "url": meta.get("url") or "",
            "score": float(dists[i]) if i < len(dists) else None,
        })

    return output
