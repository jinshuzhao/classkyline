# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0004_add_three_tiers_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='classroom',
            name='course',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='common.Course', null=True),
            preserve_default=True,
        ),
    ]
