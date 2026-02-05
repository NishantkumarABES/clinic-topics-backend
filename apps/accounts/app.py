import os
from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        self._validate_apple_oauth_config()

    def _validate_apple_oauth_config(self):
        """
        Validate Apple OAuth configuration at startup.
        Raises ImproperlyConfigured if the private key file is missing.
        """
        private_key_path = os.getenv("APPLE_PRIVATE_KEY_PATH")
        
        # Only validate if Apple OAuth is configured
        if private_key_path:
            if not os.path.isfile(private_key_path):
                raise ImproperlyConfigured(
                    f"Apple OAuth Error: AuthKey.p8 file not found at '{private_key_path}'. "
                    f"Please ensure the file exists or remove APPLE_PRIVATE_KEY_PATH from environment variables."
                )
            
            # Optional: Validate all required Apple OAuth env vars are present
            required_vars = ["APPLE_TEAM_ID", "APPLE_CLIENT_ID", "APPLE_KEY_ID"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            
            if missing_vars:
                raise ImproperlyConfigured(
                    f"Apple OAuth Error: Missing required environment variables: {', '.join(missing_vars)}. "
                    f"Either set all Apple OAuth variables or remove APPLE_PRIVATE_KEY_PATH to disable Apple Sign In."
                )

