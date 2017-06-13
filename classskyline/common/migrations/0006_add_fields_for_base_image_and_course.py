# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from common.models.fields.pickle import UnicodePickledObjectField


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0005_classroom_delete_course_cascade'),
    ]

    operations = [
        migrations.AddField(
            model_name='baseimage',
            name='extras',
            field=UnicodePickledObjectField(null=True, editable=False, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='baseimage',
            name='refname',
            field=models.CharField(max_length=64, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='course',
            name='refname',
            field=models.CharField(max_length=64, null=True),
            preserve_default=True,
        ),
    ]
