# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0006_add_fields_for_base_image_and_course'),
    ]

    operations = [
        migrations.AlterField(
            model_name='desktop',
            name='ip_address',
            field=models.GenericIPAddressField(null=True),
            preserve_default=True,
        ),
    ]
