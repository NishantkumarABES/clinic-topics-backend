import requests
BASE_URL = "http://localhost:8000/api/v1"
# BASE_URL = "https://clinic-topics-backend.onrender.com/api/v1"

payload = {
    "full_name": "Ashok Sharma",
    "email": "Askok.sharma.98@gmail.com",
    "phone": "8112324678",
    "country_code": "+91",
    "password": "MyPass123!",
    "terms_accepted": True,
    "date_of_birth": "1899-07-22",
    "gender": "male",
    "is_phone_verified": True,
    "specialization": "Cardiology",
    "license_number" : "UNNIWDNI23423",
    "years_of_experience": "10"
}

response = requests.post(
    f"{BASE_URL}/auth/register/doctor/",
    data=payload
)

print(response.status_code)
print(response.json())