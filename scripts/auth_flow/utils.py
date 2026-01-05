import random
from faker import Faker
from datetime import date
import pandas as pd

fake = Faker("en_IN")  
BASE_URL = "http://localhost:8000/api/v1"
# BASE_URL = "https://clinic-topics-backend.onrender.com/api/v1"


def generate_doctor_payload(phone_verified=False, email_verified=False):
    gender = random.choice(["male", "female"])
    dob = fake.date_of_birth(minimum_age=25, maximum_age=65)
    payload = {
        "full_name": fake.name_male() if gender == "male" else fake.name_female(),
        "email": fake.email(),
        "phone": fake.msisdn()[:10],  # ensure 10-digit Indian number
        "country_code": "+91",
        "password": fake.password(length=10, special_chars=True, digits=True, upper_case=True, lower_case=True),
        "terms_accepted": True,
        "date_of_birth": dob.isoformat(),
        "gender": gender,
        "is_phone_verified": phone_verified,
        "is_email_verified": email_verified,
        "specialization": random.choice([
            "Cardiology", "Neurology", "Orthopedics", "Dermatology", "Pediatrics", "Oncology"
        ]),
        "license_number": fake.bothify(text="????######"),
        "years_of_experience": str(
            random.randint(1, max(1, date.today().year - dob.year - 25))
        ),
    }
    return payload

def generate_patient_payload(phone_verified=False, email_verified=False):
    gender = random.choice(["male", "female"])
    dob = fake.date_of_birth(minimum_age=10, maximum_age=90)
    payload = {
        "full_name": fake.name_male() if gender == "male" else fake.name_female(),
        "email": fake.email(),
        "phone": fake.msisdn()[:10],  # ensure 10-digit Indian number
        "country_code": "+91",      
        "password": fake.password(length=10, special_chars=True, digits=True, upper_case=True, lower_case=True),
        "terms_accepted": True,
        "date_of_birth": dob.isoformat(),
        "gender": gender,
        "is_email_verified": email_verified,
        "is_phone_verified": phone_verified,
        "date_of_birth": dob.isoformat(),
        "gender": gender,
    }
    return payload


def log_generated_payload(payload):
    df = pd.DataFrame([payload])
    df.to_csv(
        "generated_payloads.csv", mode="a", index=False, 
        header=not pd.io.common.file_exists("generated_payloads.csv")
    )


if __name__ == "__main__":
    # Example usage
    # doctor_payload = generate_doctor_payload(phone_verified=True, email_verified=False)
    patient_payload = generate_patient_payload(phone_verified=False, email_verified=True)
    # print("Doctor Payload:", doctor_payload)
    print("Patient Payload:", patient_payload)