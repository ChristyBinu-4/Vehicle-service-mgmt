# Generated manually for adding landing page image fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_systemsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='landing_hero_image',
            field=models.ImageField(blank=True, help_text='Hero image for landing page (main banner image)', null=True, upload_to='system/landing/'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='landing_service_image',
            field=models.ImageField(blank=True, help_text='Service image for landing page (Why Choose Us section)', null=True, upload_to='system/landing/'),
        ),
    ]
