# consumer/consumer.py
import os, hashlib, datetime as dt, json, logging
from kafka import KafkaConsumer
import feedparser, weaviate
from dateutil import parser as dparse
from gensim.models import KeyedVectors

logging.basicConfig(level=logging.INFO)

# ---- embeddings (Req 7) ----
wv = KeyedVectors.load_word2vec_format("/models/GoogleNews-vectors-negative300.bin.gz", binary=True)

def mean_vector(text: str) -> list[float]:
    tokens = [t for t in text.lower().split() if t in wv]
    return wv.get_mean_vector(tokens).tolist() if tokens else [0.0] * wv.vector_size

# ---- weaviate client ----
client = weaviate.Client(
    url=os.getenv("WEAVIATE_URL", "http://weaviate:8080"),
    additional_headers={"X-JinaAI-Api-Key": os.getenv("JINAAI_APIKEY")}
)

if not client.schema.exists("FeedItem"):
    from weaviate.classes.config import Configure

    client.schema.create(
        "FeedItem",
        vectorizer_config=Configure.Vectorizer.none(),
        inverted_index_config=Configure.InvertedIndex.bm25(),
        reranker_config=Configure.Reranker.jinaai(model="jina-reranker-v1-base-en"),   # ➈
        properties=[
            {"name": "url",           "dataType": ["text"]},
            {"name": "title",         "dataType": ["text"]},
            {"name": "description",   "dataType": ["text"]},
            {"name": "published",     "dataType": ["date"]},
            {"name": "last_accessed", "dataType": ["date"]},
            {"name": "feed_hash",     "dataType": ["text"]},
            {"name": "item_hash",     "dataType": ["text"]},
        ],
    )

# ---- Kafka consumer ----
consumer = KafkaConsumer(
    os.getenv("KAFKA_TOPIC", "feed_urls"),
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
    group_id="rss_ingestors",
    auto_offset_reset="earliest",
)

def sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, default=str).encode()).hexdigest()

for msg in consumer:
    feed_url = msg.value.decode()
    logging.info("Fetching %s", feed_url)
    fp = feedparser.parse(feed_url)
    feed_hash = sha256(fp)            # Req 5
    accessed = dt.datetime.utcnow().isoformat()

    for entry in fp.entries:
        pub = dparse.parse(entry.get("published", accessed)).isoformat()   # Req 3
        item_hash = sha256(
            {"t": entry.title, "d": entry.get("summary"), "p": pub}
        )  # Req 6

        # build vector
        vec = mean_vector(f"{entry.title}. {entry.get('summary', '')}")

        client.data_object.create(
            {
                "url": entry.link,
                "title": entry.title,
                "description": entry.get("summary", ""),
                "published": pub,
                "last_accessed": accessed,        # Req 4
                "feed_hash": feed_hash,
                "item_hash": item_hash,
            },
            class_name="FeedItem",
            vector=vec,
        )
