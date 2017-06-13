# -*- coding: utf-8 -*-
from django.db.models import Model, GenericIPAddressField, CharField, PositiveSmallIntegerField, PositiveIntegerField


class Host(Model):

    VIRT_CAS = 0
    VIRT_KVM = 1
    VIRT_HYPERV = 2

    ip_address = GenericIPAddressField()
    uuid = CharField(max_length=36)  # host_id for CAS
    desc = CharField(max_length=1024)
    cpu = PositiveSmallIntegerField()  # CPU 核心数
    memory = PositiveIntegerField()  # 内存大小，单位 MB
    disk = PositiveIntegerField()  # 硬盘大小，单位 MB
    virt_type = PositiveSmallIntegerField(choices=(
        (VIRT_CAS, 'CAS'),
        (VIRT_KVM, 'KVM'),
        (VIRT_HYPERV, 'HYPER-V'),
    ), default=1)  # 虚拟化类型

    def __unicode__(self):
        return u'<{}: {} [UUID: {}, CPU: {}, MEM: {}, DISK: {}]>'.format(
            self.__class__.__name__,
            self.ip_address,
            self.uuid,
            self.cpu,
            self.memory,
            self.disk)
