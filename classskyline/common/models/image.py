# -*- coding: utf-8 -*-

from django.db.models import Model, CharField, IntegerField, ForeignKey, PositiveSmallIntegerField, DateTimeField, BooleanField
from django.templatetags.static import static
from common.models.fields.pickle import UnicodePickledObjectField

OS_WINDOWS = 0
OS_LINUX = 1

OS_WINXP_32 = 1
OS_WINXP_64 = 2
OS_WINVISTA_32 = 3
OS_WINVISTA_64 = 4
OS_WIN7_32 = 5
OS_WIN7_64 = 6
OS_WIN8_32 = 7
OS_WIN8_64 = 8
OS_WIN2003_32 = 9
OS_WIN2003_64 = 10
OS_WIN2008_32 = 11
OS_WIN2008_64 = 12
OS_WIN2008R2_64 = 13
OS_WIN2012 = 14
OS_WIN2012R2 = 15

OS_RHEL4_32 = 1001
OS_RHEL4_64 = 1002
OS_RHEL5_32 = 1003
OS_RHEL5_64 = 1004
OS_RHEL6_32 = 1005
OS_RHEL6_64 = 1006
OS_SUSE9_32 = 1050
OS_SUSE9_64 = 1051
OS_SUSE10_32 = 1052
OS_SUSE10_64 = 1053
OS_SUSE11_32 = 1054
OS_SUSE11_64 = 1055
OS_CENTOS_32 = 1100
OS_CENTOS_64 = 1101
OS_ORACLE_32 = 1150
OS_ORACLE_64 = 1151
OS_DEBIAN4_32 = 1200
OS_DEBIAN4_64 = 1201
OS_DEBIAN5_32 = 1202
OS_DEBIAN5_64 = 1203
OS_DEBIAN6_32 = 1204
OS_DEBIAN6_64 = 1205
OS_UBUNTU_32 = 1250
OS_UBUNTU_64 = 1251
OS_LINUX_32 = 1500
OS_LINUX_64 = 1501

OS_TYPE_CHOICES = (
    (OS_WINDOWS, 'Windows'),
    (OS_LINUX, 'Linux'),
)

OS_VERSION_CHOICES = (
    # (OS_WIN2000, 'Microsoft Windows 2000'),
    (OS_WINXP_32, 'Microsoft Windows XP Professional(32-bit)'),
    (OS_WINXP_64, 'Microsoft Windows XP Professional(64-bit)'),
    (OS_WINVISTA_32, 'Microsoft Windows Vista(32-bit)'),
    (OS_WINVISTA_64, 'Microsoft Windows Vista(64-bit)'),
    (OS_WIN7_32, 'Microsoft Windows 7(32-bit)'),
    (OS_WIN7_64, 'Microsoft Windows 7(64-bit)'),
    (OS_WIN8_32, 'Microsoft Windows 8(32-bit)'),
    (OS_WIN8_64, 'Microsoft Windows 8(64-bit)'),
    (OS_WIN2003_32, 'Microsoft Windows Server 2003(32-bit)'),
    (OS_WIN2003_64, 'Microsoft Windows Server 2003(64-bit)'),
    (OS_WIN2008_32, 'Microsoft Windows Server 2008(32-bit)'),
    (OS_WIN2008_64, 'Microsoft Windows Server 2008(64-bit)'),
    (OS_WIN2008R2_64, 'Microsoft Windows Server 2008 R2(64-bit)'),
    (OS_WIN2012, 'Microsoft Windows Server 2012'),
    (OS_WIN2012R2, 'Microsoft Windows Server 2012 R2'),

    (OS_RHEL4_32, 'Red Hat Enterprise Linux4(32-bit)'),
    (OS_RHEL4_64, 'Red Hat Enterprise Linux4(64-bit)'),
    (OS_RHEL5_32, 'Red Hat Enterprise Linux5(32-bit)'),
    (OS_RHEL5_64, 'Red Hat Enterprise Linux5(64-bit)'),
    (OS_RHEL6_32, 'Red Hat Enterprise Linux6(32-bit)'),
    (OS_RHEL6_64, 'Red Hat Enterprise Linux6(64-bit)'),
    (OS_SUSE9_32, 'Novell SUSE Linux Enterprise 8/9(32-bit)'),
    (OS_SUSE9_64, 'Novell SUSE Linux Enterprise 8/9(64-bit)'),
    (OS_SUSE10_32, 'Novell SUSE Linux Enterprise 10(32-bit)'),
    (OS_SUSE10_64, 'Novell SUSE Linux Enterprise 10(64-bit)'),
    (OS_SUSE11_32, 'Novell SUSE Linux Enterprise 11(32-bit)'),
    (OS_SUSE11_64, 'Novell SUSE Linux Enterprise 11(64-bit)'),
    (OS_CENTOS_32, 'CentOS 4/5/6(32bit)'),
    (OS_CENTOS_64, 'CentOS 4/5/6(64bit)'),
    (OS_ORACLE_32, 'Oracle Linux 4/5/6(32-bit)'),
    (OS_ORACLE_64, 'Oracle Linux 4/5/6(64-bit)'),
    (OS_DEBIAN4_32, 'Debian GUN/Linux 4(32-bit)'),
    (OS_DEBIAN4_64, 'Debian GUN/Linux 4(64-bit)'),
    (OS_DEBIAN5_32, 'Debian GUN/Linux 5(32-bit)'),
    (OS_DEBIAN5_64, 'Debian GUN/Linux 5(64-bit)'),
    (OS_DEBIAN6_32, 'Debian GUN/Linux 6(32-bit)'),
    (OS_DEBIAN6_64, 'Debian GUN/Linux 6(64-bit)'),
    (OS_UBUNTU_32, 'Ubuntu Linux(32-bit)'),
    (OS_UBUNTU_64, 'Ubuntu Linux(64-bit)'),
    (OS_LINUX_32, 'Other Linux(32-bit)'),
    (OS_LINUX_64, 'Other Linux(64-bit)'),
)


class BaseImageExtras(object):
    """BaseImage的extras扩展字段"""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class BaseImage(Model):
    """虚拟机原始镜像文件"""

    OS_IMAGES = {
        'winxp': static('assets/global/img/windowsxp.png'),
        'winvista': static('assets/global/img/windowsvista.png'),
        'win7': static('assets/global/img/windows7.png'),
        'win8': static('assets/global/img/windows8.png'),
        'win2003': static('assets/global/img/windows2003.png'),
        'win2008': static('assets/global/img/windows2008.png'),
        'win2012': static('assets/global/img/windows2012.png'),
        'rhel': static('assets/global/img/redhat.png'),
        'suse': static('assets/global/img/suse.png'),
        'centos': static('assets/global/img/centos.png'),
        'oracle': static('assets/global/img/oracle.png'),
        'debian': static('assets/global/img/debian.png'),
        'ubuntu': static('assets/global/img/ubuntu.png'),
        'linux': static('assets/global/img/linux.png'),
        'unknown': static('assets/global/img/system-unknown.png')
    }

    name = CharField(max_length=64, unique=True)
    refname = CharField(max_length=64, null=True)  # 虚拟机名称
    capacity = IntegerField(default=10240)  # MB
    image_path = CharField(max_length=512)
    created_at = DateTimeField(auto_now_add=True)
    image_md5 = CharField(max_length=32, null=True, blank=True)
    os_type = PositiveSmallIntegerField(null=True, blank=True, choices=OS_TYPE_CHOICES)
    os_version = PositiveSmallIntegerField(null=True, blank=True, choices=OS_VERSION_CHOICES)
    published = BooleanField(default=False)
    extras = UnicodePickledObjectField(null=True, blank=True)

    def get_os_dict_key(self):
        if self.os_version:
            if self.os_version < 20:
                if self.os_version in (1, 2):
                    return 'winxp'
                elif self.os_version in (3, 4):
                    return 'winvista'
                elif self.os_version in (5, 6):
                    return 'win7'
                elif self.os_version in (7, 8):
                    return 'win8'
                elif self.os_version in (9, 10):
                    return 'win2003'
                elif self.os_version in (11, 12, 13):
                    return 'win2008'
                elif self.os_version in (14, 15):
                    return 'win2012'
            else:
                if 1000 < self.os_version <= 1049:
                    return 'rhel'
                elif 1050 <= self.os_version <= 1099:
                    return 'suse'
                elif 1100 <= self.os_version <= 1149:
                    return 'centos'
                elif 1150 <= self.os_version <= 1199:
                    return 'oracle'
                elif 1200 <= self.os_version <= 1249:
                    return 'debian'
                elif 1250 <= self.os_version <= 1299:
                    return 'ubuntu'
                return 'linux'
        else:
            return 'unknown'

    def get_os_img_url(self):
        return BaseImage.OS_IMAGES[self.get_os_dict_key()]

    def __unicode__(self):
        return u'<{}: {} [SIZE: {}, PATH: {}]>'.format(
            self.__class__.__name__,
            self.name,
            self.capacity,
            self.image_path)


class CourseImage(Model):
    """课程镜像文件"""

    parent = ForeignKey(BaseImage)
    name = CharField(max_length=64)
    capacity = IntegerField(default=10240)
    image_path = CharField(max_length=512)
    image_md5 = CharField(max_length=32, null=True, blank=True)
    image_version = IntegerField(default=1)

    def __unicode__(self):
        return u'<{}: {} [SIZE: {}, PATH: {}, REF: {}]>'.format(
            self.__class__.__name__,
            self.name,
            self.capacity,
            self.image_path,
            self.parent.image_path)

    class Meta:
        unique_together = ('name', 'image_version')


class DesktopImage(Model):
    """云桌面镜像文件"""

    parent = ForeignKey(CourseImage)
    name = CharField(max_length=64)
    capacity = IntegerField(default=10240)
    image_path = CharField(max_length=512)
    image_md5 = CharField(max_length=32, null=True, blank=True)
    image_version = IntegerField(default=1)

    def __unicode__(self):
        return u'<{}: {} [SIZE: {}, PATH: {}, REF: {}]>'.format(
            self.__class__.__name__,
            self.name,
            self.capacity,
            self.image_path,
            self.parent.image_path)

    class Meta:
        unique_together = ('name', 'image_version')
