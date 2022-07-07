# Generated by Django 2.2.19 on 2022-07-06 11:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0015_game_deck_generator'),
    ]

    operations = [
        migrations.AlterField(
            model_name='player',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='_players', to=settings.AUTH_USER_MODEL),
        ),
    ]
