# Generated by Django 4.1 on 2022-09-09 18:49

import core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_alter_profile_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='bank',
            field=models.PositiveIntegerField(
                default=1000,
                validators=[
                    # core.validators.bet_multiplicity
                ],
            ),
        ),
    ]
