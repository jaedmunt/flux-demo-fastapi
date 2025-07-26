FROM python:3.12-slim
RUN pip install kafka-python
COPY feeds.txt /app/feeds.txt
COPY producer.py /app/
WORKDIR /app
CMD ["python", "producer.py"]
