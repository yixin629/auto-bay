from celery import Celery

from app.config import settings

celery_app = Celery(
    "autobay",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.sync_*": {"queue": "sync"},
        "app.workers.tasks.ai_*": {"queue": "ai"},
        "app.workers.tasks.*": {"queue": "default"},
    },
)

celery_app.conf.beat_schedule = {
    "sync-orders-every-5min": {
        "task": "app.workers.tasks.sync_orders.sync_all_orders",
        "schedule": 300.0,
    },
    "sync-inventory-every-15min": {
        "task": "app.workers.tasks.sync_inventory.sync_all_inventory",
        "schedule": 900.0,
    },
    "update-exchange-rates-daily": {
        "task": "app.workers.tasks.update_exchange_rates.fetch_rates",
        "schedule": 86400.0,
    },
    "recalculate-prices-hourly": {
        "task": "app.workers.tasks.update_pricing.recalculate_all_prices",
        "schedule": 3600.0,
    },
}

celery_app.autodiscover_tasks(["app.workers.tasks"])
