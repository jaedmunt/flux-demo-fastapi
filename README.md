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
                                 FastAPI (“/search”)  ← Bearer-token
                                                        ↓
                                           Users (hybrid search)
```
