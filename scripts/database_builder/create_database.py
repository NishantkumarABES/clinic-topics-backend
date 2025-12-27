import psycopg2
import uuid, logging
from tqdm import tqdm
from datetime import datetime, timezone
from utils import make_django_password, generate_dummy_users_data
from sql_commands import INSERT_USER_SQL, IS_SUPERUSER_EXISTS_SQL
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CreateDummyDatabase:
    def __init__(self, db_url=None, superuser_email=None, superuser_password=None):
        DB_URL = db_url or "postgresql://postgres:admin@localhost:5432/clinic_topics"
        self.conn = psycopg2.connect(DB_URL)
        self.superuser_email = superuser_email or "nishant.kumar@qsstechnosoft.com"
        self.superuser_password = superuser_password or "Admin@123"
        self.superuser_phone = "0000000000"
        self.create_superuser()
    
    def create_superuser(self):
        self.conn.autocommit = True
        cur = self.conn.cursor()
        now = datetime.now(timezone.utc)
        cur.execute(IS_SUPERUSER_EXISTS_SQL)
        if cur.fetchone()[0]:
            logger.info("Superuser already exists. Skipping creation.")
            cur.close()
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
        cur.close()
        logger.info(f"Superuser created: {self.superuser_email}")
        
    
    def create_admin_user(self, email, phone, full_name, password):
        self.conn.autocommit = True
        cur = self.conn.cursor()
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
        

    def create_system_user(
            self, email, phone, full_name, password, role, is_email_verified, is_phone_verified,
            gender, date_of_birth, created_at=None, updated_at=None,
        ):
        
        self.conn.autocommit = True
        cur = self.conn.cursor()
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
    
    def close_connection(self):
        self.conn.close()



RENDER_DB_URL = "postgresql://postgres_render:oRF5IVpoP8MK4fnyEbwPsjw35z281Q0g@dpg-d55ufc63jp1c73a3oa4g-a.oregon-postgres.render.com/clinic_topics"
dummy_db = CreateDummyDatabase(RENDER_DB_URL)
# dummy_db.create_admin_user(
#     email="admin@clinic.topics.com",
#     phone="0000000001",
#     full_name="Clinic Topics Admin",
#     password="Admin@123"
# )

dummy_user_data = generate_dummy_users_data(size=234, previous_months=3)
for user in tqdm(dummy_user_data, desc="Creating dummy users"):
    dummy_db.create_system_user(**user)
logger.info("Dummy database creation completed.")
dummy_db.close_connection()











