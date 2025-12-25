"""
TNSE Celery Application Configuration

Provides Celery application setup for background task processing.

Work Stream: WS-1.6 - Content Collection Pipeline

Requirements addressed:
- Set up Celery/RQ with Redis
- Schedule periodic runs (every 15-30 min)
"""

from celery import Celery

from src.tnse.core.config import get_settings


def create_celery_app() -> Celery:
    """Create and configure the Celery application.

    Returns:
        Configured Celery application instance.
    """
    settings = get_settings()

    app = Celery(
        "tnse",
        broker=settings.celery.broker_url,
        backend=settings.celery.result_backend,
    )

    # Configure Celery settings
    app.conf.update(
        # Timezone
        timezone="UTC",
        enable_utc=True,
        # Serialization - JSON for safety and interoperability
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        # Reliability settings
        task_acks_late=True,  # Acknowledge after task completes
        task_reject_on_worker_lost=True,  # Requeue if worker crashes
        # Task settings
        task_track_started=True,
        task_time_limit=600,  # 10 minute hard limit
        task_soft_time_limit=540,  # 9 minute soft limit
        # Worker settings
        worker_prefetch_multiplier=1,  # One task at a time for fairness
        worker_disable_rate_limits=False,
        # Result settings
        result_expires=86400,  # Results expire after 24 hours
        # Task discovery
        imports=["src.tnse.pipeline.tasks"],
        include=["src.tnse.pipeline.tasks"],
    )

    return app


# Create the default Celery application instance
celery_app = create_celery_app()


# Celery Beat schedule configuration
celery_app.conf.beat_schedule = {
    "collect-content-every-15-minutes": {
        "task": "src.tnse.pipeline.tasks.collect_all_channels",
        "schedule": 900.0,  # 15 minutes in seconds
        "options": {
            "expires": 840.0,  # Expire if not started within 14 minutes
        },
    },
}
