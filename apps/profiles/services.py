def update_doctor_section_completion(profile, section):
    rules = {
        "overview": lambda p: bool(p.specializations and p.years_of_experience),
        "professional": lambda p: bool(p.qualifications),
        "license": lambda p: bool(p.license_number and p.license_document),
        "practice": lambda p: bool(p.clinic_name and p.consultation_fee),
        "availability": lambda p: bool(p.available_days and p.available_time_slots),
        "about": lambda p: bool(p.bio),
    }

    completed = rules[section](profile)
    setattr(profile, f"{section}_completed", completed)
    profile.save(update_fields=[f"{section}_completed"])

def update_patient_section_completion(profile, section):
    rules = {
        "personal": lambda p: bool(p.blood_group and p.address),
        "medical": lambda p: bool(
            p.medical_history or
            p.current_medications or
            p.allergies or
            p.chronic_conditions
        ),
        "emergency": lambda p: bool(
            p.emergency_contact_name and
            p.emergency_contact_phone
        ),
        "insurance": lambda p: bool(
            p.insurance_provider and p.insurance_policy_number
        ),
    }

    completed = rules[section](profile)
    setattr(profile, f"{section}_completed", completed)
    profile.save(update_fields=[f"{section}_completed"])
