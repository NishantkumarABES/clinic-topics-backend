from django.db import migrations, transaction

def generate_order_numbers(apps, schema_editor):
    Order = apps.get_model("commerce", "Order")

    with transaction.atomic():
        orders = Order.objects.select_for_update().order_by("created_at")

        counter = 1
        for order in orders:
            if not order.order_number:
                order.order_number = f"ORD-{str(counter).zfill(8)}"
                order.save(update_fields=["order_number"])
                counter += 1

class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0005_order_order_number"),
    ]

    operations = [
        migrations.RunPython(generate_order_numbers),
    ]