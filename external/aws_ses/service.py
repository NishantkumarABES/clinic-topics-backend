import os, boto3
import logging

logging.basicConfig(level=logging.INFO)


class EmailClient:
    def __init__(self, aws_access_key, aws_secret_key, aws_region):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_region = aws_region
        self.client = boto3.client(
            "ses", region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key
        )
    
    def _create_message(self, subject, body_text, body_html=None):
        message = {
            "Subject": {"Data": subject},
            "Body": {
                "Text": {"Data": body_text}
            }
        }
        if body_html:
            message["Body"]["Html"] = {"Data": body_html}
        return message
    
    def send_email(self, sender, recipient, subject, body_text, body_html=None):
        message = self._create_message(subject, body_text, body_html)
        try:
            response = self.client.send_email(
                Source=sender,
                Destination={"ToAddresses": [recipient]},
                Message=message
            )
            logging.info("✅ Email sent successfully! Message ID: %s", response["MessageId"])
            return response
        except Exception as e:
            logging.error("❌ Failed to send email: %s", e)


email_client = EmailClient(
    aws_access_key=os.environ.get("AWS_ACCESS_KEY"),
    aws_secret_key=os.environ.get("AWS_SECRET_KEY"),
    aws_region=os.environ.get("AWS_REGION")
)
