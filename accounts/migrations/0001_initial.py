
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import imagekit.models.fields
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=256)),
                ('last_name', models.CharField(blank=True, max_length=256, null=True)),
                ('address', models.TextField(blank=True, max_length=256, null=True)),
                ('email', models.EmailField(blank=True, max_length=256, null=True)),
                ('phone', models.CharField(blank=True, max_length=30, null=True)),
                ('loyalty_points', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'Customers',
            },
        ),
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
                ('slug', django_extensions.db.fields.AutoSlugField(blank=True, editable=False, populate_from='name', unique=True, verbose_name='Slug')),
                ('phone_number', models.BigIntegerField(blank=True, null=True, verbose_name='Phone Number')),
                ('address', models.CharField(blank=True, max_length=50, null=True, verbose_name='Address')),
            ],
            options={
                'verbose_name': 'Vendor',
                'verbose_name_plural': 'Vendors',
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', django_extensions.db.fields.AutoSlugField(blank=True, editable=False, populate_from='email', unique=True, verbose_name='Account ID')),
                ('profile_picture', imagekit.models.fields.ProcessedImageField(default='profile_pics/default.jpg', upload_to='profile_pics')),
                ('telephone', phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region=None, verbose_name='Telephone')),
                ('email', models.EmailField(blank=True, max_length=150, null=True, verbose_name='Email')),
                ('first_name', models.CharField(blank=True, max_length=30, verbose_name='First Name')),
                ('last_name', models.CharField(blank=True, max_length=30, verbose_name='Last Name')),
                ('status', models.CharField(choices=[('INA', 'Inactive'), ('A', 'Active'), ('OL', 'On leave')], default='INA', max_length=12, verbose_name='Status')),
                ('role', models.CharField(blank=True, choices=[('OP', 'Operative'), ('EX', 'Executive'), ('AD', 'Admin')], max_length=12, null=True, verbose_name='Role')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Profile',
                'verbose_name_plural': 'Profiles',
                'ordering': ['slug'],
            },
        ),
    ]
