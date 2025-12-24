import os, sys
from dotenv import load_dotenv, find_dotenv 
load_dotenv(find_dotenv("secrets/.env", raise_error_if_not_found=True), override=True)

SETTINGS_MODULE = os.getenv('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', SETTINGS_MODULE)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()