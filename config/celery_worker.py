from celery import Celery
from config.config import settings

# Configure Celery based on available Redis options
broker_url = settings.REDIS_URL
backend_url = settings.REDIS_URL
broker_kwargs = {}
backend_kwargs = {}

# Configure SSL if using Upstash Redis with rediss:// URL
if settings.CELERY_BROKER_USE_SSL:
    broker_kwargs['ssl_cert_reqs'] = 'CERT_NONE'
    backend_kwargs['ssl_cert_reqs'] = 'CERT_NONE'

# Add Upstash REST API configuration if available
if settings.USE_UPSTASH_REDIS:
    # For Upstash Redis, we'll still use the Redis URL for Celery's connection
    # but we'll add additional configuration for our custom client
    broker_kwargs.update({
        'rest_url': settings.UPSTASH_REDIS_REST_URL,
        'rest_token': settings.UPSTASH_REDIS_REST_TOKEN
    })
    backend_kwargs.update({
        'rest_url': settings.UPSTASH_REDIS_REST_URL,
        'rest_token': settings.UPSTASH_REDIS_REST_TOKEN
    })

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
