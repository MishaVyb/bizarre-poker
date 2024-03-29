# Generated by Django 4.1 on 2022-08-26 05:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0042_alter_game_options_alter_player_managers_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='player',
            name='position',
            field=models.PositiveSmallIntegerField(
                default=0, verbose_name='player`s number in a circle starting from 0'
            ),
            preserve_default=False,
        ),
    ]
