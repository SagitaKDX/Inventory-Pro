from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('slug', django_extensions.db.fields.AutoSlugField(blank=True, editable=False, populate_from='name', unique=True)),
            ],
            options={
                'verbose_name_plural': 'Categories',
            },
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', django_extensions.db.fields.AutoSlugField(blank=True, editable=False, populate_from='name', unique=True)),
                ('name', models.CharField(max_length=50)),
                ('description', models.TextField(max_length=256)),
                ('quantity', models.IntegerField(default=0)),
                ('price', models.FloatField(default=0)),
                ('expiring_date', models.DateTimeField(blank=True, null=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='store.category')),
                ('vendor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.vendor')),
            ],
            options={
                'verbose_name_plural': 'Items',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Delivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name', models.CharField(blank=True, max_length=30, null=True)),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region=None)),
                ('location', models.CharField(blank=True, max_length=20, null=True)),
                ('date', models.DateTimeField()),
                ('is_delivered', models.BooleanField(default=False, verbose_name='Is Delivered')),
                ('item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='store.item')),
            ],
        ),
    ]
