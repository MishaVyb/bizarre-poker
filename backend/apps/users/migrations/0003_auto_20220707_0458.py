# Generated by Django 2.2.19 on 2022-07-07 04:58

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20220706_1236'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UserProxy',
        ),
        migrations.AlterField(
            model_name='profile',
            name='user',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='_profile',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
