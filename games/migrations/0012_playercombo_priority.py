# Generated by Django 2.2.19 on 2022-06-28 13:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0011_auto_20220628_1303'),
    ]

    operations = [
        migrations.AddField(
            model_name='playercombo',
            name='priority',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
