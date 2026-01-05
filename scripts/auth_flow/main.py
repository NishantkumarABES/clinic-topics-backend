import requests
from utils import *

user_type = "doctor"
verification_type = "email"

phone_verified = verification_type in ["phone", "both"]
email_verified = verification_type in ["email", "both"]

payload_functions = {
    "doctor": generate_doctor_payload,
    "patient": generate_patient_payload
}
payload = payload_functions[user_type](phone_verified=phone_verified, email_verified=email_verified)
log_generated_payload(payload)
if user_type == "doctor":
    files = {
        "license_document": open("data/license_image.jpg", "rb"),
    }
response = requests.post(f"{BASE_URL}/auth/register/{user_type}/", data=payload, files=files if user_type == "doctor" else None)
print("Registration Response:", response.status_code, response.json())