# check database connection
import psycopg2
from psycopg2 import OperationalError

DB_URL = "postgresql://postgres_render:oRF5IVpoP8MK4fnyEbwPsjw35z281Q0g@dpg-d55ufc63jp1c73a3oa4g-a.oregon-postgres.render.com/clinic_topics"
def check_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        print("Connection to PostgreSQL DB successful")
    except OperationalError as e:
        print(f"The error '{e}' occurred")
    finally:
        if conn: conn.close()

check_db_connection()

    