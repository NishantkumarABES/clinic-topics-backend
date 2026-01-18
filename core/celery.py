from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "expire-unanswered-calls": {
        "task": "apps.video_calls.tasks.expire_unanswered_calls",
        "schedule": 30.0,  # runs every 30 seconds
    }
}
