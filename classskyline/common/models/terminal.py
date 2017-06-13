# -*- coding: utf-8 -*-
from django.db.models import Model, CharField, GenericIPAddressField


class Terminal(Model):

    name = CharField(max_length=64)  # 瘦客户机名称
    mac_address = CharField(max_length=17, db_index=True)  # 网卡MAC地址
    ip_address = GenericIPAddressField()  # 网卡IP地址
    version = CharField(max_length=20)

    def __unicode__(self):
        return u'<{}: {} [IP:{}, MAC:{}]>'.format(
            self.__class__.__name__,
            self.name,
            self.ip_address,
            self.mac_address)
