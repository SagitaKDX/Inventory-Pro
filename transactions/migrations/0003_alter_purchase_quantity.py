from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_rename_discount_amount_sale_tax_amount_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='purchase',
            name='quantity',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
