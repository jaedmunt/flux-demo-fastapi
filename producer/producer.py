# producer/producer.py
import os, pathlib, time
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# Retry connection to Kafka
max_retries = 10
retry_delay = 5

for attempt in range(max_retries):
    try:
        producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            value_serializer=lambda v: v.encode()
        )
        print(f"Successfully connected to Kafka on attempt {attempt + 1}")
        break
    except NoBrokersAvailable:
        if attempt < max_retries - 1:
            print(f"Failed to connect to Kafka, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
        else:
            print("Failed to connect to Kafka after all retries")
            raise
    except Exception as e:
        print(f"Unexpected error connecting to Kafka: {e}")
        raise

topic = os.getenv("KAFKA_TOPIC", "feed_urls")

for url in pathlib.Path("/app/feeds.txt").read_text().splitlines():
    if url.strip():
        producer.send(topic, url.strip())
        print(f"Queued {url}")
        time.sleep(0.2)          # small throttle

producer.flush()
