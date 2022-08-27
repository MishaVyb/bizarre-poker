from django.db import migrations, models
import games.models.player


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0034_remove_game_action_name_game_begins_game_stage_index_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='playerbet',
            name='value',
        ),
    ]
