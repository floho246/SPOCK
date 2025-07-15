from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field
from services.rag_service import SourceType

# ──────────────────────────────────────────────────────────────────────────────
#  Models
# ──────────────────────────────────────────────────────────────────────────────
class SearchType(str, Enum):
    keyword = "Keyword"
    embedding = "Embedding"
    hybrid = "Hybrid"


class SearchRequest(BaseModel):
    query: str = Field(..., example="Suchbegriff")
    sources: List[str] = Field(..., example=["wiki", "jira"])
    searchType: SearchType = Field(
        ..., description="Art der Suche"
    )
    topK: Optional[int] = Field(
        10, description="Anzahl Top-K (bei embedding oder hybrid)"
    )
    enableGenerative: bool = Field(
        False, description="Generative Antwort (RAG) ein-/ausschalten"
    )
    promptExtension: Optional[str] = Field(
        None,
        description="Hier hast du zum einen uusätzlichen Kontext zum beantworten der Anfrage und die ursprüngliche Nutzeranfrage. Bitte beantworte die folgende Frage basierend auf dem bereitgestellten Textauszug oder fass das Dokument zusammen, falls es keine sinnvolle Frage gibt. Nutze ausschließlich Informationen aus dem Text. Wenn keine passende Antwort möglich ist, gib das an."
    )
    generativeDocs: Optional[int] = Field(
        1, description="Anzahl der Genutzten Ergebnisse für generative Antworten"
    )


class SearchResult(BaseModel):
    sourceType: SourceType
    id: str
    browseUrl: str
    title: Optional[str]
    summary: Optional[str]
    created: Optional[date]
    creator: Optional[str]
    score: float
    content: object


class SearchResponse(BaseModel):
    results: List[SearchResult]
    answer: Optional[str] = None


class SourceInfo(BaseModel):
    name: str = Field(
        ...,
        title="Quellenname",
        description="Ein lesbarer Name für die Datenquelle",
        example="Wiki"
    )
    type: SourceType = Field(
        ...,
        title="Quellentyp",
        description="Der Typ der Datenquelle",
        example=SourceType.confluence
    )
    available: bool = Field(
        ...,
        title="Verfügbarkeit",
        description="Gibt an, ob die Quelle aktuell verfügbar ist",
        example=True
    )
    embeddings: bool = Field(
        ...,
        title="Embeddings aktiviert",
        description="Gibt an, ob die Quelle Embeddings unterstützt",
        example=False
    )


class SourcesResponse(BaseModel):
    sources: List[SourceInfo]


# Anfrage-Modell
class LLMQuery(BaseModel):
    prompt: str = Field(
        ...,
        example="Was ist die Hauptstadt von Frankreich?",
        description="Der vollständige Prompt, der an das Sprachmodell gesendet werden soll."
    )


# Antwort-Modell (optional, aber sauber)
class LLMResponse(BaseModel):
    response: str


# Anfrage-Datenmodell
class DocumentQueryRequest(BaseModel):
    index: str = Field(..., example="wiki", description="Elasticsearch-Index, aus dem das Dokument geladen wird.")
    doc_id: str = Field(..., example="JIRA-123", description="Eindeutige Dokument-ID im angegebenen Index.")
    user_query: str = Field(..., example="Worum geht es in diesem Dokument?",
                            description="Benutzerfrage oder Zusammenfassungsanfrage zum Dokument.")

# ──────────────────────────────────────────────────────────────────────────────
