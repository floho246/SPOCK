import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from Models import *
from services.rag_service import RAGService

load_dotenv()  # ← muss vor jedem os.getenv stehen

print("→ ELASTICSEARCH_URI =", os.getenv("ELASTICSEARCH_URI"))

app = FastAPI(title="RAG Service API")

# Alles erlauben was CORS angeht
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisiere den RAGServiceHandler
elasticsearch_uri = os.getenv("ELASTICSEARCH_URI")
groq_api_key = os.getenv("GROQ_API_KEY")
username = os.getenv("ELASTIC_USERNAME")
password = os.getenv("ELASTIC_PASSWORD")
logging.info("Das Programm startet jetzt")
logging.info(elasticsearch_uri)
rag = RAGService(elasticsearch_uri, groq_api_key, username, password)

@app.get("/api/health")
def health_check():
    """
    Gesundheitsprüfung: Elasticsearch + optional LLM-Gateway
    """
    es_ok = rag._elastic_client.ping()
    if not es_ok:
        raise HTTPException(status_code=503, detail="Elasticsearch nicht erreichbar")
    # Optional: hier könnte man noch Groq-Ping o.ä. abfragen
    return {"status": "ok"}


@app.get("/api/sources")
def list_sources():
    """
    Listet alle konfigurierten Indices/Datenquellen auf.
    """
    return SourcesResponse(
        # todo das sollte vllt von elastic direkt abgefragt werden
        sources= [
            SourceInfo(name=os.getenv("JIRA_INDEX"), type=SourceType.jira, available=True, embeddings=True),
            SourceInfo(name=os.getenv("WIKI_INDEX"), type=SourceType.confluence, available=True, embeddings=True),
            # SourceInfo(name=os.getenv("REPO_INDEX"), type=SourceType.unknown, available=False, embeddings=False),
            SourceInfo(name=os.getenv("FILES_INDEX"), type=SourceType.unknown, available=True, embeddings=False),
        ]
    )

@app.post("/api/generate", response_model=LLMResponse)
def generate_llm_response(query: LLMQuery):
    """
    Anfrage an das LLM senden und Antwort generieren
    """
    try:
        result = rag.query_languageModel(query.prompt)
        return LLMResponse(response=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM-Fehler: {str(e)}")
        
@app.post("/api/llm/doc_query", response_model=LLMResponse)
def query_single_document(request: DocumentQueryRequest):
    """
    LLM-Anfrage basierend auf einem bestimmten Elasticsearch-Dokument.
    """
    try:
        answer = rag.combined_query(
            index=request.index,
            doc_id=request.doc_id,
            user_query=request.user_query
        )
        return LLMResponse(answer=answer)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interner Fehler: {str(e)}")

@app.post("/api/search", response_model=SearchResponse)
def search(req: SearchRequest):
    """
    Ein einziger Search-Endpoint, der
     - Keyword-, Vektor- oder Hybrid-Suche ausführt
     - optional eine generative RAG-Antwort anfordert
    """
    # 1) Dokumente holen
    if req.searchType == SearchType.keyword:
        hits = []
        for src in req.sources:
            hits += rag.search_elasticsearch(req.query, index=src, max_results=req.topK)
    elif req.searchType == SearchType.embedding:
        hits = []
        for src in req.sources:
            hits += rag.vector_search_elasticsearch(src, req.query, top_k=req.topK)
    else:  # hybrid
        hits = []
        for src in req.sources:
        # simple hybrid: beide Modi kombinieren und nach score sortieren
            hits += rag.hybrid_search_elasticsearch(src, req.query, top_k=req.topK)

    # 2) Optional: generative Antwort
    answer = None
    if req.enableGenerative:
        # wir nutzen einfach die relevantesten Snippets als Prompt-Extension
        snippets = "\n".join(f"{h['source']} — ID: {h.get('id','')}; " f"Titel: {h.get('title','')}; "    f"Summary: {h.get('summary','')}; "  "----" for h in hits[:req.generativeDocs])
        payload = f"{req.promptExtension or ''}\n\nOriginal query: {req.query}\n\nSnippets:\n{snippets}"
        answer = rag.query_languageModel(payload)

    # 3) Mapping auf das gemeinsame Result-DTO
    results = []
    for h in hits:
        src = h["source"]
        doc_id = h.get("id") 
        browse = h.get("url")
        results.append(
            SearchResult(
                sourceType=SourceType(src),
                id=doc_id,
                browseUrl=browse,
                title=h.get("title"), 
                summary=h.get("summary"), 
                created=h.get("created") if "created" in h else None,
                creator=h.get("creator") if "creator" in h else None,
                score=h["score"],
                content=h.get("content")
            )
       )

    return SearchResponse(results=results, answer=answer)

