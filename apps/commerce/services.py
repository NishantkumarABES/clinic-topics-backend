def cart_requires_prescription(cart):
    items = cart.items.filter(saved_for_later=False)
    for item in items:
        if item.product.is_prescription_required and not item.prescription:
            return True
    return False