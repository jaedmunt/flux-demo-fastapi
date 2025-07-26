# producer/producer.py
import os, pathlib, time
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
    value_serializer=lambda v: v.encode()
)
topic = os.getenv("KAFKA_TOPIC", "feed_urls")

for url in pathlib.Path("/app/feeds.txt").read_text().splitlines():
    if url.strip():
        producer.send(topic, url.strip())
        print(f"Queued {url}")
        time.sleep(0.2)          # small throttle

producer.flush()
