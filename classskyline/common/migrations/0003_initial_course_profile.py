# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def initial_fixture_data(apps, schema_editor):
    CourseProfile = apps.get_model('common', 'CourseProfile')

    CourseProfile.objects.create(id=1, name=u'标准配置', cpu=1, memory=2048, disk=20)
    CourseProfile.objects.create(id=2, name=u'高性能配置', cpu=2, memory=4096, disk=40)


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0002_initial_admin'),
    ]

    operations = [
        migrations.RunPython(initial_fixture_data)
    ]
