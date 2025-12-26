import psycopg2
import uuid, logging
from tqdm import tqdm
from datetime import datetime, timezone
from utils import make_django_password, generate_dummy_users_data
from sql_commands import INSERT_USER_SQL, IS_SUPERUSER_EXISTS_SQL
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CreateDummyDatabase:
    def __init__(self, dbconfig=None, superuser_email=None, superuser_password=None):
        self.db_config = dbconfig or {
            "dbname": "clinic_topics",
            "user": "postgres",
            "password": "admin",
            "host": "localhost",
            "port": 5432,
        }
        self.superuser_email = superuser_email or "nishant.kumar@qsstechnosoft.com"
        self.superuser_password = superuser_password or "Admin@123"
        self.superuser_phone = "0000000000"
        self.create_superuser()
    
    def create_superuser(self):
        conn = psycopg2.connect(**self.db_config)
        conn.autocommit = True
        cur = conn.cursor()
        now = datetime.now(timezone.utc)
        cur.execute(IS_SUPERUSER_EXISTS_SQL)
        if cur.fetchone()[0]:
            logger.info("Superuser already exists. Skipping creation.")
            cur.close()
            conn.close()
            return

        data = {
            "id": str(uuid.uuid4()),
            "password": make_django_password(self.superuser_password),
            "last_login": None, "is_superuser": True,
            "email": self.superuser_email, "phone": self.superuser_phone,
            "full_name": "System Administrator",
            "is_staff": True, "is_active": True,
            "role": "admin", "state": "active", "terms_accepted": True,
            "terms_accepted_at": now, "terms_version": "1.0.0",
            "is_email_verified": True, "is_phone_verified": True,
            "created_at": now, "updated_at": now,
            "gender": None, "date_of_birth": None
        }

        cur.execute(INSERT_USER_SQL, data)
        logger.info(f"Superuser created: {self.superuser_email}")
        cur.close()
        conn.close()
    
    def create_admin_user(self, email, phone, full_name, password):
        conn = psycopg2.connect(**self.db_config)
        conn.autocommit = True
        cur = conn.cursor()
        now = datetime.now(timezone.utc)

        data = {
            "id": str(uuid.uuid4()),
            "password": make_django_password(password),
            "last_login": None, "is_superuser": False,
            "email": email, "phone": phone,
            "full_name": full_name,
            "is_staff": True, "is_active": True,
            "role": "admin", "state": "active", "terms_accepted": True,
            "terms_accepted_at": now, "terms_version": "1.0.0",
            "is_email_verified": True, "is_phone_verified": True,
            "created_at": now, "updated_at": now,
            "gender": None, "date_of_birth": None
        }

        cur.execute(INSERT_USER_SQL, data)
        logger.info(f"Admin user created: {email}")
        cur.close()
        conn.close()

    def create_system_user(
            self, email, phone, full_name, password, role, is_email_verified, is_phone_verified,
            gender, date_of_birth, created_at=None, updated_at=None,
        ):
        conn = psycopg2.connect(**self.db_config)
        conn.autocommit = True
        cur = conn.cursor()
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        if updated_at is None:
            updated_at = datetime.now(timezone.utc)

        data = {
            "id": str(uuid.uuid4()),
            "password": make_django_password(password),
            "last_login": None, "is_superuser": False,
            "email": email, "phone": phone, "full_name": full_name,
            "is_staff": False, "is_active": True,
            "role": role, "state": "active", "terms_accepted": True,
            "terms_accepted_at": created_at, "terms_version": "1.0.0",
            "is_email_verified": is_email_verified, "is_phone_verified": is_phone_verified,
            "created_at": created_at, "updated_at": updated_at,
            "gender": gender, "date_of_birth": date_of_birth
        }

        cur.execute(INSERT_USER_SQL, data)
        cur.close()
        conn.close()


dummy_db = CreateDummyDatabase()
# dummy_db.create_admin_user(
#     email="clinic_topics@admin.com",
#     phone="0000000001",
#     full_name="Clinic Topics Admin",
#     password="Admin@123"
# )

dummy_user_data = generate_dummy_users_data(size=1357, previous_months=3)
for user in tqdm(dummy_user_data, desc="Creating dummy users"):
    dummy_db.create_system_user(**user)













