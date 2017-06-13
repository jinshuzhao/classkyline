# -*- coding: utf-8 -*-

MAC_TYPE_COURSE = 1
MAC_TYPE_VM = 2


def random_mac(class_id, type_id, index):
    oui = [0x0c, 0xda, 0x42]
    mac = oui + [
        class_id,
        type_id,
        index
    ]
    return ':'.join(map(lambda x: '%02X' % x, mac))
