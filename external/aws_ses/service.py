import os, boto3
import logging
logger = logging.getLogger(__name__)

class EmailClient:
    def __init__(self):
        self.client = boto3.client(
            "ses", region_name=os.environ.get("AWS_REGION"),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_KEY"),
        )
        self.sender = os.environ.get("SES_SENDER_EMAIL")  # verified sender

    def send_email(self, recipient, subject, body_text, body_html=None):
        message = {
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body_text}},
        }
        if body_html:
            message["Body"]["Html"] = {"Data": body_html}

        try:
            response = self.client.send_email(
                Source=self.sender,
                Destination={"ToAddresses": [recipient]},
                Message=message
            )
            logger.info("SES Email sent: %s", response["MessageId"])
            return response
        except Exception as e:
            logger.error("SES Email failed: %s", str(e))
            raise
