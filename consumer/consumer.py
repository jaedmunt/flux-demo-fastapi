# consumer/consumer.py
import os, hashlib, datetime as dt, json, logging
from kafka import KafkaConsumer
import feedparser, weaviate
from dateutil import parser as dparse

logging.basicConfig(level=logging.INFO)

# ---- embeddings (Req 7) ----
try:
    from sentence_transformers import SentenceTransformer
    
    # Load a pre-trained sentence transformer model
    model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dimensional embeddings
    
    logging.info("Loaded sentence transformer model: all-MiniLM-L6-v2")
    
    def mean_vector(text: str) -> list[float]:
        # Get embeddings for the text
        embeddings = model.encode(text)
        return embeddings.tolist()
            
except Exception as e:
    logging.warning(f"Error loading sentence transformer model: {e}, using zero vectors")
    def mean_vector(text: str) -> list[float]:
        return [0.0] * 384  # Default 384-dimensional zero vector

# ---- weaviate client ----
client = weaviate.WeaviateClient(
    connection_params=weaviate.connect.ConnectionParams.from_url(
        os.getenv("WEAVIATE_URL", "http://weaviate:8080"),
        grpc_port=50051
    ),
    additional_headers={"X-JinaAI-Api-Key": os.getenv("JINAAI_APIKEY")}
)

# Connect to Weaviate
client.connect()

# Check if collection exists, if not create it
try:
    client.collections.get("FeedItem")
    logging.info("FeedItem collection already exists")
except:
    logging.info("Creating FeedItem collection")
    from weaviate.classes.config import Configure

    client.collections.create(
        "FeedItem",
        vectorizer_config=Configure.Vectorizer.none(),
        inverted_index_config=Configure.InvertedIndex.bm25(),
        reranker_config=Configure.Reranker.jinaai(model="jina-reranker-v1-base-en"),
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

        client.collections.get("FeedItem").data.insert(
            {
                "url": entry.link,
                "title": entry.title,
                "description": entry.get("summary", ""),
                "published": pub,
                "last_accessed": accessed,        # Req 4
                "feed_hash": feed_hash,
                "item_hash": item_hash,
            },
            vector=vec,
        )
