"""
FastAPI application entry point for document processing + RAG.
"""
from __future__ import annotations

import os
from pathlib import Path
import httpx

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from openai import OpenAI

from app.api.routes import router
from app.api.quiz_routes import router as quiz_router
from app.db.database import init_db
from app.config import settings


# ==========================================================
# Env loading (force the .env that sits next to THIS file)
# ==========================================================
ENV_PATH = (Path(__file__).resolve().parent / ".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")  # required
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SELF_BASE_URL = os.getenv("SELF_BASE_URL", "http://127.0.0.1:8000")

if not OPENAI_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing. Create app/.env with:\n"
        "OPENAI_API_KEY=sk-....\n"
        "SELF_BASE_URL=http://127.0.0.1:8000\n"
        "OPENAI_MODEL=gpt-4o-mini"
    )

# OpenAI client reads the key set above
client_oa = OpenAI(api_key=OPENAI_KEY)


# ==========================================================
# FastAPI app
# ==========================================================
app = FastAPI(
    title="Document Processing API",
    description="API for processing PDF/PPTX with embeddings + RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your existing routers
app.include_router(router, prefix="/api", tags=["documents"])
app.include_router(quiz_router, prefix="/api", tags=["quiz"])


@app.on_event("startup")
async def startup_event():
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.chroma_db_path, exist_ok=True)
    os.makedirs("app/data", exist_ok=True)
    init_db()
    print("✓ Database tables created")
    print("✓ Application started")
    print(f"✓ Upload directory: {settings.upload_dir}")
    print(f"✓ ChromaDB path: {settings.chroma_db_path}")
    print(f"✓ Database path: {settings.db_path}")


@app.on_event("shutdown")
async def shutdown_event():
    print("✓ Application shutdown complete")


@app.get("/")
async def root():
    return {
        "message": "Document Processing API + RAG",
        "endpoints": {
            "health": "/api/health",
            "collections": "/api/collections",
            "search": "/api/search",
            "ask": "/api/ask",
        },
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": OPENAI_MODEL}


# ==========================================================
# RAG: request model + helper
# ==========================================================
class AskReq(BaseModel):
    query: str
    collection_name: Optional[str] = None
    top_k: int = 5


async def _search_backend(query: str, top_k: int, collection_name: Optional[str]) -> List[Dict[str, Any]]:
    """
    Calls the existing /api/search endpoint and normalizes results.
    Supports:
      - { results: [{title,page/slide/chunk,snippet,url}, ...] }
      - { documents: [{source, content, chunk_index, ...}, ...] }
    """
    params: Dict[str, Any] = {"query": query, "top_k": top_k}
    if collection_name:
        params["collection_name"] = collection_name

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(f"{SELF_BASE_URL}/api/search", params=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search request failed: {e}")

    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Search failed: {r.text}")

    data = r.json()

    # Friend format
    if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
        return data["results"]

    # Your ingestion format
    if isinstance(data, dict) and "documents" in data and isinstance(data["documents"], list):
        docs = data["documents"]
        items = []
        for i, d in enumerate(docs):
            items.append(
                {
                    "title": d.get("source") or f"Document {i+1}",
                    "page": d.get("chunk_index") or d.get("page") or d.get("slide") or d.get("chunk"),
                    "snippet": d.get("content") or "",
                    "url": d.get("url") or "",
                }
            )
        return items

    return []


# ==========================================================
# RAG endpoint
# ==========================================================
@app.post("/api/ask")
async def api_ask(body: AskReq):
    # 1) Retrieve slide chunks
    items = await _search_backend(body.query, body.top_k, body.collection_name)
    if not items:
        return {"answer": f"No matches for “{body.query}”.", "citations": []}

    # Build RAG context
    def fmt(it: Dict[str, Any]) -> str:
        loc = it.get("page") or it.get("slide") or it.get("chunk") or ""
        if isinstance(loc, int):
            loc = f"p.{loc}"
        snippet = (it.get("snippet") or "").strip()
        title = it.get("title") or "Source"
        return f"[{title}] {loc}  {snippet}"

    context = "\n\n".join(fmt(it)[:800] for it in items[:body.top_k])

    system_prompt = (
        "You are a strict teaching assistant. "
        "Answer ONLY using the provided slide excerpts. "
        "If the info is not present, say you cannot find it in the slides. "
        "Use 3–6 short bullet points and cite like [Title p.3]."
    )
    user_prompt = (
        f"QUESTION:\n{body.query}\n\n"
        f"SLIDE EXCERPTS:\n{context}\n\n"
        "Write the answer now."
    )

    # 2) Generate with OpenAI
    try:
        resp = client_oa.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.2,
            max_tokens=400,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as e:
        # Return the *actual* OpenAI error to the frontend (401/invalid key, etc.)
        raise HTTPException(status_code=500, detail=f"OpenAI Error: {e}")

    answer = resp.choices[0].message.content.strip()

    # 3) Citations
    citations: List[str] = []
    for it in items[:body.top_k]:
        title = it.get("title") or "Source"
        loc = it.get("page") or it.get("slide") or it.get("chunk") or ""
        if isinstance(loc, int):
            loc = f"p.{loc}"
        snippet = (it.get("snippet") or "").strip()[:120]
        part = [title]
        if loc:
            part.append(str(loc))
        if snippet:
            part.append(f"— {snippet}")
        citations.append(" ".join(part))

    return {"answer": answer, "citations": citations}
