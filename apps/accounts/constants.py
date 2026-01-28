class UserRole:
    DOCTOR = "doctor"
    PATIENT = "patient"
    ADMIN = "admin"

    CHOICES = (
        (DOCTOR, "Doctor"),
        (PATIENT, "Patient"),
        (ADMIN, "Admin"),
    )
    
class UserState:
    CREATED = "created"
    INACTIVE = "inactive"
    ACTIVE = "active"
    DELETED = "deleted"

    CHOICES = (
        (CREATED, "Created"),
        (INACTIVE, "Inactive"),
        (ACTIVE, "Active"),
        (DELETED, "Deleted"),
    )

# accounts/constants.py

class AuthProviderType:
    GOOGLE = "google"
    APPLE = "apple"
    FACEBOOK = "facebook"

    CHOICES = (
        (GOOGLE, "Google"),
        (APPLE, "Apple"),
        (FACEBOOK, "Facebook"),
    )

class DeviceType:
    DEVICE_ANDROID = "android"
    DEVICE_IOS = "ios"
    DEVICE_WEB = "web"

    DEVICE_CHOICES = (
        (DEVICE_ANDROID, "Android"),
        (DEVICE_IOS, "iOS"),
        (DEVICE_WEB, "Web"),
    )