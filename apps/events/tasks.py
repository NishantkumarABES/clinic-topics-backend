from celery import shared_task
from apps.events.models import Event


@shared_task
def update_event_statuses():
    """
    Runs daily to refresh status of all active events.
    """

    events = Event.objects.filter(is_active=True)

    updated_count = 0

    for event in events:
        new_status = event.calculate_status()
        if event.status != new_status:
            event.status = new_status
            event.save(update_fields=["status"])
            updated_count += 1

    return f"{updated_count} events updated."