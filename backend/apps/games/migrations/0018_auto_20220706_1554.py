# Generated by Django 2.2.19 on 2022-07-06 15:54

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0017_auto_20220706_1236'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='game',
            options={
                'ordering': ['-created'],
                'verbose_name': 'poker game',
                'verbose_name_plural': 'poker games',
            },
        ),
        migrations.AlterModelOptions(
            name='player',
            options={
                'ordering': ['-created'],
                'verbose_name': 'user in game (player)',
                'verbose_name_plural': 'users in games (players)',
            },
        ),
        migrations.RemoveField(
            model_name='player',
            name='bet',
        ),
        migrations.AlterField(
            model_name='player',
            name='user',
            # field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='_players', to='users.UserProxy'),
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='_players',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name='PlayerBet',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'created',
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name='creation data'
                    ),
                ),
                (
                    'modified',
                    models.DateTimeField(
                        auto_now=True, db_index=True, verbose_name='modification data'
                    ),
                ),
                ('value', models.PositiveIntegerField(default=0)),
                (
                    'player',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='_bet',
                        to='games.Player',
                    ),
                ),
            ],
            options={
                'ordering': ['-created'],
                'abstract': False,
            },
        ),
    ]