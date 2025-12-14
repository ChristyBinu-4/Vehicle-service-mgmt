# Generated migration to update User role choices to uppercase

from django.db import migrations, models


def update_role_values_to_uppercase(apps, schema_editor):
    """
    Data migration: Convert existing lowercase role values to uppercase.
    """
    User = apps.get_model('accounts', 'User')
    role_mapping = {
        'user': 'USER',
        'servicer': 'SERVICER',
        'admin': 'ADMIN',
    }
    
    for user in User.objects.all():
        if user.role in role_mapping:
            user.role = role_mapping[user.role]
            user.save(update_fields=['role'])


def reverse_role_values_to_lowercase(apps, schema_editor):
    """
    Reverse data migration: Convert uppercase role values back to lowercase.
    """
    User = apps.get_model('accounts', 'User')
    role_mapping = {
        'USER': 'user',
        'SERVICER': 'servicer',
        'ADMIN': 'admin',
    }
    
    for user in User.objects.all():
        if user.role in role_mapping:
            user.role = role_mapping[user.role]
            user.save(update_fields=['role'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_rename_work_type_workprogress_title_and_more'),
    ]

    operations = [
        # First, update existing data to uppercase
        migrations.RunPython(
            update_role_values_to_uppercase,
            reverse_role_values_to_lowercase,
        ),
        # Then, update the field definition with new choices and default
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('USER', 'User'),
                    ('SERVICER', 'Servicer'),
                    ('ADMIN', 'Admin'),
                ],
                default='USER',
                max_length=20,
                verbose_name='user role'
            ),
        ),
    ]

