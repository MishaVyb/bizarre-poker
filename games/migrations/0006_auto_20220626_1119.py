# Generated by Django 2.2.19 on 2022-06-26 11:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0005_auto_20220622_1004'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='player',
            options={
                'verbose_name': 'user in game (player)',
                'verbose_name_plural': 'users in games (players)',
            },
        ),
        migrations.CreateModel(
            name='GameProcess',
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
                ('status', models.CharField(default='not define yet', max_length=79)),
                ('step', models.SmallIntegerField(default=0)),
                (
                    'game',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='process',
                        to='games.Game',
                    ),
                ),
            ],
        ),
    ]
