
from django.db import migrations
import uuid


def fill_uuids(apps, schema_editor):
    Product = apps.get_model("core", "Product")

    # заполним всем, у кого uuid пустой/NULL
    for p in Product.objects.filter(uuid__isnull=True):
        p.uuid = uuid.uuid4()
        p.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_merchcategory_order_orderitem_product_colors_and_more"),
    ]

    operations = [
        migrations.RunPython(fill_uuids, migrations.RunPython.noop),
    ]