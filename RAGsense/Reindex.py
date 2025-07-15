
from elasticsearch import Elasticsearch, helpers

ES_HOST = "http://localhost:9200"  
SOURCE_INDEX = "connector-jira_v2"
TARGET_INDEX = "jira"
SCROLL = "2m"
BATCH_SIZE = 100

es = Elasticsearch(ES_HOST, basic_auth=("elastic", "password"), request_timeout=60)

if not es.indices.exists(index=TARGET_INDEX):
    es.indices.create(index=TARGET_INDEX)

query = {
    "query": {
        "bool": {
            "must_not": {
                "term": {
                    "Type.keyword": "Attachment"
                }
            }
        }
    }
}

resp = es.search(
    index=SOURCE_INDEX,
    scroll=SCROLL,
    size=BATCH_SIZE,
    body=query
)

scroll_id = resp["_scroll_id"]
hits = resp["hits"]["hits"]
total = 0

while hits:
    actions = []

    for doc in hits:
        source = doc["_source"]

        actions.append({
            "_op_type": "index",
            "_index": TARGET_INDEX,
            "_id": doc["_id"],
            "_source": source
        })

    helpers.bulk(es, actions)
    total += len(hits)
    print(f"{total} Dokumente uebertragen...")

    resp = es.scroll(scroll_id=scroll_id, scroll=SCROLL)
    scroll_id = resp["_scroll_id"]
    hits = resp["hits"]["hits"]

es.clear_scroll(scroll_id=scroll_id)
print(f"Reindexing abgeschlossen. Insgesamt uebertragen: {total} Dokumente.")
