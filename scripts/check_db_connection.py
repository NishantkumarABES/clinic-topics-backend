# check database connection
import psycopg2
from psycopg2 import OperationalError

db_config = {
        "dbname": "clinic_topics",
        "user": "postgres-render",
        "password": "oRF5IVpoP8MK4fnyEbwPsjw35z281Q0g",
        "host": "dpg-d55ufc63jp1c73a3oa4g-a",
        "port": 5432,
    }

def check_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(**db_config)
        print("Connection to PostgreSQL DB successful")
    except OperationalError as e:
        print(f"The error '{e}' occurred")
    finally:
        if conn: conn.close()

check_db_connection()

    