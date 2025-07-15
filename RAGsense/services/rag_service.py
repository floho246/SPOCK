import linecache
import os
import warnings
from enum import Enum
from typing import Any
from typing import List, Dict

from dateutil import parser
from dotenv import load_dotenv
from elastic_transport import ObjectApiResponse
from elasticsearch import Elasticsearch, helpers
from openai import OpenAI
from sentence_transformers import SentenceTransformer

class SourceType(str, Enum):
    jira = "Jira"
    confluence = "Confluence"
    network_drive = "Network Drive"
    unknown = "Unknown"

def prepare_search_results(response: ObjectApiResponse, index_name: str) -> List[Dict[str, Any]]:
    """
    Bereitet die Such-Treffer aus Elasticsearch auf und mappt sie
    je nach Index-Typ (Jira, Wiki, Repo, Sonstige) in ein einheitliches Format.

    :param response: Das Elasticsearch-Response-Objekt
    :param index_name: Name des Elasticsearch-Index
    :return: Liste von Dictionarys mit den aufbereiteten Ergebnissen
    """
    results = []

    for hit in response.get("hits", {}).get("hits", []):
        src = hit.get("_source", {})
        score = hit.get("_score", 0.0)

        if os.getenv("JIRA_INDEX") in index_name:
            # Jira-Index
            item = {
                "source": SourceType.jira,
                "id": src.get("Key"),
                "title": src.get("Issue", {}).get("summary"),
                "summary": src.get("Issue", {}).get("description"),
                "score": score,
                "url": "http://jira/browse/" + src.get("Key"),
                "creator": src.get("Issue", {}).get("creator", {}).get("displayName"),
                "created": ((created_str := src.get("Issue", {}).get("created")) and parser.isoparse(created_str).date()) or None,
                "content": src.get("Issue")
            }

        elif os.getenv("WIKI_INDEX") in index_name:
            # Wiki-Index
            item = {
                "source": SourceType.confluence,
                "id": f"{hit.get('_id')}",
                "title": src.get("title"),
                "summary": src.get("body"),
                "score": score,
                "url": src.get("url"),
                "creator": (author := src.get("author")) and isinstance(author, dict) and author.get("displayName"),
                "created": ((created_str := src.get("createdDate")) and parser.isoparse(created_str).date()) or None,
                "content": "TODO Wiki Content hier rein"
            }

        elif os.getenv("FILES_INDEX") in index_name:
            # Wiki-Index
            item = {
                "source": SourceType.network_drive,
                "id": src.get('id'),
                "title": src.get("title"),
                "summary": src.get("body"),
                "score": score,
                "url": src.get("path"),
                "created": ((created_str := src.get("created_at")) and parser.isoparse(created_str).date()) or None,
                "size_bytes": src.get("size"),
            }

        else:
            # Fallback für alle anderen Indizes
            item = {
                "source": SourceType.unknown,
                "content": src.get("content"),
                "score": score,
            }
            if "id" in src:
                item["id"] = src["id"]
            else:
                item["id"] = 0
            if "url" in src:
                item["url"] = src["url"]
            else:
                item["url"] = "http://example.org"
            
            if "page_number" in src:
                item["page_number"] = src["page_number"]

        results.append(item)

    return results


class RAGService:
    def __init__(self, elasticsearch_uri: str, groq_api_key: str, username: str, password: str):

        self._openAI_client = OpenAI(base_url=os.getenv("LLM_URL"), api_key="not-needed")
        models = self._openAI_client.models.list()
        print(models)

         # Anfrage an das Groq-Modell
        completion = self._openAI_client.chat.completions.create(
            model="/models/Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf",
            messages=[ { "role": "system", "content": "Du bist ein hilfreicher Assistent."},{"role": "user", "content": "What is the capital of france?"}]
        )
        print(completion)

        warnings.filterwarnings(
            'ignore',
            message='.*merge body fields no duplicates.*',
            category=UserWarning,
            module='elasticsearch'
        )
        _original_getlines = linecache.getlines

        def safe_getlines(filename: str, module_globals=None):
            try:
                return _original_getlines(filename, module_globals)
            except UnicodeDecodeError:
                return []

        linecache.getlines = safe_getlines

        self._elastic_client = Elasticsearch(
            elasticsearch_uri,
            basic_auth=(username, password)
        )
        if self._elastic_client.ping():
            print("Erfolgreich mit Elasticsearch verbunden.")
        else:
            print("Elasticsearch Verbindung fehlgeschlagen.")

        load_dotenv()

    # 2. Search text passages in Elasticsearch
    def search_elasticsearch(self, query: str, index: str = "_all", max_results: int = 100) -> List[dict]:
        """
        Fuehrt die Suche in Elasticsearch aus und gibt eine Liste von Ergebnissen zurueck.
        Jedes Ergebnis enthaelt 'content', 'page_number' und 'score'.
        """
        load_dotenv()
        response = self._elastic_client.search(index=index, body={
            "query": {
                "query_string": {
                    "query": query,
                    # optional: lenient=true bei z.B. Zahlen-/Datumsparse-Fehlern
                    # "lenient": True
                }
            },
            "size": max_results
        })

        return prepare_search_results(response, index)


    # 3. Query Groq
    def query_languageModel(self, prompt: str) -> str:
        """
        Fuehrt eine LLM-Anfrage bei OpenAI compatible webserevers durch und gibt das Ergebnis als String zurueck.
        Streamt die Antwort direkt in der Konsole.
        """
        # Anfrage an das Groq-Modell
        completion = self._openAI_client.chat.completions.create(
            model="/models/Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf",
            messages=[ { "role": "system", "content": "Du bist ein hilfreicher Assistent."},{"role": "user", "content": prompt}]
        )
        print(completion)

        return completion.choices[0].message.content

    # 4. Combined User Query
    def combined_query(self, index: str, doc_id: str, user_query: str) -> dict:
        """
        Führt eine kombinierte Anfrage durch, basierend auf einem einzelnen Dokument in Elasticsearch.
        - Holt das Dokument über Index + ID
        - Kombiniert dessen Inhalt mit dem Benutzerprompt
        - Ruft die Antwort vom Sprachmodell ab

        Gibt ein Dictionary mit LLM-Antwort und Dokumentinhalt zurück.
        """
        # 1. Hole das Dokument aus Elasticsearch
        try:
            doc = self._elastic_client.get(index=index, id=doc_id)
            document_text = doc["_source"].get("content", "")
        except Exception as e:
            raise ValueError(f"Fehler beim Abrufen des Dokuments {index}/{doc_id}: {str(e)}")

        if not document_text.strip():
            raise ValueError("Dokument ist leer oder enthält kein 'content'-Feld")

        # 2. Hardcoded Prompt Extension
        prompt_extension = (
            "Bitte beantworte die folgende Frage basierend auf dem bereitgestellten Textauszug oder fass das Dokument zusammen, falls es keine sinnvolle Frage gibt "
            "Nutze ausschließlich Informationen aus dem Text. Wenn keine passende Antwort möglich ist, gib das an."
        )

        # 3. Prompt zusammensetzen
        prompt = (
            f"{prompt_extension}\n\n"
            f"Frage:\n{user_query}\n\n"
            f"Textauszug:\n{document_text}"
        )

        # 4. Anfrage an LLM
        try:
            llm_answer = self.query_languageModel(prompt)
        except Exception as e:
            raise ValueError(f"Fehler bei der Anfrage an das Sprachmodell: {str(e)}")

        # 5. Rückgabe
        return llm_answer


    def compute_embeddings_for_elasticsearch_index(
        self, 
        index_name: str,
        model_name: str = "distiluse-base-multilingual-cased-v1",
        batch_size: int = 128,
        scroll_ttl: str = '2m',
        show_progress: bool = True,
        ) -> int:
        """
        Laedt alle Dokumente eines Elasticsearch-Index, serialisiert das komplette Dokument als JSON-String,
        berechnet ihre Embeddings mit einem SentenceTransformer-Modell
        und speichert die Embeddings zurueck im Elasticsearch-Index.

        Args:
            elastic_client (Elasticsearch): Initialisierter Elasticsearch-Client.
            index_name (str): Name des zu aktualisierenden Index.
            model_name (str): Bezeichnung des SentenceTransformer-Modells.
            batch_size (int): Anzahl der Dokumente pro Batch.
            show_progress (bool): Fortschrittsanzeige beim Berechnen.

        Returns:
            int: Anzahl der bearbeiteten Dokumente.
        """
         # Modell laden
        model = SentenceTransformer(model_name)
        elastic_client=self._elastic_client

        total_processed = 0
                
        # High-Level search mit Scroll
        resp = elastic_client.search(
            index=index_name,
            body={"query": {"match_all": {}}},
            scroll=scroll_ttl,
            size=batch_size
        )
        scroll_id = resp.get("_scroll_id")
        hits = resp["hits"]["hits"]

        def extract_text(doc_source, index_name):
            if index_name == "jira":
                fields = [
                    ("Issue.assignee.displayName", "Bearbeiter:"),
                    ("Issue.creator.displayName", "Erstellt von:"),
                    #("Issue.comments.body", "Kommentare:"),
                    ("Issue.summary", "Zusammenfassung:"),
                    ("Issue.description", "Beschreibung:"),
                    ("Issue.project.name", "Projektname:"),
                    ("Issue.project.projectCategory.description", "Projektkategorie:"),
                    ("Issue.resolution.name", "Lösung:"),
                    ("Type", "Typ:"),
                    ("Custom_Fields.Kunde(n)", "Kunde(n):")
                ]
            elif index_name == "wiki":
                fields = [
                    ("title", "Titel:"),
                    ("body", "Inhalt:"),
                    ("url", "URL:")
                ]
            else:
                return ""

            def get_nested_value(obj, path):
                keys = path.split(".")
                for key in keys:
                    if isinstance(obj, dict):
                        obj = obj.get(key)
                    else:
                        return None
                return obj

            lines = []
            for path, label in fields:
                value = get_nested_value(doc_source, path)
                if value:
                    if isinstance(value, list):
                        value = "\n".join(str(v) for v in value)
                    lines.append(f"{label} {value}")
            return "\n".join(lines)



        while hits:
            texts = [extract_text(doc["_source"], index_name) for doc in hits]
            ids = [doc["_id"] for doc in hits]

            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
            )

            actions = [
                {
                    "_op_type": "update",
                    "_index": index_name,
                    "_id": doc_id,
                    "doc": {"embedding": emb.tolist()}
                }
                for doc_id, emb in zip(ids, embeddings)
            ]
            helpers.bulk(elastic_client, actions)

            total_processed += len(hits)

            resp = elastic_client.scroll(
                scroll_id=scroll_id,
                scroll=scroll_ttl
            )
            scroll_id = resp.get("_scroll_id")
            hits = resp["hits"]["hits"]

        # Scroll-Kontext löschen
        try:
            elastic_client.clear_scroll(scroll_id=scroll_id)
        except Exception:
            pass

        return total_processed

    
    def vector_search_elasticsearch(
        self,
        index_name: str,
        query: str,
        model_name: str = "distiluse-base-multilingual-cased-v1",
        top_k: int = 30,
    ) -> List:
        """
        Führt eine Vektor-Suche in Elasticsearch durch:
        1. Berechnet das Embedding des Suchstrings.
        2. Verwendet script_score mit cosineSimilarity, um die Top-K-Dokumente zu ranken.

        Returns:
            List[Dict[str, Any]]: Die Treffer mit _id, _score und _source.
        """
        model = SentenceTransformer(model_name)
        # Query-Embedding berechnen
        query_emb = model.encode([query], convert_to_numpy=True)[0].tolist()

        # Script-Score Abfrage
        body = {
            "size": top_k,
            "query": {
                "script_score": {
                    # 1) Erst filtern …
                    "query": {
                        "bool": {
                            "must":   {"match_all": {}},            # alle Dokumente
                            "must_not": {"term": {
                                "Type": "Attachment"
                                }
                            }  # … außer type=attachment
                        }
                    },
                    # 2) … dann mit dem Vektor scorieren
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_emb}
                    }
                }
            }
        }

        resp = self._elastic_client.search(
            index=index_name,
            body=body
        )

        return prepare_search_results(resp, index_name)




    def hybrid_search_elasticsearch(
        self,
        index_name: str,
        query: str,
        model_name: str = "distiluse-base-multilingual-cased-v1",
        top_k: int = 30,
        bm25_weight: float = 1.0,
        embedding_weight: float = 35.0,
    ) -> List[dict]:
        """
        Führt eine hybride Suche in Elasticsearch durch:
        - Kombiniert BM25-basierten Query-String-Score mit Vektor-Score (Cosine Similarity).
        - Entfernt Dokumente vom Typ "Attachment".

        Args:
            index_name (str): Name des Elasticsearch-Index.
            query (str): Suchstring für die Query-String-Komponente.
            model_name (str): Name des SentenceTransformer-Modells für Embeddings.
            top_k (int): Anzahl der zurückzugebenden Top-Dokumente.
            bm25_weight (float): Gewichtung des BM25-Scores.
            embedding_weight (float): Gewichtung des Embedding-Scores.

        Returns:
            List[dict]: Treffer mit Feldern aus _source und kombiniertem Score.
        """
        from sentence_transformers import SentenceTransformer

        # 1) Embedding des Suchstrings berechnen
        model = SentenceTransformer(model_name)
        query_emb = model.encode([query], convert_to_numpy=True)[0].tolist()

        # 2) Hybrid-Abfrage zusammenstellen
        body = {
            "size": top_k,
            "query": {
                "script_score": {
                    # a) Alle Dokumente (außer Attachments) durchsuchen
                    "query": {
                        "bool": {
                            "should": [
                                {"query_string": {"query": query}},  # BM25-Teil
                                {"match_all": {}}                      # Basis für Embeddings
                            ],
                            "must_not": {"term": {"Type": "Attachment"}}
                        }
                    },
                    # b) Score-Kombination: bm25_weight * BM25 + embedding_weight * (Cosine + Offset)
                    "script": {
                        "source": (
                            "double bm25 = _score;"
                            "double emb = cosineSimilarity(params.query_vector, 'embedding') + 1.0;"
                            "return params.bm25_weight * bm25 + params.embedding_weight * emb;"
                        ),
                        "params": {
                            "query_vector": query_emb,
                            "bm25_weight": bm25_weight,
                            "embedding_weight": embedding_weight
                        }
                    }
                }
            }
        }

        # 3) Anfrage ausführen
        response = self._elastic_client.search(index=index_name, body=body)

        return prepare_search_results(response, index_name)

