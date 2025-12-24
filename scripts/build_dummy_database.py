import psycopg2
import uuid
from datetime import datetime
from django.contrib.auth.hashers import make_password  
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# DATABASE CONFIG (EDIT AS NEEDED)
# -------------------------------------------------
DB_CONFIG = {
    "dbname": "clinic_topics",
    "user": "postgres",
    "password": "admin",
    "host": "localhost",
    "port": 5432,
}

SUPERUSER_EMAIL = "nishant.kumar@qsstechnosoft.com"
SUPERUSER_PASSWORD = "Admin@123"
SUPERUSER_PHONE = "0000000000"

# -------------------------------------------------
# SQL
# -------------------------------------------------
CHECK_USER_SQL = """
SELECT 1 FROM accounts_user WHERE email = %s;
"""

INSERT_USER_SQL = """
INSERT INTO accounts_user (
    id,
    password,
    last_login,
    is_superuser,
    email,
    phone,
    full_name,
    is_staff,
    is_active,
    role,
    state,
    terms_accepted,
    terms_accepted_at,
    terms_version,
    is_email_verified,
    is_phone_verified,
    created_at,
    updated_at
)
VALUES (
    %(id)s,
    %(password)s,
    %(last_login)s,
    %(is_superuser)s,
    %(email)s,
    %(phone)s,
    %(full_name)s,
    %(is_staff)s,
    %(is_active)s,
    %(role)s,
    %(state)s,
    %(terms_accepted)s,
    %(terms_accepted_at)s,
    %(terms_version)s,
    %(is_email_verified)s,
    %(is_phone_verified)s,
    %(created_at)s,
    %(updated_at)s
);
"""

# -------------------------------------------------
# MAIN LOGIC
# -------------------------------------------------
def create_superuser():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    # 1️⃣ Check if user exists
    cur.execute(CHECK_USER_SQL, (SUPERUSER_EMAIL,))
    if cur.fetchone():
        logger.info("Superuser already exists.")
        cur.close()
        conn.close()
        return

    # 2️⃣ Prepare values
    now = datetime.utcnow()

    data = {
        "id": str(uuid.uuid4()),
        "password": make_password(SUPERUSER_PASSWORD),
        "last_login": None,
        "is_superuser": True,
        "email": SUPERUSER_EMAIL,
        "phone": SUPERUSER_PHONE,
        "full_name": "System Administrator",
        "is_staff": True,
        "is_active": True,
        "role": "admin",
        "state": "active",
        "terms_accepted": True,
        "terms_accepted_at": now,
        "terms_version": "1.0.0",
        "is_email_verified": True,
        "is_phone_verified": True,
        "created_at": now,
        "updated_at": now,
    }

    # 3️⃣ Insert
    cur.execute(INSERT_USER_SQL, data)

    logger.info(f"Superuser created: {SUPERUSER_EMAIL}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    create_superuser()
