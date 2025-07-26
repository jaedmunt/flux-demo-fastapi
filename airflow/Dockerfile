# airflow/Dockerfile
FROM apache/airflow:2.9.0-python3.11

# ──[ Install extra system libs only if you need them ]─────────────
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*
USER airflow

# ──[ Airflow provider & any other Python deps ]────────────────────
RUN pip install --no-cache-dir \
        apache-airflow-providers-apache-kafka \
        weaviate-client==4.4.2

# (optional) copy a requirements.txt if you’d rather pin versions here
# COPY requirements.txt /tmp/requirements.txt
# RUN pip install --no-cache-dir -r /tmp/requirements.txt
