# Generated by Django 4.1 on 2022-08-26 13:57

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager



class Migration(migrations.Migration):

    dependencies = [
        ('games', '0044_rename_active_player_is_active_and_more'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='playerbet',
            managers=[
                ('_manager_for_related_fields', django.db.models.manager.Manager()),
            ],
        ),
        migrations.RemoveField(
            model_name='playerbet',
            name='values',
        ),
        migrations.AddField(
            model_name='playerbet',
            name='value',
            field=models.PositiveIntegerField(
                default=0,
                validators=[
                    # games.models.player.bet_multiplicity
                ],
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='playerbet',
            name='player',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='bet',
                to='games.player',
            ),
        ),
    ]
