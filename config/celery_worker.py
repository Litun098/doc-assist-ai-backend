from celery import Celery

# For development, use SQLite-based broker and backend
import os

# Create directory for Celery results if it doesn't exist
celery_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'celery')
os.makedirs(celery_dir, exist_ok=True)

# Use SQLite for both broker and backend
sqlite_db_path = os.path.join(celery_dir, 'celery.sqlite')

print("Using SQLite-based broker for Celery (development mode)")
broker_url = f'sqla+sqlite:///{sqlite_db_path}'
backend_url = f'db+sqlite:///{sqlite_db_path}'

# No special kwargs needed for SQLite
broker_kwargs = {}
backend_kwargs = {}

celery_app = Celery(
    "anydocai",
    broker=broker_url,
    backend=backend_url,
    broker_transport_options=broker_kwargs,
    backend_transport_options=backend_kwargs,
    include=["app.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
)

if __name__ == "__main__":
    celery_app.start()
