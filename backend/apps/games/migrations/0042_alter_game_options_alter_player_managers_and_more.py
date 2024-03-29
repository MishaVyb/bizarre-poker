# Generated by Django 4.1 on 2022-08-26 04:54

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_alter_profile_user'),
        ('games', '0041_remove_player_performer'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='game',
            options={
                'default_manager_name': 'objects',
                'ordering': ['created'],
                'verbose_name': 'poker game',
                'verbose_name_plural': 'poker games',
            },
        ),
        migrations.AlterModelManagers(
            name='player',
            managers=[
                ('_manager_for_related_fields', django.db.models.manager.Manager()),
            ],
        ),
        migrations.RemoveField(
            model_name='player',
            name='dealer',
        ),
        migrations.AlterField(
            model_name='player',
            name='game',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='players',
                to='games.game',
            ),
        ),
        migrations.AlterField(
            model_name='player',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='players',
                to='users.userproxy',
            ),
        ),
        migrations.AlterField(
            model_name='playerbet',
            name='player',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='bet',
                to='games.player',
            ),
        ),
    ]
