from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "smart_doc_qa",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,            # Re-queue on worker crash
    worker_prefetch_multiplier=1,   # One task at a time per worker — fair for heavy tasks
    task_routes={
        "app.workers.tasks.process_document": {"queue": "documents"},
    },
)
