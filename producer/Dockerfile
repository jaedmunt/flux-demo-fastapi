# producer/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "producer.py"]
