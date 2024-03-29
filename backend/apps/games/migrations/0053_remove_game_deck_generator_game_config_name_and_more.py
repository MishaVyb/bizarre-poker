# Generated by Django 4.1 on 2022-10-12 07:08

import core.models
import core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0052_alter_player_bets'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='game',
            name='deck_generator',
        ),
        migrations.AddField(
            model_name='game',
            name='config_name',
            field=models.CharField(
                choices=[
                    ('bizarre', 'Bizarre'),
                    ('foolish', 'Foolish'),
                    ('classic', 'Classic'),
                    ('fun', 'Fun'),
                    ('crazy', 'Crazy'),
                ],
                default='classic',
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name='player',
            name='bets',
            field=models.JSONField(
                blank=True,
                default=core.models.get_list_default,
                validators=[core.validators.int_list_validator],
            ),
        ),
    ]
