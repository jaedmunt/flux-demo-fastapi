# Flux Demo FastAPI

## Quick Guidance/ Gotchas

- feeds.txt goes in root. Store longer or alternative versions elsewhere and move to root when ready

## API Usage

### Search Endpoint
```bash
curl -X GET "http://localhost:8000/search?q=bitcoin" \
  -H "Authorization: Bearer supersecret"
```

### Parameters
- `q` (required): Search query text
- `limit` (default: 10): Number of results to return
- `alpha` (default: 0.5): Hybrid search weighting (0=BM25 only, 1=vector only)
- `rerank_k` (default: 50): Number of results to rerank
- `recency` (default: true): Sort by published date (newest first)

### Examples
```bash
# Basic search
curl -X GET "http://localhost:8000/search?q=health" \
  -H "Authorization: Bearer supersecret"

# Relevance-focused search (no date sorting)
curl -X GET "http://localhost:8000/search?q=bitcoin&recency=false" \
  -H "Authorization: Bearer supersecret"

# More results with higher vector weighting
curl -X GET "http://localhost:8000/search?q=AI&limit=20&alpha=0.8" \
  -H "Authorization: Bearer supersecret"
```

## TODOS:

- [x] Specific versioning on the requirements files
- [ ] Speed up conmsumer
- [ ] Distributed scheduler (Kafka) needs to partition by domains


fluxdemo-fastapi/
├─ docker-compose.yml
├─ feeds.txt
├─ .env.example
├─ producer/
│  ├─ Dockerfile
│  └─ producer.py
├─ consumer/
│  ├─ Dockerfile
│  └─ consumer.py
├─ airflow/
│  ├─ dags/
│  │  └─ repoll_feeds.py
│  └─ Dockerfile
├─ search_api/
│  ├─ Dockerfile
│  └─ main.py
└─ README.md


```bash
feeds.txt → Producer → Kafka topic `feed_urls`
                   ↘︎ hourly (Airflow)
                                    ↓
           Consumer (feedparser → date-normalise → SHA-256 hashes
                     → Word2Vec vectors) ----------------┐
                                                        ↓
                               Weaviate (FeedItem class; BM25 index
                               + vectors; reranker-jinaai module)
                                                        ↓
                                 FastAPI ("/search")  ← Bearer-token
                                                        ↓
                                           Users (hybrid search)
```
