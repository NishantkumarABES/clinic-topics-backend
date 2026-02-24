import os
from celery import Celery
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(".env", raise_error_if_not_found=True), override=True)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
app = Celery("config")
# Load settings with CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from installed apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")