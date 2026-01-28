import requests, random
from faker import Faker
from datetime import date


fake = Faker("en_IN")  
BASE_URL = "http://localhost:8000/api/v1"
# BASE_URL = "https://clinic-topics-backend.onrender.com/api/v1"

from exponent_server_sdk import PushClient, PushMessage

def test_expo_token(push_token: str):
    """
    Quick test to verify a single Expo push token.
    Run from Django shell or call manually.
    """

    client = PushClient()

    message = PushMessage(
        to=push_token,
        title="Expo Push Test",
        body="If you see this, Expo push is working 🎉",
        data={"test": "true"},
        sound="default"
    )

    try:
        response = client.publish(message)
    except Exception as e:
        return {"success": False, "error": str(e)}

    if response.is_success():
        return {"success": True, "status": "Delivered"}
    else:
        return {
            "success": False,
            "status": "Failed",
            "details": str(response.details)
        }



test_expo_token(
    push_token="ExponentPushToken[Y0bEdKB1Wele4ksiEI2iG6]",
)






# def generate_doctor_payload(phone_verified=False, email_verified=False):
#     gender = random.choice(["male", "female"])
#     dob = fake.date_of_birth(minimum_age=25, maximum_age=65)
#     payload = {
#         "full_name": fake.name_male() if gender == "male" else fake.name_female(),
#         "email": fake.email(),
#         "phone": fake.msisdn()[:10],  # ensure 10-digit Indian number
#         "country_code": "+91",
#         "password": fake.password(length=10, special_chars=True, digits=True, upper_case=True, lower_case=True),
#         "terms_accepted": True,
#         "date_of_birth": dob.isoformat(),
#         "gender": gender,
#         "is_phone_verified": phone_verified,
#         "is_email_verified": email_verified,
#         "specialization": random.choice([
#             "Cardiology", "Neurology", "Orthopedics", "Dermatology", "Pediatrics", "Oncology"
#         ]),
#         "license_number": fake.bothify(text="????######"),
#         "years_of_experience": str(
#             random.randint(1, max(1, date.today().year - dob.year - 25))
#         ),
#     }
#     return payload

# def generate_patient_payload(phone_verified=False, email_verified=False):
#     gender = random.choice(["male", "female"])
#     dob = fake.date_of_birth(minimum_age=10, maximum_age=90)
#     payload = {
#         "full_name": fake.name_male() if gender == "male" else fake.name_female(),
#         "email": fake.email(),
#         "phone": fake.msisdn()[:10],  # ensure 10-digit Indian number
#         "country_code": "+91",      
#         "password": fake.password(length=10, special_chars=True, digits=True, upper_case=True, lower_case=True),
#         "terms_accepted": True,
#         "date_of_birth": dob.isoformat(),
#         "gender": gender,
#         "is_email_verified": email_verified,
#         "is_phone_verified": phone_verified,
#         "date_of_birth": dob.isoformat(),
#         "gender": gender,
#     }
#     return payload






# print(response.status_code)
# print(response.json())


