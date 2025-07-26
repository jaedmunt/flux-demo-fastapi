from airflow import DAG
from airflow.providers.apache.kafka.operators.produce import ProduceToTopicOperator
from airflow.utils.dates import days_ago
from datetime import datetime

with DAG(
    dag_id="repoll_feeds",
    description="Re-queue RSS urls every hour",
    start_date=days_ago(1),
    schedule_interval="0 * * * *",       # hourly
    catchup=False,
) as dag:
    ProduceToTopicOperator(
        task_id="enqueue_links",
        topic="feed_urls",
        kafka_config_id="kafka_default",
        producer_function=lambda: [
            u.strip() for u in open("/opt/airflow/feeds.txt") if u.strip()
        ],
    )
