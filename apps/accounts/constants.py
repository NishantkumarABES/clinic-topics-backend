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
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    DELETED = "deleted"

    CHOICES = (
        (CREATED, "Created"),
        (ACTIVE, "Active"),
        (SUSPENDED, "Suspended"),
        (DEACTIVATED, "Deactivated"),
        (DELETED, "Deleted"),
    )
