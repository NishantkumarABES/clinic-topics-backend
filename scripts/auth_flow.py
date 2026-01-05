import requests

BASE_URL = "http://localhost:8000/api/v1"
# BASE_URL = "https://clinic-topics-backend.onrender.com/api/v1"
payload = {
    "full_name": "Nishant Sharma",
    "email": "nishant.sharma.98@gmail.com",
    "phone": "8112334678",
    "country_code": "+91",
    "password": "12345",
    "terms_accepted": True,
    "date_of_birth": "1899-07-22",
    "gender": "male",
    "is_phone_verified": True,
    "specialization": "Cardiology",
    "license_number" : "UNNIWDNI23423",
    "years_of_experience": "10"
}

file = {
    "license_document": open("C:\\Users\\QSS\\Desktop\\Clinic Topics\\clinic-topics-backend\\media\\licenses\\license_image.jpg", "rb")
}

response = requests.post(f"{BASE_URL}/auth/register/doctor/", data=payload, files=file)
print(response.status_code)
print(response.json())

#