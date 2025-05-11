
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sale',
            old_name='discount_amount',
            new_name='tax_amount',
        ),
        migrations.RenameField(
            model_name='sale',
            old_name='discount_percentage',
            new_name='tax_percentage',
        ),
    ]
