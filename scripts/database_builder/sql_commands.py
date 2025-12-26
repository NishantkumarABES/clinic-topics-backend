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