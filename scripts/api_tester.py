import requests
BASE_URL = "http://localhost:8000/api/v1/"

payload = {
    "full_name": "Rohan Sharma",
    "email": "rohan.sharma.98@gmail.com",
    "phone": "8122335678",
    "country_code": "+91",
    "password": "MyPass123!",
    "terms_accepted": True,
    "date_of_birth": "1999-07-22",
    "gender": "male",
    "is_phone_verified": True
}

response = requests.post(
    "http://localhost:8000/api/v1/auth/register/patient/",
    data=payload
)

print(response.status_code)
print(response.json())