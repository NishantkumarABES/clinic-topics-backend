from apps.commerce.constants import OrderStatus, ProductCategory

def classify_refund_case(order):

    if order.payment_method == "cod":
        return "cod"

    if order.status in [OrderStatus.PAID, OrderStatus.PROCESSING]:
        return "cancel_before_shipping"

    if order.status == OrderStatus.SHIPPED:
        return "in_transit"

    if order.status == OrderStatus.DELIVERED:

        if order.items.filter(
            product__category=ProductCategory.MEDICINE
        ).exists():
            return "medicine_delivered"

        return "equipment_delivered"

    return "other"