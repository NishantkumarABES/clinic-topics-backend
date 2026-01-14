"""
Commerce Services

This module provides service layer functions for commerce operations.
"""
import razorpay
from django.conf import settings


def cart_requires_prescription(cart):
    items = cart.items.filter(saved_for_later=False)
    for item in items:
        if item.product.is_prescription_required and not item.prescription:
            return True
    return False


class RazorpayService:
    """Service class for Razorpay payment operations."""

    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    def create_order(self, amount: int, currency: str = "INR", receipt: str = None, notes: dict = None) -> dict:
        """
        Create a Razorpay order.

        Args:
            amount: Amount in paise (smallest currency unit). e.g., 50000 for ₹500
            currency: Currency code (default: INR)
            receipt: Unique receipt ID for the order
            notes: Additional notes (optional)

        Returns:
            dict: Razorpay order response containing order_id, amount, currency, etc.
        """
        order_data = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "notes": notes or {},
        }
        return self.client.order.create(data=order_data)

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str
    ) -> bool:
        """
        Verify the payment signature from Razorpay.

        Args:
            razorpay_order_id: The Razorpay order ID
            razorpay_payment_id: The Razorpay payment ID
            razorpay_signature: The signature provided by Razorpay

        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            self.client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

    def verify_webhook_signature(self, payload: str, signature: str, webhook_secret: str) -> bool:
        """
        Verify webhook signature from Razorpay.

        Args:
            payload: The raw request body
            signature: X-Razorpay-Signature header value
            webhook_secret: Webhook secret from Razorpay dashboard

        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            self.client.utility.verify_webhook_signature(payload, signature, webhook_secret)
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

    def fetch_payment(self, payment_id: str) -> dict:
        """
        Fetch payment details from Razorpay.

        Args:
            payment_id: The Razorpay payment ID

        Returns:
            dict: Payment details
        """
        return self.client.payment.fetch(payment_id)

    def capture_payment(self, payment_id: str, amount: int, currency: str = "INR") -> dict:
        """
        Capture an authorized payment.

        Args:
            payment_id: The Razorpay payment ID
            amount: Amount to capture in paise
            currency: Currency code

        Returns:
            dict: Capture response
        """
        return self.client.payment.capture(payment_id, amount, {"currency": currency})

    def refund_payment(self, payment_id: str, amount: int = None, notes: dict = None) -> dict:
        """
        Initiate a refund for a payment.

        Args:
            payment_id: The Razorpay payment ID
            amount: Amount to refund in paise (optional, defaults to full refund)
            notes: Additional notes (optional)

        Returns:
            dict: Refund response
        """
        refund_data = {"notes": notes or {}}
        if amount:
            refund_data["amount"] = amount
        return self.client.payment.refund(payment_id, refund_data)


# Singleton instance for easy import
razorpay_service = RazorpayService()