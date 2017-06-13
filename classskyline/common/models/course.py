# -*- coding: utf-8 -*-
from django.db.models import Model, CharField, PositiveSmallIntegerField, PositiveIntegerField, ForeignKey
from django.templatetags.static import static
from common.models.image import CourseImage, BaseImage


class CourseProfile(Model):

    name = CharField(max_length=256)  # 配置名称
    cpu = PositiveSmallIntegerField()  # CPU 核心数
    memory = PositiveIntegerField()  # 内存大小，单位 MB

    def __unicode__(self):
        return u'<{}: {} [CPU: {}, MEM: {}, DISK: {}]>'.format(
            self.__class__.__name__,
            self.name,
            self.cpu,
            self.memory)


class Course(Model):

    EXTRA_IMAGES = {
        'winxp': static('assets/global/img/windowsxp-gray.png'),
        'winvista': static('assets/global/img/windowsvista-gray.png'),
        'win7': static('assets/global/img/windows7-gray.png'),
        'win8': static('assets/global/img/windows8-gray.png'),
        'win2003': static('assets/global/img/windows2003-gray.png'),
        'win2008': static('assets/global/img/windows2008-gray.png'),
        'win2012': static('assets/global/img/windows2012-gray.png'),
        'rhel': static('assets/global/img/redhat-gray.png'),
        'suse': static('assets/global/img/suse-gray.png'),
        'centos': static('assets/global/img/centos-gray.png'),
        'oracle': static('assets/global/img/oracle-gray.png'),
        'debian': static('assets/global/img/debian-gray.png'),
        'ubuntu': static('assets/global/img/ubuntu-gray.png'),
        'linux': static('assets/global/img/linux-gray.png'),
        'unknown': static('assets/global/img/system-unknown-gray.png')
    }

    VISIBILITIES = (
        (0, u'管理员可见'),
        (1, u'管理员和教师可见'),
        (2, u'管理员、教师、学生可见')
    )

    name = CharField(max_length=64)
    refname = CharField(max_length=64, null=True)  # 虚拟机名称
    desc = CharField(max_length=1024)
    uuid = CharField(max_length=36, db_index=True)  # 课程虚机的 vmID
    priority = PositiveSmallIntegerField(default=0)
    profile = ForeignKey(CourseProfile)
    image = ForeignKey(CourseImage)
    visibility = PositiveSmallIntegerField(choices=VISIBILITIES, db_index=True)  # 是否可见

    @property
    def os_type(self):
        return self.image.parent.os_type

    @property
    def os_version(self):
        return self.image.parent.os_version

    def get_os_type_display(self):
        return self.image.parent.get_os_type_display()

    def get_os_version_display(self):
        return self.image.parent.get_os_version_display()

    def get_os_img_url(self):
        if self.visibility == 0:
            img_url = Course.EXTRA_IMAGES[self.image.parent.get_os_dict_key()]
        else:
            img_url = self.image.parent.get_os_img_url()
        return img_url

    def __unicode__(self):
        return u'<{}: {} [UUID: {}, DESC: {}, TYPE: {}, VERSION: {}, IMG: {}]>'.format(
            self.__class__.__name__,
            self.name,
            self.uuid,
            self.desc,
            self.get_os_type_display(),
            self.get_os_version_display(),
            self.image.image_path)
