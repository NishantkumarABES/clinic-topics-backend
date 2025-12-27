import os, base64, hashlib, random
from faker import Faker
from tqdm import tqdm
from datetime import datetime, timedelta, timezone
from typing import List, Dict
# -------------------------------------------------
# DJANGO-COMPATIBLE PASSWORD HASHING (NO DJANGO)
# -------------------------------------------------
def make_django_password(password, iterations=720000):
    salt = base64.b64encode(os.urandom(12)).decode().strip("=")
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        iterations
    )
    hash_ = base64.b64encode(dk).decode().strip()
    return f"pbkdf2_sha256${iterations}${salt}${hash_}"




fake = Faker()
ROLES = ["patient", "doctor"]


def generate_dummy_users_data(size: int, previous_months: int = 3) -> List[Dict]:
    if size <= 0: raise ValueError("Size must be a positive integer")
    if previous_months <= 0: raise ValueError("previous_months must be >= 1")
    users = []
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=previous_months * 30)

    for _ in tqdm(range(size), desc="Generating dummy user data"):
        email = fake.unique.email()
        phone = fake.unique.msisdn()
        gender = random.choice(["male", "female", "other"])
        date_of_birth = fake.date_of_birth(tzinfo=timezone.utc, minimum_age=18, maximum_age=80)
        created_at = fake.date_time_between(
            start_date=start_date,
            end_date=now,
            tzinfo=timezone.utc
        )
        updated_at = fake.date_time_between(
            start_date=created_at,
            end_date=now,
            tzinfo=timezone.utc
        )
        

        user = {
            "email": email, "phone": phone,
            "full_name": fake.name(),
            "password": make_django_password(fake.password(length=12)),
            "role": random.choices(ROLES, weights=[0.7, 0.3], k=1)[0],
            "is_email_verified": random.choice([True, False]),
            "is_phone_verified": random.choice([True, False]),
            "gender": gender, "date_of_birth": date_of_birth,
            "created_at": created_at, "updated_at": updated_at,
        }
        users.append(user)

    return users


# Example usage
if __name__ == "__main__":
    dummy_users = generate_dummy_users_data(size=1000, previous_months=3)
    print(dummy_users[0])
