INSERT_USER_SQL = """
INSERT INTO accounts_user (
    id, password, last_login, is_superuser, email, phone, full_name, is_staff, is_active, role, state, terms_accepted, 
    terms_accepted_at, terms_version, is_email_verified, is_phone_verified, created_at, updated_at, gender, date_of_birth
)
VALUES (
    %(id)s, %(password)s, %(last_login)s, %(is_superuser)s, %(email)s, %(phone)s, %(full_name)s, %(is_staff)s, %(is_active)s,
    %(role)s, %(state)s, %(terms_accepted)s, %(terms_accepted_at)s, %(terms_version)s, %(is_email_verified)s, %(is_phone_verified)s,
    %(created_at)s, %(updated_at)s, %(gender)s, %(date_of_birth)s
);
"""


IS_SUPERUSER_EXISTS_SQL = """
SELECT EXISTS (SELECT 1 FROM accounts_user WHERE is_superuser = True);
"""

INSERT_SQL = """
INSERT INTO doctor_profiles (
    user_id,
    created_at,
    updated_at,
    year_of_experience,
    license_number,
    verification_status,
    clinic_name,
    clinic_address
)
VALUES (
    %(user_id)s,
    %(created_at)s,
    %(updated_at)s,
    %(year_of_experience)s,
    %(license_number)s,
    %(verification_status)s,
    %(clinic_name)s,
    %(clinic_address)s
);
"""

INSERT_INTO_DOCTOR_PROFILES_SQL = """
INSERT INTO profiles_doctorprofile (
    id,
    user_id,
    created_at,
    updated_at,
    years_of_experience,
    license_number,
    verification_status,
    clinic_name,
    clinic_address,
    license_document,
    awards,
    bio,
    consultation_fee,
    about_completed,
    availability_completed, 
    license_completed, 
    overview_completed, 
    practice_completed, 
    professional_completed,
    locked_sections
)
VALUES (
    %(id)s,
    %(user_id)s,
    %(created_at)s,
    %(updated_at)s,
    %(years_of_experience)s,
    %(license_number)s,
    %(verification_status)s,
    %(clinic_name)s,
    %(clinic_address)s,
    %(license_document)s,
    %(awards)s,
    %(bio)s,
    %(consultation_fee)s,
    %(about_completed)s,
    %(availability_completed)s,
    %(license_completed)s,
    %(overview_completed)s,
    %(practice_completed)s,
    %(professional_completed)s,
    %(locked_sections)s
);
"""