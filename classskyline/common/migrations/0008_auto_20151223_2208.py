# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0007_allow_dekstop_ip_address_null'),
    ]

    operations = [
        migrations.CreateModel(
            name='Gradeclass',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, blank=True)),
                ('description', models.CharField(max_length=200, blank=True)),
                ('totals', models.IntegerField(null=True)),
                ('seq', models.IntegerField(null=True)),
                ('is_init', models.NullBooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='LoginRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('studentnum', models.CharField(max_length=20, blank=True)),
                ('date_login', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, blank=True)),
                ('password', models.CharField(max_length=100, blank=True)),
                ('num', models.CharField(max_length=20, blank=True)),
                ('idcard', models.CharField(max_length=20, blank=True)),
                ('gender', models.PositiveIntegerField(verbose_name=set([(1, '\u7537'), (0, '\u5973')]))),
                ('stu_vm_number', models.IntegerField(null=True, blank=True)),
                ('grade', models.ForeignKey(to='common.Gradeclass')),
            ],
        ),
        migrations.AlterField(
            model_name='baseimage',
            name='name',
            field=models.CharField(unique=True, max_length=64),
        ),
    ]
