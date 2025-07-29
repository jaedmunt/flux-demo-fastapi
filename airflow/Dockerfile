# airflow/Dockerfile
FROM apache/airflow:2.9.0-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
USER airflow

RUN pip install --no-cache-dir apache-airflow-providers-apache-kafka \
                               weaviate-client==4.4.2
