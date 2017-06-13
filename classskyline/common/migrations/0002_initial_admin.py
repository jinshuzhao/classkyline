# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def add_useradmin(apps, schema_editor):
    from django.contrib.auth.models import User
    # User = apps.get_model('django.contrib.auth', 'User')

    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', None, 'admin')


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_useradmin)
    ]
