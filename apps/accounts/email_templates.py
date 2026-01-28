from datetime import date


def otp_email_html(full_name: str | None, otp: str) -> str:
    name = full_name or "User"
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Email Verification</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:40px 0;">
        <table width="600" style="background:#ffffff;border-radius:8px;padding:30px;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
          <tr>
            <td style="text-align:center;">
              <h2 style="color:#222;">Verify Your Email</h2>
              <p style="font-size:16px;color:#555;">
                Hello {name},<br><br>
                Use the following verification code to complete your sign-up:
              </p>
              <div style="margin:30px 0;">
                <span style="font-size:32px;letter-spacing:6px;font-weight:bold;color:#0B5ED7;">
                  {otp}
                </span>
              </div>
              <p style="font-size:14px;color:#777;">
                This code expires in 5 minutes.<br>
                If you didn’t request this, please ignore this email.
              </p>
              <p style="font-size:13px;color:#aaa;margin-top:30px;">
                {date.today().year} © ClinicTopics
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def password_reset_html(full_name: str | None, reset_link: str) -> str:
    name = full_name or "User"
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Password Reset</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:40px 0;">
        <table width="600" style="background:#ffffff;border-radius:8px;padding:30px;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
          <tr>
            <td style="text-align:center;">
              <h2 style="color:#222;">Reset Your Password</h2>
              <p style="font-size:16px;color:#555;">
                Hello {name},<br><br>
                Click the button below to reset your password:
              </p>
              <div style="margin:30px 0;">
                <a href="{reset_link}"
                   style="background:#0B5ED7;color:#fff;text-decoration:none;
                          padding:12px 24px;border-radius:5px;
                          font-size:16px;display:inline-block;">
                  Reset Password
                </a>
              </div>
              <p style="font-size:14px;color:#777;">
                This link expires in 15 minutes.<br>
                If you didn’t request a password reset, ignore this email.
              </p>
              <p style="font-size:13px;color:#aaa;margin-top:30px;">
                {date.today().year} © ClinicTopics
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def doctor_invitation_html(full_name: str, email: str, temp_password: str) -> str:
    name = full_name or "Doctor"
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Doctor Invitation</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:40px 0;">
        <table width="600" style="background:#ffffff;border-radius:8px;padding:30px;">
          <tr>
            <td style="text-align:center;">

              <!-- Logo -->
              <img 
                src="https://admin-panel-frontend-2yrl.onrender.com/src/assets/logo.svg"
                alt="ClinicTopics Logo"
                style="max-width:180px;height:auto;margin-bottom:20px;"
              />

              <h2 style="color:#222;">You're Invited to ClinicTopics</h2>
              <p style="font-size:16px;color:#555;">
                Hello Dr. {name},<br><br>
                An administrator has created your account on ClinicTopics.
              </p>
              <div style="margin:20px 0;font-size:15px;color:#333;">
                <strong>Login Email:</strong> {email}<br>
                <strong>Temporary Password:</strong> {temp_password}
              </div>
              <p style="font-size:14px;color:#777;">
                Please log in using the ClinicTopics mobile app and change your password immediately after login.
              </p>
              <p style="font-size:13px;color:#aaa;margin-top:30px;">
                {date.today().year} © ClinicTopics
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
