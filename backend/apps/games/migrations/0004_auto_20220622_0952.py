# Generated by Django 2.2.19 on 2022-06-22 09:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0003_auto_20220622_0920'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='game',
            constraint=models.CheckConstraint(
                check=models.Q(_negated=True, id=13),
                name='not empty players list',
            ),
        ),
    ]
