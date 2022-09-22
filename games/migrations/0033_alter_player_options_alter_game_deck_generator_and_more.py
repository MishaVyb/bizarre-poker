# Generated by Django 4.1 on 2022-08-15 13:26

from django.db import migrations, models
import games.models.fields
import games.models.game


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0032_remove_game_only one host at game'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='player',
            options={
                'ordering': [
                    models.OrderBy(models.F('position'), nulls_last=True),
                    'id',
                ],
                'verbose_name': 'user in game (player)',
                'verbose_name_plural': 'users in games (players)',
            },
        ),
        migrations.AlterField(
            model_name='game',
            name='deck_generator',
            field=models.CharField(
                default=games.models.game.get_deck_default,
                max_length=79,
                verbose_name='name of deck generator method or contaianer',
            ),
        ),
        # migrations.AlterField(
        #     model_name='playerbet',
        #     name='value',
        #     field=games.models.fields.BetField(blank=True, default=None, null=True),
        # ),
    ]
