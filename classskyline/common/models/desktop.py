# -*- coding: utf-8 -*-
from django.db.models import Model, CharField, GenericIPAddressField, SmallIntegerField, PositiveSmallIntegerField, ForeignKey

from common.models.course import Course
from common.models.image import DesktopImage


class Desktop(Model):

    PROTO_RDP = 0
    PROTO_SPICE = 1
    PROTO_VNC = 2
    PROTO_SSH = 3

    name = CharField(max_length=64, db_index=True)  # 虚拟机主机名
    uuid = CharField(max_length=36)  # 桌面虚机的vmID
    mac_address = CharField(max_length=17)  # 网卡MAC地址
    ip_address = GenericIPAddressField(null=True)  # 网卡IP地址
    protocol1 = PositiveSmallIntegerField(choices=(
        (PROTO_RDP, 'rdp'),
        (PROTO_SPICE, 'spice'),
        (PROTO_VNC, 'vnc'),
        (PROTO_SSH, 'ssh'),
    ), null=True)  # 首选协议
    address1 = GenericIPAddressField(null=True)  # 首选协议地址
    port1 = SmallIntegerField(default=-1)  # 首选协议端口
    username1 = CharField(max_length=64, null=True, blank=True)  # 首选协议用户名
    password1 = CharField(max_length=64, null=True, blank=True)  # 首选协议密码
    protocol2 = PositiveSmallIntegerField(choices=(
        (PROTO_RDP, 'rdp'),
        (PROTO_SPICE, 'spice'),
        (PROTO_VNC, 'vnc'),
        (PROTO_SSH, 'ssh'),
    ), null=True)  # 次选协议
    address2 = GenericIPAddressField(null=True)  # 次选协议地址
    port2 = SmallIntegerField(default=-1)  # 次选协议端口
    username2 = CharField(max_length=64, null=True, blank=True)  # 次选协议用户名
    password2 = CharField(max_length=64, null=True, blank=True)  # 次选协议密码
    course = ForeignKey(Course)  # 对应的课程
    image = ForeignKey(DesktopImage)

    def clean_protocol1(self):
        self.protocol1 = Desktop.PROTO_RDP
        self.address1 = None
        self.port1 = -1
        self.username1 = None
        self.password1 = None
        self.save()

    def set_protocol1(self, ipaddr):
        self.protocol1 = Desktop.PROTO_RDP
        self.address1 = ipaddr
        self.port1 = 3389
        self.username1 = 'h3class'
        self.password1 = 'h3class'
        self.save()

    def clean_protocol2(self):
        self.protocol2 = Desktop.PROTO_VNC
        self.address2 = None
        self.port2 = -1
        self.username2 = None
        self.password2 = None
        self.save()

    def set_protocol2(self, ipaddr, port):
        self.protocol2 = Desktop.PROTO_VNC
        self.address2 = ipaddr
        self.port2 = port
        self.save()

    def __unicode__(self):
        return u'<{}: {} [UUID: {}, MAC: {}, IP: {}, COURSE: {}, IMG: {}, PORT2: {}]>'.format(
            self.__class__.__name__,
            self.name,
            self.uuid,
            self.mac_address,
            self.ip_address,
            self.course and self.course.name,
            self.image and self.image.image_path,
            self.port2)
