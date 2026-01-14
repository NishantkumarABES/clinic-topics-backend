import razorpay
from django.conf import settings


class RazorpayService:
    """Shared Razorpay service for all apps."""

    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    def create_order(self, amount: int, currency: str = "INR", receipt: str = None, notes: dict = None) -> dict:
        order_data = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "notes": notes or {},
        }
        return self.client.order.create(data=order_data)

    def verify_payment_signature(self, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
        try:
            self.client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature
            })
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

    def verify_webhook_signature(self, payload: str, signature: str, webhook_secret: str) -> bool:
        try:
            self.client.utility.verify_webhook_signature(payload, signature, webhook_secret)
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

    def fetch_payment(self, payment_id: str) -> dict:
        return self.client.payment.fetch(payment_id)

    def capture_payment(self, payment_id: str, amount: int, currency: str = "INR") -> dict:
        return self.client.payment.capture(payment_id, amount, {"currency": currency})

    def refund_payment(self, payment_id: str, amount: int = None, notes: dict = None) -> dict:
        refund_data = {"notes": notes or {}}
        if amount:
            refund_data["amount"] = amount
        return self.client.payment.refund(payment_id, refund_data)


# Shared singleton instance
razorpay_service = RazorpayService()
