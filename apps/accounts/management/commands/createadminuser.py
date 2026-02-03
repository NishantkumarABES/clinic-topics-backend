import os
from django.core.management.base import BaseCommand
from apps.accounts.models import User

class Command(BaseCommand):
    help = "Create admin user (non-superuser)"

    def handle(self, *args, **kwargs):

        email = os.getenv("INITIAL_ADMIN_EMAIL", "admin@clinic.topics.com")
        password = os.getenv("INITIAL_ADMIN_PASSWORD", "AdminPass123!")

        if not email or not password:
            raise ValueError("INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD must be set")

        # Idempotency check
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING("Admin already exists"))
            return

        User.objects.create_admin_user(
            email=email,
            password=password,
            full_name="Clinic Topics Admin",
            phone="0000000001"
        )

        self.stdout.write(self.style.SUCCESS("Admin user created successfully"))
