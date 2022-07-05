# Generated by Django 2.2.19 on 2022-06-29 13:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0013_auto_20220629_1316'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='player',
            name='User can play in Game only by one Player',
        ),
        migrations.AddConstraint(
            model_name='player',
            constraint=models.UniqueConstraint(
                fields=('user', 'game'),
                name='unique: User can play in Game only by one Player',
            ),
        ),
    ]
