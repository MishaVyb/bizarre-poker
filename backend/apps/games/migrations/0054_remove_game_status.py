# Generated by Django 4.1 on 2022-10-13 12:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0053_remove_game_deck_generator_game_config_name_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='game',
            name='status',
        ),
    ]
