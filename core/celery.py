from celery.schedules import crontab

CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE = {
    "expire-unanswered-calls": {
        "task": "apps.video_calls.tasks.expire_unanswered_calls",
        "schedule": 30.0,
    },

    "mark-inactive-users": {
        "task": "apps.accounts.tasks.mark_inactive_users",
        "schedule": crontab(hour=3, minute=0),  # every day at 3 AM
    },
}
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60