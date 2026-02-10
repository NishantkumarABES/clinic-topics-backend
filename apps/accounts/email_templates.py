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


def password_reset_html(full_name: str | None, otp: str) -> str:
    name = full_name or "User"

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Password Reset OTP</title>
</head>

<body style="margin:0;padding:0;background-color:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
    <tr>
      <td align="center">

        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:10px;
                      padding:40px;box-shadow:0 4px 12px rgba(0,0,0,0.06);">

          <tr>
            <td align="center">

              <h2 style="margin-bottom:10px;color:#1a1a1a;">
                Password Reset Request
              </h2>

              <p style="font-size:16px;color:#444;line-height:1.6;">
                Hello <strong>{name}</strong>,
                <br><br>
                We received a request to reset your password.
                Use the One-Time Password (OTP) below to continue:
              </p>

              <!-- OTP BOX -->
              <div style="
                  margin:30px 0;
                  font-size:34px;
                  letter-spacing:8px;
                  font-weight:bold;
                  color:#0B5ED7;
                  background:#f1f6ff;
                  padding:18px 28px;
                  border-radius:8px;
                  display:inline-block;">
                  {otp}
              </div>

              <p style="font-size:15px;color:#555;">
                This OTP is valid for <strong>5 minutes</strong>.
              </p>

              <p style="font-size:14px;color:#777;margin-top:25px;">
                If you did not request this password reset,
                please ignore this email — your account is still secure.
              </p>

              <hr style="margin:35px 0;border:none;border-top:1px solid #eee;">

              <p style="font-size:13px;color:#999;">
                For security reasons, never share this OTP with anyone.
                ClinicTopics will never ask for your OTP.
              </p>

              <p style="font-size:12px;color:#bbb;margin-top:30px;">
                © {date.today().year} ClinicTopics. All rights reserved.
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
