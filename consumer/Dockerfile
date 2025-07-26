FROM python:3.12-slim
RUN apt-get update && apt-get install -y gcc && \
    pip install kafka-python feedparser python-dateutil gensim weaviate-client
COPY consumer.py /app/
WORKDIR /app
CMD ["python", "consumer.py"]
