# Generated by Django 2.2.19 on 2022-08-09 20:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0025_auto_20220809_1646'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='host',
            field=models.BooleanField(default=False, verbose_name='game host'),
        ),
        # migrations.AlterField(
        #     model_name='player',
        #     name='user',
        #     field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='_players', to='users.UserProxy'),
        # ),
    ]
