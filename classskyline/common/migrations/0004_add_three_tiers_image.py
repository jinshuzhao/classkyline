# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import common.models.fields.pickle


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0003_initial_course_profile'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64)),
                ('capacity', models.IntegerField(default=10240)),
                ('image_path', models.CharField(max_length=512)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('image_md5', models.CharField(max_length=32, null=True, blank=True)),
                ('os_type', models.PositiveSmallIntegerField(blank=True, null=True, choices=[(0, b'Windows'), (1, b'Linux')])),
                ('os_version', models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, b'Microsoft Windows XP Professional(32-bit)'), (2, b'Microsoft Windows XP Professional(64-bit)'), (3, b'Microsoft Windows Vista(32-bit)'), (4, b'Microsoft Windows Vista(64-bit)'), (5, b'Microsoft Windows 7(32-bit)'), (6, b'Microsoft Windows 7(64-bit)'), (7, b'Microsoft Windows 8(32-bit)'), (8, b'Microsoft Windows 8(64-bit)'), (9, b'Microsoft Windows Server 2003(32-bit)'), (10, b'Microsoft Windows Server 2003(64-bit)'), (11, b'Microsoft Windows Server 2008(32-bit)'), (12, b'Microsoft Windows Server 2008(64-bit)'), (13, b'Microsoft Windows Server 2008 R2(64-bit)'), (14, b'Microsoft Windows Server 2012'), (15, b'Microsoft Windows Server 2012 R2'), (1001, b'Red Hat Enterprise Linux4(32-bit)'), (1002, b'Red Hat Enterprise Linux4(64-bit)'), (1003, b'Red Hat Enterprise Linux5(32-bit)'), (1004, b'Red Hat Enterprise Linux5(64-bit)'), (1005, b'Red Hat Enterprise Linux6(32-bit)'), (1006, b'Red Hat Enterprise Linux6(64-bit)'), (1050, b'Novell SUSE Linux Enterprise 8/9(32-bit)'), (1051, b'Novell SUSE Linux Enterprise 8/9(64-bit)'), (1052, b'Novell SUSE Linux Enterprise 10(32-bit)'), (1053, b'Novell SUSE Linux Enterprise 10(64-bit)'), (1054, b'Novell SUSE Linux Enterprise 11(32-bit)'), (1055, b'Novell SUSE Linux Enterprise 11(64-bit)'), (1100, b'CentOS 4/5/6(32bit)'), (1101, b'CentOS 4/5/6(64bit)'), (1150, b'Oracle Linux 4/5/6(32-bit)'), (1151, b'Oracle Linux 4/5/6(64-bit)'), (1200, b'Debian GUN/Linux 4(32-bit)'), (1201, b'Debian GUN/Linux 4(64-bit)'), (1202, b'Debian GUN/Linux 5(32-bit)'), (1203, b'Debian GUN/Linux 5(64-bit)'), (1204, b'Debian GUN/Linux 6(32-bit)'), (1205, b'Debian GUN/Linux 6(64-bit)'), (1250, b'Ubuntu Linux(32-bit)'), (1251, b'Ubuntu Linux(64-bit)'), (1500, b'Other Linux(32-bit)'), (1501, b'Other Linux(64-bit)')])),
                ('published', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Classroom',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('seats', models.SmallIntegerField()),
                ('state', models.PositiveSmallIntegerField(default=0, choices=[(0, '\u521d\u59cb\u72b6\u6001'), (1, '\u51c6\u5907\u4e0a\u8bfe'), (2, '\u6b63\u5728\u4e0a\u8bfe'), (3, '\u51c6\u5907\u4e0b\u8bfe')])),
                ('course', models.ForeignKey(blank=True, to='common.Course', null=True)),
                ('host', models.ForeignKey(to='common.Host')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CourseImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64)),
                ('capacity', models.IntegerField(default=10240)),
                ('image_path', models.CharField(max_length=512)),
                ('image_md5', models.CharField(max_length=32, null=True, blank=True)),
                ('image_version', models.IntegerField(default=1)),
                ('parent', models.ForeignKey(to='common.BaseImage')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='courseimage',
            unique_together=set([('name', 'image_version')]),
        ),
        migrations.CreateModel(
            name='DesktopImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64)),
                ('capacity', models.IntegerField(default=10240)),
                ('image_path', models.CharField(max_length=512)),
                ('image_md5', models.CharField(max_length=32, null=True, blank=True)),
                ('image_version', models.IntegerField(default=1)),
                ('parent', models.ForeignKey(to='common.CourseImage')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='desktopimage',
            unique_together=set([('name', 'image_version')]),
        ),
        # Option
        migrations.RenameModel(
            old_name='Settings',
            new_name='Option'),
        migrations.AlterField(
            model_name='option',
            name='key',
            field=models.CharField(unique=True, max_length=64),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='option',
            name='value',
            field=common.models.fields.pickle.UnicodePickledObjectField(editable=False),
            preserve_default=True,
        ),
        # TerminalConnJournal
        migrations.DeleteModel(
            name='TerminalConnJournal',
        ),
        # Host
        migrations.AlterField(
            model_name='host',
            name='disk',
            field=models.PositiveIntegerField(),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='host',
            name='ip_address',
            field=models.GenericIPAddressField(),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='host',
            name='memory',
            field=models.PositiveIntegerField(),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='host',
            name='virt_type',
            field=models.PositiveSmallIntegerField(default=1, choices=[(0, b'CAS'), (1, b'KVM'), (2, b'HYPER-V')]),
            preserve_default=True,
        ),
        migrations.RemoveField(
            model_name='host',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='host',
            name='deleted',
        ),
        migrations.RemoveField(
            model_name='host',
            name='deleted_at',
        ),
        migrations.RemoveField(
            model_name='host',
            name='deleted_by',
        ),
        migrations.RemoveField(
            model_name='host',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='host',
            name='updated_by',
        ),
        migrations.RemoveField(
            model_name='host',
            name='created_at',
        ),
        # Desktop
        migrations.RemoveField(
            model_name='desktop',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='deleted',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='deleted_at',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='deleted_by',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='host',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='is_snapshot',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='password',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='port',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='protocol',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='state',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='updated_by',
        ),
        migrations.RemoveField(
            model_name='desktop',
            name='username',
        ),
        migrations.AddField(
            model_name='desktop',
            name='address1',
            field=models.GenericIPAddressField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='desktop',
            name='address2',
            field=models.GenericIPAddressField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='desktop',
            name='image',
            field=models.ForeignKey(to='common.DesktopImage'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='desktop',
            name='password1',
            field=models.CharField(max_length=64, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='desktop',
            name='password2',
            field=models.CharField(max_length=64, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='desktop',
            name='port1',
            field=models.SmallIntegerField(default=-1),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='desktop',
            name='port2',
            field=models.SmallIntegerField(default=-1),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='desktop',
            name='protocol1',
            field=models.PositiveSmallIntegerField(null=True, choices=[(0, b'rdp'), (1, b'spice'), (2, b'vnc'), (3, b'ssh')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='desktop',
            name='protocol2',
            field=models.PositiveSmallIntegerField(null=True, choices=[(0, b'rdp'), (1, b'spice'), (2, b'vnc'), (3, b'ssh')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='desktop',
            name='username1',
            field=models.CharField(max_length=64, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='desktop',
            name='username2',
            field=models.CharField(max_length=64, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='desktop',
            name='ip_address',
            field=models.GenericIPAddressField(),
            preserve_default=True,
        ),
        # CourseProfile
        migrations.RemoveField(
            model_name='courseprofile',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='courseprofile',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='courseprofile',
            name='deleted',
        ),
        migrations.RemoveField(
            model_name='courseprofile',
            name='deleted_at',
        ),
        migrations.RemoveField(
            model_name='courseprofile',
            name='deleted_by',
        ),
        migrations.RemoveField(
            model_name='courseprofile',
            name='disk',
        ),
        migrations.RemoveField(
            model_name='courseprofile',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='courseprofile',
            name='updated_by',
        ),
        migrations.AlterField(
            model_name='courseprofile',
            name='memory',
            field=models.PositiveIntegerField(),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='courseprofile',
            name='name',
            field=models.CharField(max_length=256),
            preserve_default=True,
        ),
        # Course
        migrations.AddField(
            model_name='course',
            name='image',
            field=models.ForeignKey(to='common.CourseImage'),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='course',
            name='counter',
        ),
        migrations.RemoveField(
            model_name='course',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='course',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='course',
            name='deleted',
        ),
        migrations.RemoveField(
            model_name='course',
            name='deleted_at',
        ),
        migrations.RemoveField(
            model_name='course',
            name='deleted_by',
        ),
        migrations.RemoveField(
            model_name='course',
            name='host',
        ),
        migrations.RemoveField(
            model_name='course',
            name='is_volume',
        ),
        migrations.RemoveField(
            model_name='course',
            name='os_type',
        ),
        migrations.RemoveField(
            model_name='course',
            name='os_version',
        ),
        migrations.RemoveField(
            model_name='course',
            name='state',
        ),
        migrations.RemoveField(
            model_name='course',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='course',
            name='updated_by',
        ),
        migrations.AlterField(
            model_name='course',
            name='priority',
            field=models.PositiveSmallIntegerField(default=0),
            preserve_default=True,
        ),
        # Network
        migrations.RemoveField(
            model_name='network',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='network',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='network',
            name='deleted',
        ),
        migrations.RemoveField(
            model_name='network',
            name='deleted_at',
        ),
        migrations.RemoveField(
            model_name='network',
            name='deleted_by',
        ),
        migrations.RemoveField(
            model_name='network',
            name='enabled',
        ),
        migrations.RemoveField(
            model_name='network',
            name='subnet',
        ),
        migrations.RemoveField(
            model_name='network',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='network',
            name='updated_by',
        ),
        migrations.RenameField(
            model_name='network',
            old_name='ip_address_begin',
            new_name='address_begin',
        ),
        migrations.AlterField(
            model_name='network',
            name='address_begin',
            field=models.GenericIPAddressField(protocol=b'ipv4'),
            preserve_default=False,
        ),
        migrations.RenameField(
            model_name='network',
            old_name='ip_address_end',
            new_name='address_end',
        ),
        migrations.AlterField(
            model_name='network',
            name='address_end',
            field=models.GenericIPAddressField(protocol=b'ipv4'),
            preserve_default=False,
        ),
        migrations.RenameField(
            model_name='network',
            old_name='dns_master',
            new_name='dns',
        ),
        migrations.AlterField(
            model_name='network',
            name='dns',
            field=models.GenericIPAddressField(null=True, protocol=b'ipv4', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='network',
            name='activate_external',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='network',
            name='gateway',
            field=models.GenericIPAddressField(null=True, protocol=b'ipv4', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='network',
            name='name',
            field=models.CharField(default='default', unique=True, max_length=64),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='network',
            name='netmask',
            field=models.GenericIPAddressField(protocol=b'ipv4'),
            preserve_default=True,
        ),
        # Terminal
        migrations.RemoveField(
            model_name='terminal',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='terminal',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='terminal',
            name='deleted',
        ),
        migrations.RemoveField(
            model_name='terminal',
            name='deleted_at',
        ),
        migrations.RemoveField(
            model_name='terminal',
            name='deleted_by',
        ),
        migrations.RemoveField(
            model_name='terminal',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='terminal',
            name='updated_by',
        ),
        migrations.AlterField(
            model_name='terminal',
            name='ip_address',
            field=models.GenericIPAddressField(),
            preserve_default=True,
        ),
    ]
