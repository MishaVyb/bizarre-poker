# Generated by Django 2.2.19 on 2022-07-07 05:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0021_auto_20220707_0521'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='game',
            options={
                'ordering': ['created'],
                'verbose_name': 'poker game',
                'verbose_name_plural': 'poker games',
            },
        ),
        migrations.AlterModelOptions(
            name='player',
            options={
                'ordering': ['created'],
                'verbose_name': 'user in game (player)',
                'verbose_name_plural': 'users in games (players)',
            },
        ),
        migrations.AlterModelOptions(
            name='playerbet',
            options={'ordering': ['created']},
        ),
    ]