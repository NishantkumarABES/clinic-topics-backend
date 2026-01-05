from django.db import transaction
from .models import StaticPageVersion


def publish_version(version_obj: StaticPageVersion):
    with transaction.atomic():
        # Unpublish existing versions
        StaticPageVersion.objects.filter(
            page=version_obj.page,
            is_published=True
        ).update(is_published=False)

        # Publish selected version
        version_obj.is_published = True
        version_obj.save()
