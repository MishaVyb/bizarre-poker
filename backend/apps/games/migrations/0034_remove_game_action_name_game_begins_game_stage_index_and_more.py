# Generated by Django 4.1 on 2022-08-19 14:01

from django.db import migrations, models
import games.models.player


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0033_alter_player_options_alter_game_deck_generator_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='game',
            name='action_name',
        ),
        migrations.AddField(
            model_name='game',
            name='begins',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='game',
            name='stage_index',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='playerbet',
            name='_values',
            field=models.JSONField(
                # default=games.models.player.get_bet_default
            ),
        ),
        migrations.AlterField(
            model_name='playerbet',
            name='value',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]