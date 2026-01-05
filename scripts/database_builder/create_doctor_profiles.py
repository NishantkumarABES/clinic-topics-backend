import psycopg2
import pandas as pd
import uuid, logging, random
from tqdm import tqdm
from faker import Faker
from datetime import timedelta
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from sql_commands import INSERT_INTO_DOCTOR_PROFILES_SQL

def generate_consultation_fee():
    return random.randint(500, 5000)

DB_URL = "postgresql://postgres:admin@localhost:5432/clinic_topics"
conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()
doctor_profiles_df = pd.read_csv("fake_doctor_profiles.csv")
for _, row in tqdm(doctor_profiles_df.iterrows(), total=len(doctor_profiles_df), desc="Inserting doctor profiles"):
    row['id'] = str(uuid.uuid4())
    row['license_document'] = "media/licenses/license_image.jpg"
    row['awards'] = ''
    row['bio'] = ''
    row['consultation_fee'] = generate_consultation_fee()
    row['about_completed'] = False
    row['availability_completed'] = False
    row['license_completed'] = False
    row['overview_completed'] = False
    row['practice_completed'] = False
    row['professional_completed'] = False
    row['locked_sections'] = []
    cur.execute(
        INSERT_INTO_DOCTOR_PROFILES_SQL,
        row.to_dict()
    )








# doctor_users = pd.read_csv("data_doctors.csv")[['id', 'created_at']]
# existed_id_index = doctor_users[doctor_users['id']=='4eabc263-6512-48e7-87af-97b43a2a0db1'].index
# doctor_users = doctor_users.drop(index=existed_id_index)

# fake = Faker()
# Faker.seed(42)
# random.seed(42)
# doctor_users['created_at'] = pd.to_datetime(doctor_users['created_at'])

# def generate_updated_at(created_at):
#     max_days = 365
#     delta_days = random.randint(0, max_days)
#     return created_at + timedelta(days=delta_days)

# def generate_years_of_experience(created_at):
#     return random.randint(1, 30)

# # -----------------------------
# # Generate fake profile data
# # -----------------------------
# profiles = []

# for _, row in doctor_users.iterrows():
#     created_at = row['created_at']

#     profiles.append({
#         "user_id": row['id'],
#         "created_at": created_at,
#         "updated_at": generate_updated_at(created_at),
#         "year_of_experience": generate_years_of_experience(created_at),
#         "license_number": fake.bothify(text="LIC-#####-????").upper(),
#         "verification_status": random.choices(["pending", "approved", "rejected"], weights=[0.5, 0.37, 0.13], k=1)[0],
#         "clinic_name": fake.company(),
#         "clinic_address": fake.address().replace("\n", ", ")
#     })


# doctor_profiles_df = pd.DataFrame(profiles)
# doctor_profiles_df.to_csv("fake_doctor_profiles.csv", index=False)
# print("✅ Fake doctor profile data generated successfully!")
# print(doctor_profiles_df.head())

