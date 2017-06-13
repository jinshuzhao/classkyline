# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.db.models import Model, CharField, GenericIPAddressField, BooleanField

from utils.vendor.IPy import IP


class Network(Model):

    name = CharField(max_length=64, unique=True)
    address_begin = GenericIPAddressField(protocol='ipv4')
    address_end = GenericIPAddressField(protocol='ipv4')
    netmask = GenericIPAddressField(protocol='ipv4')
    gateway = GenericIPAddressField(protocol='ipv4', null=True, blank=True)
    dns = GenericIPAddressField(protocol='ipv4', null=True, blank=True)
    activate_external = BooleanField(default=True)

    def clean(self):
        ipaddr1 = IP(self.address_begin)
        ipaddr2 = IP(self.address_end)
        if ipaddr1 > ipaddr2:
            raise ValidationError('The begin address MUST be smaller than the end address')

        segment1 = ipaddr1.make_net(self.netmask)
        segment2 = ipaddr2.make_net(self.netmask)
        if segment1 != segment2:
            raise ValidationError('The begin address and end address MUST be in same network segment')

    def __unicode__(self):
        return u'<{}: {} [BEGIN: {}, END: {}, MASK: {}, GW: {}, DNS: {}, EXT: {}]>'.format(
            self.__class__.__name__,
            self.name,
            self.address_begin,
            self.address_end,
            self.netmask,
            self.gateway,
            self.dns,
            self.activate_external)
